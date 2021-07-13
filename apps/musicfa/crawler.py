import re
import logging
from datetime import datetime
from urllib.parse import unquote, urlparse

from django.core.validators import URLValidator
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
            logger.debug(f'[downloading content]-[URL: {url}]')
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
                logger.debug(f'[new {c_music.post_type} created]-[id:{c_music.id}]-[album id: {c_music.album_id}]')
            else:
                logger.debug(
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
            logger.debug(f'[new album created]-[id: {album.id}]')
        else:
            logger.debug(f'[duplicate album found]-[id: {album.id}]')
        return album

    def create_artist(self, **kwargs):
        artist = None
        created = False
        correct_names = [value.strip() for key, value in kwargs.items()]
        kwargs['correct_names'] = correct_names

        try:
            for name in correct_names:
                q1 = Artist.objects.filter(correct_names__contains=[name])
                q2 = Artist.objects.filter(correct_names__iregex=fr'^\b{{name}}\b')
                artist = q1.intersection(q2).first()

                if q1.count() == 0 or q2.count() == 0:
                    artist = q1.difference(q2).first() or q2.difference(q1).first()

                if artist is not None:
                    break

            if artist is None:
                artist = Artist.objects.create(**kwargs)
                created = True

        except Exception as e:
            logger.error(f"[creating artist failed]-[exc: {e}]-[kwargs: {kwargs}]")
            return
        if created:
            logger.debug(f'[new artist created]-[id: {artist.id}]')
        else:
            logger.debug(f'[duplicate artist found]-[id: {artist.id}]')
        return artist

    def is_duplicate(self, cls, site_id):
        return cls.objects.filter(site_id=site_id).exists()
        
    def is_new_post_album(self, site_id):
        """
        :param site_id: site id of Album
        :return: if the CMusic is not exist it's mean new post (True) otherwise (False) will return.
        """
        return self.is_duplicate(Album, site_id)

    def is_new_post_single(self, site_id):
        """
        :param site_id: site id of CMusic
        :return: if the CMusic is not exist it's mean new post (True) otherwise (False) will return.
        """
        return self.is_duplicate(CMusic, site_id)

    def is_valid_url(self, url):
        val = URLValidator()
        try:
            val(url)
            return True
        except Exception as e:
            logger.warning(f'[invalid URL found]-[URL: {url}]-[website: {self.website_name}]-[exc: {e}]')
            return False

    def clean_url(self, url):
        pass

    def invalid_url_found_log(self, invalid_url, post_url, field_name):
        logger.warning(
            f'[invalid url found for {field_name} file... skipping this post]-[Post URL: {post_url}]'
            f'-[Invalid URL: {invalid_url}]-[website: {self.website_name}]'
        )


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

            logger.info(f'[{total_pages} page found to crawl]-[website: {self.website_name}]')
            for i in range(1, total_pages + 1):
                page_url = f"{self.base_url}page/{i}/"
                page = requests.get(page_url)
                soup = BeautifulSoup(page.text, "html.parser")
                logger.info(f'[crawling... ]-[URL: {page_url}]')
                for post in soup.find_all("a", class_="show-more"):
                    yield post.attrs["href"]
        except Exception as e:
            logger.error(f"[collecting links failed]-[exc: {e}]-[website: {self.website_name}]")

    def collect_musics(self):
        super().collect_musics()
        for post_url in self.collect_links():
            page = self.make_request(post_url)
            try:
                soup = BeautifulSoup(page.text, "html.parser")

                artist_name_fa = ""
                title = soup.find("h1", class_="title").find("a").getText().strip()
                title = title.encode().decode('utf-8-sig')
                names = soup.find("div", class_="post-content").find_all("strong")

                raw_name_en = urlparse(soup.find("a", class_="dl-320").attrs["href"].encode().decode('utf-8-sig')).path
                raw_name_en = unquote(raw_name_en).split('/')[-1].replace('.mp3', '').split('-')
                artist_name_en = raw_name_en[0]
                song_name_en = raw_name_en[1]

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

                # Getting Songs URLs 128, 320
                quality_128 = soup.find("a", class_="dl-128").attrs["href"].encode().decode('utf-8-sig')
                quality_320 = soup.find("a", class_="dl-320").attrs["href"].encode().decode('utf-8-sig')
                # Validating the files URL
                if not self.is_valid_url(quality_128):
                    self.invalid_url_found_log(quality_128, post_url, 'music 128')
                    continue
                if not self.is_valid_url(quality_320):
                    self.invalid_url_found_log(quality_320, post_url, 'music 320')
                    continue

                # thumbnail link
                thumbnail = soup.find("img", class_=["size-full", "size-medium"]).attrs[
                    "data-src"].encode().decode(
                    'utf-8-sig')
                # validating thumbnail
                if not self.is_valid_url(thumbnail):
                    self.invalid_url_found_log(thumbnail, post_url, 'thumbnail')
                    continue

                publish_date = self.fix_jdate(soup.find("div", class_="times").get_text().strip(), months)
                publish_date = datetime.strptime(publish_date, '%m %d, %Y')

                artist = self.create_artist(name_en=artist_name_en, name_fa=artist_name_fa)
                site_id = self.get_site_id(soup)

                if not self.is_new_post_single(site_id):
                    if len(artist_name_en) > 0:
                        kwargs = dict(
                            site_id=site_id,
                            defaults={
                                "title": title,
                                "song_name_fa": song_name_fa,
                                "song_name_en": song_name_en,
                                "post_type": CMusic.SINGLE_TYPE,
                                "lyrics": lyrics,
                                "artist": artist,
                                "link_mp3_128": quality_128,
                                "link_mp3_320": quality_320,
                                "link_thumbnail": thumbnail,
                                "published_date": publish_date,
                                'page_url': post_url,
                                'wp_category_id': self.category_id
                            }
                        )
                        self.create_music(**kwargs)
                else:
                    logger.info(f'[duplicate post found]-[URL: {post_url}]')
                    return
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
                link_128 = link.attrs['href']
        return self.clean_url(link_128), self.clean_url(link_320)

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
        for link in self.collect_post_links('archive/single/', 'single'):
            yield link

    def collect_single_musics(self):
        """
        Getting the detail of each Music. collecting all data of musics.
        :return: None
        """
        for post_page_url in self.collect_link_singles():
            try:
                soup = BeautifulSoup(self.make_request(post_page_url).text, "html.parser")

                # Getting links of this post
                link_128, link_320 = self.get_download_link(soup)

                if not self.is_valid_url(link_128):
                    self.invalid_url_found_log(link_128, post_page_url, 'music 128')
                    continue
                if not self.is_valid_url(link_320):
                    self.invalid_url_found_log(link_320, post_page_url, 'music 320')
                    continue

                link_thumbnail = self.get_thumbnail(soup)
                if not self.is_valid_url(link_thumbnail):
                    self.invalid_url_found_log(link_thumbnail, post_page_url, 'thumbnail')
                    continue

                song_name_en, artist_name_en, publish_date = self.get_content_section_info(soup)
                title = self.get_title(soup)

                # Lyric
                lyric = soup.find('div', class_='tab-pane fade in active').find('p')

                # Title tag
                title_tag = self.get_title_tag(soup)

                artist = self.create_artist(name_en=artist_name_en)  # get or create Artist
                kwargs = dict(
                    site_id=self.get_obj_site_id(post_page_url),
                    defaults=dict(
                        artist=artist,
                        song_name_en=song_name_en,
                        link_mp3_128=link_128,
                        link_mp3_320=link_320,
                        link_thumbnail=link_thumbnail,
                        lyrics=lyric.decode_contents() if lyric else '',
                        title=title,
                        title_tag=title_tag,
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
        for link in self.collect_post_links('archive/album/', 'album'):
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
                artist = self.create_artist(name_en=artist_name_en)

                # Title tag
                title_tag = self.get_title_tag(soup)

                defaults = dict(
                    artist=artist,
                    page_url=post_page_url,
                    link_mp3_128=link_128,
                    link_mp3_320=link_320,
                    link_thumbnail=link_thumbnail,
                    title=title,
                    title_tag=title_tag,
                    album_name_en=album_name_en,
                    published_date=publish_date,
                    site_id=site_id,
                    wp_category_id=self.category_id
                )

                # getting and creating all musics
                album_musics = soup.find_all('div', class_='trklines')
                if album_musics:
                    album = self.create_album(site_id, defaults)
                    for index, m in enumerate(album_musics):
                        link_mp3_320 = m.find('div', class_='rightf3').find('a').attrs['href']
                        link_mp3_128 = m.find('div', class_='rightf3 plyiter').find('a').attrs['href']
                        kwargs = dict(
                            # creating custom site id for `album-musics` type from album site id
                            site_id=f"{int(site_id) + 1001 + index}",
                            defaults=dict(
                                link_mp3_128=link_mp3_128,
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
                else:
                    logger.warning("[finding tracks of album failed]-[exc: track list is empty]")
            except Exception as e:
                logger.error(f"[creating album failed]-[exc: {e}]-[URL: {post_page_url}]")
                continue

    def collect_post_links(self, main_page_url, post_type):
        main_url = f"{self.base_url}{main_page_url}"
        logger.info(f'[collect single music links]-[website: {self.website_name}]')
        try:
            # Getting the first page musics
            first_page = self.make_request(main_url)
            soup = BeautifulSoup(first_page.text, "html.parser")
            navigation_section = soup.find_all('a', class_="page-numbers")
            # to remove any non digit character from this text like this ("3,045") using re.sub
            last_page = int(re.sub("[^0-9]", "", navigation_section[-2].get_text()))

        except Exception as e:
            logger.error(f'[getting first page failed]-[exc: {e}]-[URL: {main_page_url}')
        else:
            logger.info(f'[{last_page} page found to crawl]-[website: {self.website_name}]')
            # Crawling the next pages
            for i in range(1, last_page + 1):
                current_page_url = f"{main_url}page/{i}"
                page = self.make_request(current_page_url)
                soup = BeautifulSoup(page.text, "html.parser")
                logger.info(f'[crawling page...]-[URL: {current_page_url}]')
                for post_detail in soup.find_all('div', class_='postbox'):
                    link = post_detail.find('a', class_='iaebox').attrs['href']
                    site_id = link.split('/')[3]
                    if not getattr(self, f'is_new_post_{post_type}')(site_id):  # post_type could be album or single
                        yield link
                    else:
                        logger.info(f'[duplicate post found]-[URL: {link}]-[Page: {current_page_url}]')
                        return

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

    def clean_url(self, url):
        if url.startswith('dl.ganja2music.com'):
            return f'http://{url}'
        return url

    def get_title_tag(self, soup):
        return soup.find('title').get_text()

