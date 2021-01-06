import logging
from urllib.parse import unquote, urlparse

from datetime import datetime
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile

import requests
from bs4 import BeautifulSoup
from khayyam import JalaliDate

from .models import CMusic, Album, Artist

months = ["ژانویه", "فوریه", "مارس", "آوریل", "می", "ژوئن", "جولای", "آگوست", "سپتامبر", "اکتبر", "نوامبر", "دسامبر"]
jalali_months = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
alpha = "A aB bC cD dE eF fG gH hI iJ jK kL lM mN nO oP pQ qR rS sT tU uV vW wX xY yZ z"
logger = logging.getLogger(__name__)


class Crawler:
    category_id = 0
    website_name = ''

    def __init__(self):
        logger.info(f'[starting... crawler for {self.website_name}]')

    def collect_links(self):
        """
        Collecting the all links to get data from it.
        :return: a single link to detail of post (one music).
        """
        logger.info(f'[collect links starting...]-[website: {self.website_name}]')

    def collect_musics(self):
        """
        Collecting the detail of music.
        """
        logger.info(f'[collect musics starting...]-[website: {self.website_name}]')

    def collect_files(self):
        """
        Downloading the data of crawled musics that is_downloaded field is False.
        """
        logger.info(f'[collecting the files]-[website: {self.website_name}]')

    def make_request(self, url, method='get', **kwargs):
        try:
            req = requests.request(method, url, **kwargs, )
            req.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.critical(f'[make request failed! HTTP ERROR]-[response: {e.response.text}]-[status code: {e.response.status_code}]-[URL: {url}]')
            raise Exception(e.response.text)
        except requests.RequestException as e:
            logger.error(f"[make request failed! HTTP ERROR]-[exc: {e}]-[URL: {url}]")
            raise

        return req

    def get_crawled_musics(self):
        """
        Getting the CMusic that file of them is not downloaded.
        :return: A queryset of CMusic.
        """
        logger.debug(f'[getting the crawled music to download the files...]')
        for c in CMusic.objects.filter(
                is_downloaded=False,
                page_url__icontains=self.website_name
        ).order_by('-id'):
            yield c

    def get_crawler_album(self):
        logger.debug(f'[getting the crawled album to download the files...]')
        for c in Album.objects.filter(
                is_downloaded=False,
                page_url__icontains=self.website_name
        ).order_by('-id'):
            yield c

    @staticmethod
    def download_content(url):
        """
        :param url: URL of file to download the it.
        :return: File to save in CMusic object.
        """
        try:
            logger.debug(f'[downloading the URL: {url}]')
            r = requests.get(url, allow_redirects=False)
        except Exception as e:
            logger.error(f'[downloading file failed]-[exc: {e}]')
            return None
        img_temp = NamedTemporaryFile(delete=True)
        img_temp.write(r.content)
        img_temp.flush()  # deleting the file from RAM
        return File(img_temp, name=unquote(url).split('/')[-1])

    def download_all_files(self, c):
        """
        :param c: CMusic object to download file of it
        :return: None
        """
        c.file_mp3_128 = self.download_content(c.link_mp3_128)
        c.file_mp3_320 = self.download_content(c.link_mp3_320)
        c.file_thumbnail = self.download_content(c.link_thumbnail)
        if c.file_mp3_128 or c.file_mp3_320 or c.file_thumbnail:
            c.is_downloaded = True

    def fix_jdate(self, date_str, correct_month):
        for i, t in enumerate(correct_month):
            if t in date_str:
                month_text = date_str[date_str.find(t[0]):date_str.find(t[-2]) + 2]
                return date_str.replace(month_text, f'{i + 1}')

    def create_music(self, **kwargs):
        try:
            c_music, created = CMusic.objects.get_or_create(
                **kwargs
            )
            if created:
                logger.info(f'[new {c_music.post_type} created]-[id:{c_music.id}]-[album id: {c_music.album_id}]')
            else:
                logger.info(
                    f'[duplicate {c_music.post_type} found]-[id:{c_music.id}]-[album id: {c_music.album_id}]')
        except Exception as e:
            logger.warning(f"[creating music failed]-[exc: {e}]")

    def create_album(self, site_id, defaults):
        try:
            album, created = Album.objects.get_or_create(
                site_id=site_id,
                defaults=defaults
            )
        except Exception as e:
            logger.warning(f"[Creating album failed]-[exc: {e}]-[site_id: {site_id}]")
            logger.debug(f"[defaults: {defaults}]")
            return
        if created:
            logger.info(f'[new album created]-[id: {album.id}]')
        else:
            logger.info(f'[duplicate album found]-[id: {album.id}]')
        return album

    def create_artist(self, **kwargs):
        correct_names = [value for key, value in kwargs.items()]
        artists = Artist.objects.filter(**kwargs)
        if artists.exists():
            return artists.first()

        try:
            kwargs['correct_names'] = correct_names
            artist, created = Artist.objects.get_or_create(
                correct_names__overlap=correct_names,
                defaults=kwargs
            )
        except Exception as e:
            logger.error(f"[creating artist failed]-[exc: {e}]-[kwargs: {kwargs}]")
            return
        if created:
            logger.info(f'[new artist created]-[id: {artist.id}]')
        else:
            logger.info(f'[duplicate artist found]-[id: {artist.id}]')
        return artist


class NicMusicCrawler(Crawler):
    category_id = 0
    website_name = 'nicmusic'
    base_url = 'https://nicmusic.net/'

    def collect_files(self):
        super().collect_files()
        for c in self.get_crawled_musics():
            self.download_all_files(c)
            try:
                c.save()
            except Exception as e:
                logger.error(f'[saving downloaded files failed]-[exc: {e}]-[id: {c.id}]-[obj: {c}]')

    def collect_links(self):
        super().collect_links()
        try:
            main_page = self.make_request(self.base_url)
            main_soup = BeautifulSoup(main_page.text, "html.parser")
            nav_links = main_soup.find("div", class_="nav-links").find_all("a")
            total_pages = int(nav_links[-2].get_text())
            for i in range(1, total_pages + 1):
                page = requests.get(f"{self.base_url}page/{i}/")
                soup = BeautifulSoup(page.text, "html.parser")
                for post in soup.find_all("a", class_="show-more"):
                    yield post.attrs["href"]
        except Exception as e:
            logger.error(f"[collecting links failed]-[exc: {e}]-[website: {self.website_name}]")

    def collect_musics(self):
        super().collect_musics()
        for url in self.collect_links():
            page = self.make_request(url)
            try:
                soup = BeautifulSoup(page.text, "html.parser")

                artist_name_fa = ""
                title = soup.find("h1", class_="title").find("a").getText().strip()
                title = title.encode().decode('utf-8-sig')
                names = soup.find("div", class_="post-content").find_all("strong")
                names_en = soup.find("div", class_="post-content").find_all("p")
                name_en = ""
                for name in names_en:
                    name = name.get_text().encode().decode('utf-8-sig')
                    for char in name:
                        if char in alpha:
                            name_en += char
                song_name_start_index = name_en.index("Called ")
                artist_name_start_index = name_en.index("By ")
                artist_name_en = name_en[
                                 artist_name_start_index + 2:song_name_start_index].strip().encode().decode(
                    'utf-8-sig')
                song_name_en = name_en[song_name_start_index + 6:].strip().encode().decode('utf-8-sig')
                categories = soup.find("div", class_="categories").find("a").get_text()
                if len(names) > 0:
                    if categories not in ["آهنگ های گوناگون", "تک آهنگ های جدید"] and categories.startswith(
                            "آهنگ های "):
                        artist_name_fa = categories[9:]
                    elif categories not in ["آهنگ های گوناگون", "تک آهنگ های جدید"] and categories.startswith(
                            "دانلود آهنگ "):
                        artist_name_fa = categories[12:].encode().decode('utf-8-sig')
                    else:
                        artist_name_fa = names[0].get_text().encode().decode('utf-8-sig')

                song_name_fa_start_index = title.index("به نام")
                song_name_fa = title[song_name_fa_start_index + 6:].strip().encode().decode('utf-8-sig')

                if len(artist_name_fa) == 0 or artist_name_fa[0] in alpha:
                    names2 = names[2].get_text()
                    if names2[0] not in alpha:
                        artist_name_fa = names[2].get_text()
                lyrics_all = soup.find("div", class_="post-content").find_all("p")[7:]
                lyrics = ""
                if lyrics_all:
                    for ly in lyrics_all:
                        lyrics += f"{ly.get_text().strip()}\n"

                lyrics = lyrics.replace("\"", "")
                lyrics = lyrics.strip().encode().decode('utf-8-sig')
                if "دانلود در ادامه مطلب" in lyrics:
                    start_index = lyrics.index("دانلود در ادامه مطلب")
                    lyrics = lyrics[start_index + 21:]
                    lyrics = lyrics.strip()
                quality_128 = soup.find("a", class_="dl-128").attrs["href"].encode().decode('utf-8-sig')
                quality_320 = soup.find("a", class_="dl-320").attrs["href"].encode().decode('utf-8-sig')
                thumbnail = soup.find("img", class_=["size-full", "size-medium"]).attrs[
                    "data-src"].encode().decode(
                    'utf-8-sig')
                publish_date = self.fix_jdate(soup.find("div", class_="times").get_text().strip(), months)
                publish_date = datetime.strptime(publish_date, '%m %d, %Y')

                if len(artist_name_en) > 0:
                    kwargs = dict(
                        site_id=self.get_site_id(soup),
                        defaults={
                            "title": title,
                            "song_name_fa": song_name_fa,
                            "song_name_en": song_name_en,
                            "post_type": CMusic.SINGLE_TYPE,
                            "lyrics": lyrics,
                            "artist": self.create_artist(name_en=artist_name_en, name_fa=artist_name_fa),
                            "link_mp3_128": quality_128,
                            "link_mp3_320": quality_320,
                            "link_thumbnail": thumbnail,
                            "published_date": publish_date,
                            'page_url': url,
                            'wp_category_id': self.category_id
                        }
                    )
                    self.create_music(**kwargs)
            except Exception as e:
                logger.warning(f'[failed to collect music]-[exc: {e}]-[website: {self.website_name}]')
                continue

    def get_site_id(self, soup):
        site_id = urlparse(soup.find('link', attrs={'rel': 'shortlink'}).attrs['href']).query  # etc. p=83628
        return site_id.replace('p=', '')


class Ganja2MusicCrawler(Crawler):
    category_id = 0
    website_name = 'ganja2music'
    base_url = 'https://www.ganja2music.com/'

    def collect_musics(self):
        super().collect_musics()
        self.collect_album_musics()
        self.collect_single_musics()

    def get_download_link(self, soup):
        # Download link
        link_320 = ''
        link_128 = ''
        music_dl_links = soup.find_all('a', class_='dlbter')
        for link in music_dl_links:
            if '320' in link.get_text():
                link_320 = link.attrs['href']
            elif '128' in link.get_text():
                link_128 = link.attrs.get('href')
        return link_128, link_320

    def get_thumbnail(self, soup):
        from .utils import url_join

        # Thumbnail
        link_thumbnail = soup.find('div', class_='insidercover').find('a').attrs['href']
        return url_join(self.base_url, link_thumbnail[1:])

    def get_content_section_info(self, soup):
        from .utils import per_num_to_eng

        # Name of Music, Artist and Publish Date
        content_section = soup.find('div', class_='content')
        song_name_en = content_section.find('h2').get_text()
        artist_name_en = content_section.find('div', class_='thisinfo').find('a').get_text()
        publish_date = per_num_to_eng(self.fix_jdate(
            content_section.find('div', class_='feater').find('b').get_text(),
            jalali_months
        ))
        publish_date = JalaliDate.strptime(publish_date, '%m , %d , %Y').todate()
        return song_name_en, artist_name_en, publish_date

    def get_title(self, soup):
        # Title
        title_section = soup.find('div', class_='tinle')
        return f"{title_section.find('b').get_text()} {title_section.find('i').get_text()}"

    def get_obj_site_id(self, url):
        return url.split('/')[3]

    def collect_link_singles(self):
        for link in self.collect_post_links('archive/single/'):
            yield link

    def collect_single_musics(self):
        """
        Getting the detail of each Music. collecting all data of musics.
        :return: None
        """
        for post_page_url in self.collect_link_singles():
            try:
                soup = BeautifulSoup(self.make_request(post_page_url).text, "html.parser")
                link_128, link_320 = self.get_download_link(soup)
                link_thumbnail = self.get_thumbnail(soup)
                song_name_en, artist_name_en, publish_date = self.get_content_section_info(soup)
                title = self.get_title(soup)

                # Lyric
                lyric_text = soup.find('div', class_='tab-pane fade in active').find('p')
                if lyric_text:
                    lyric_text = lyric_text.get_text()

                kwargs = dict(
                    site_id=self.get_obj_site_id(post_page_url),
                    defaults=dict(
                        artist=self.create_artist(name_en=artist_name_en),  # get or create Artist
                        song_name_en=song_name_en,
                        link_mp3_128=link_128,
                        link_mp3_320=link_320,
                        link_thumbnail=link_thumbnail,
                        lyrics=lyric_text or '',
                        title=title,
                        published_date=publish_date,
                        post_type=CMusic.SINGLE_TYPE,
                        page_url=post_page_url,
                        wp_category_id=self.category_id
                    )
                )
                self.create_music(**kwargs)  # get or create CMusic
            except Exception as e:
                logger.error(f'[collect single music failed]-[exc: {e}]-[website: {self.website_name}]')
                continue

    def collect_link_albums(self):
        for link in self.collect_post_links('archive/album/'):
            yield link

    def collect_album_musics(self):
        for post_page_url in self.collect_link_albums():
            try:
                soup = BeautifulSoup(self.make_request(post_page_url).text, "html.parser")

                link_128, link_320 = self.get_download_link(soup)  # zip files
                link_thumbnail = soup.find('div', class_='insidercover').find('a').attrs['href']
                if not link_thumbnail.startswith('http'):
                    link_thumbnail = self.get_thumbnail(soup)
                album_name_en, artist_name_en, publish_date = self.get_content_section_info(soup)
                title = self.get_title(soup)
                site_id = self.get_obj_site_id(post_page_url)

                defaults = dict(
                    artist=self.create_artist(name_en=artist_name_en),
                    page_url=post_page_url,
                    link_mp3_128=link_128,
                    link_mp3_320=link_320,
                    link_thumbnail=link_thumbnail,
                    title=title,
                    album_name_en=album_name_en,
                    published_date=publish_date,
                    site_id=site_id,
                    wp_category_id=self.category_id
                )
                album = self.create_album(site_id, defaults)

                # getting and creating all musics
                album_musics = soup.find_all('div', class_='trklines')

                for index, m in enumerate(album_musics):
                    link_mp3_320 = m.find('div', class_='rightf3').find('a').attrs['href']
                    kwargs = dict(
                        # creating custom site id for `album-musics` type from album site id
                        site_id=f"{int(site_id) + 1001 + index}",
                        defaults=dict(
                            link_mp3_128=m.find('div', class_='rightf3 plyiter').find('a').attrs['href'],
                            link_mp3_320=link_mp3_320,
                            album=album,
                            artist_id=album.artist_id,
                            published_date=publish_date,
                            page_url=post_page_url,
                            post_type=CMusic.ALBUM_MUSIC_TYPE,
                            song_name_en=m.find('div', class_='rightf2').get_text(),
                            wp_category_id=self.category_id
                        )
                    )
                    self.create_music(**kwargs)
            except Exception as e:
                logger.error(f"[creating album failed]-[exc: {e}]-[URL: {post_page_url}]")
                continue

    def detect_new_post_in_page(self, main_page_url, soup):
        music_ids_in_current_page = [link.attrs['href'].split('/')[3] for link in soup.find_all('a', class_='iaebox')]
        if 'single' in main_page_url and CMusic.objects.filter(site_id__in=music_ids_in_current_page).count() < 30:
            return True
        elif 'album' in main_page_url and Album.objects.filter(site_id__in=music_ids_in_current_page).count() < 30:
            return True
        return False

    def collect_post_links(self, main_page_url):
        logger.info(f'[collect single music links]-[website: {self.website_name}]')
        try:
            # Getting the first page musics
            first_page = self.make_request(f"{self.base_url}{main_page_url}")
            soup = BeautifulSoup(first_page.text, "html.parser")
            next_page_link = soup.find('div', class_='pagenumbers').find('a', class_="next page-numbers").attrs['href']
            if self.detect_new_post_in_page(main_page_url, soup):
                for post_detail in soup.find_all('div', class_='postbox'):
                    yield post_detail.find('a', class_='iaebox').attrs['href']
        except Exception as e:
            logger.error(f'[getting first page failed]-[exc: {e}]-[URL: {main_page_url}')
            return
        # Crawling the next pages
        while next_page_link:
            try:
                page = self.make_request(next_page_link)
                soup = BeautifulSoup(page.text, "html.parser")
                if self.detect_new_post_in_page(main_page_url, soup):
                    for post_detail in soup.find_all('div', class_='postbox'):
                        link = post_detail.find('a', class_='iaebox').attrs['href']
                        yield link
                else:
                    logger.info(f'[crawled page found. skipping this page]-[URL: {next_page_link}]')
                next_page_link = soup.find('div', class_='pagenumbers').find('a', class_="next page-numbers").attrs[
                    'href']
                logger.info(f'[next page]-[URL: {next_page_link}]')
            except Exception as e:
                logger.error(f'[navigating pages failed]-[exc: {e}]-[current page: {next_page_link}]')
                continue

    def collect_files(self):
        super().collect_files()
        self.collect_album_files()
        self.collect_music_files()

    def collect_music_files(self):
        for c in self.get_crawled_musics():
            if c.album or CMusic.ALBUM_MUSIC_TYPE:  # downloading just the 320 file from album-music
                c.file_mp3_320 = self.download_content(c.link_mp3_320)
                if c.file_mp3_320:
                    c.is_downloaded = True
            else:
                self.download_all_files(c)
            try:
                c.save()
            except Exception as e:
                logger.error(f'[collect files failed]-[exc: {e}]-[cmusic: {c}]')

    def collect_album_files(self):
        for c in self.get_crawler_album():
            c.file_thumbnail = self.download_content(c.link_thumbnail)
            if c.file_thumbnail:
                c.is_downloaded = True
            try:
                c.save()
            except Exception as e:
                logger.error(f'[collect files failed]-[exc: {e}]-[album: {c}]')


