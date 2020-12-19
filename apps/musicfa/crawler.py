import logging
import sys
from urllib.parse import unquote

from datetime import datetime
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile

import requests
from bs4 import BeautifulSoup

from .models import CMusic, Artist, Album
from .utils import PrintException, per_num_to_eng

months = ["ژانویه", "فوریه", "مارس", "آوریل", "می", "ژوئن", "جولای", "آگوست", "سپتامبر", "اکتبر", "نوامبر", "دسامبر"]
jalali_months = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
alpha = "A aB bC cD dE eF fG gH hI iJ jK kL lM mN nO oP pQ qR rS sT tU uV vW wX xY yZ z"
logger = logging.getLogger(__name__)


class Crawler:
    website_name = ''

    def __init__(self):
        logger.info(f'>> Starting... crawler for {self.website_name}')

    def collect_links(self):
        logger.info(f'{self.website_name} collect links starting...')

    def collect_musics(self):
        logger.info(f'{self.website_name} collect musics starting...')

    def collect_files(self):
        logger.info(f'>> Collecting the files of CMusic {self.website_name}.')
        for c in self.get_crawled_musics():
            c.file_mp3_128 = self.download_content(c.link_mp3_128)
            c.file_mp3_320 = self.download_content(c.link_mp3_320)
            c.file_thumbnail = self.download_content(c.link_thumbnail)
            c.is_downloaded = True
            try:
                c.save()
            except Exception as e:
                logger.error(f'>> collect files failed CMusic id: {c.id}')
                PrintException()

    def make_request(self, url, method='get', **kwargs):
        try:
            req = requests.request(method, url, **kwargs, )
            req.raise_for_status()
            if req.ok:
                return req
            else:
                logger.error(f'>> Make request failed! URL: {url} status: {req.status_code}')
        except requests.HTTPError:
            logger.error(f">> Make request failed! HTTP ERROR! URL: {url}")
            raise

    def get_crawled_musics(self):
        """
        Getting the CMusic that file of them is not downloaded.
        :return: A queryset of CMusic.
        """
        for c in CMusic.objects.filter(
                is_downloaded=False,
                post_name_url__icontains=self.website_name
        ):
            yield c

    def download_content(self, url):
        """
        :param url: URL of file to download the it.
        :return: File to save in CMusic object.
        """
        try:
            logger.info(f'>> Starting Download the URL: {url}')
            r = requests.get(url, allow_redirects=False)
        except Exception as e:
            logger.error(f'>> Downloading file failed. {e}')
            PrintException()
            return None
        img_temp = NamedTemporaryFile(delete=True)
        img_temp.write(r.content)
        img_temp.flush()  # deleting the file from RAM
        return File(img_temp, name=unquote(url).split('/')[-1])

    def fix_jdate(self, date_str, correct_month):
        for i, t in enumerate(correct_month):
            if t in date_str:
                month_text = date_str[date_str.find(t[0]):date_str.find(t[-2]) + 2]
                return date_str.replace(month_text, f'{i}')

    def create_artist(self, name_en, name_fa=''):
        artist, created = Artist.objects.get_or_create(
            name_en=name_en,
            defaults=dict(name_fa=name_fa)
        )
        if created:
            logger.info(f'>> New Artist Created id:{artist.id} name: {artist.name_en}')
        return artist

    def create_music(self, **kwargs):
        c_music, created = CMusic.objects.get_or_create(
            **kwargs
        )
        if created:
            logger.info(f'>> New Single Music Created id:{c_music} album id: {c_music.album_id}')

    def create_album(self, album_name_en, **kwargs):
        album, created = Album.objects.get_or_create(
            album_name_en=album_name_en,
            defaults=kwargs
        )
        if created:
            logger.info(f'>> New Album Created id: {album.id}')
        return album


class NicMusicCrawler(Crawler):
    website_name = 'nicmusic'
    base_url = 'https://nicmusic.net/'

    def collect_links(self):
        super().collect_links()
        main_page = self.make_request(self.base_url)
        main_soup = BeautifulSoup(main_page.text, "html.parser")
        nav_links = main_soup.find("div", class_="nav-links").find_all("a")
        total_pages = int(nav_links[-2].get_text())
        for i in range(1, total_pages + 1):
            page = requests.get(f"{self.base_url}page/{i}/")
            soup = BeautifulSoup(page.text, "html.parser")
            post_urls_a = soup.find_all("a", class_="show-more")
            for post in post_urls_a:
                yield post.attrs["href"]

    def collect_musics(self):
        super().collect_musics()
        try:
            for url in self.collect_links():
                page = self.make_request(url)
                soup = BeautifulSoup(page.text, "html.parser")
                try:
                    song_name_fa = ""
                    song_name_en = ""
                    artist_name_fa = ""
                    artist_name_en = ""

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
                    post_type_start_index = name_en.index("Download ")
                    artist_name_en = name_en[artist_name_start_index + 2:song_name_start_index].strip().encode().decode(
                        'utf-8-sig')
                    song_name_en = name_en[song_name_start_index + 6:].strip().encode().decode('utf-8-sig')
                    post_type = name_en[post_type_start_index + 9:artist_name_start_index].strip().encode().decode(
                        'utf-8-sig')

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
                    thumbnail = soup.find("img", class_=["size-full", "size-medium"]).attrs["data-src"].encode().decode(
                        'utf-8-sig')
                    publish_date = self.fix_jdate(soup.find("div", class_="times").get_text().strip(), months)
                    publish_date = datetime.strptime(publish_date, '%m %d, %Y')
                    if len(artist_name_en) > 0:
                        kwargs = dict(
                            post_name_url=url,
                            defaults={
                                "title": title,
                                "song_name_fa": song_name_fa,
                                "song_name_en": song_name_en,
                                "post_type": post_type,
                                "lyrics": lyrics,
                                "artist": self.create_artist(artist_name_en, artist_name_fa),
                                "link_mp3_128": quality_128,
                                "link_mp3_320": quality_320,
                                "link_thumbnail": thumbnail,
                                "published_date": publish_date
                            }
                        )
                        self.create_music(**kwargs)
                except Exception as e:
                    logger.error(f'>> 1 collect music {self.website_name}')
                    PrintException()
                    continue
        except Exception as e:
            logger.error(f'>> collect music {self.website_name}')
            PrintException()


class Ganja2MusicCrawler(Crawler):
    website_name = 'ganja2music'
    base_url = 'https://www.ganja2music.com/'

    def collect_links(self):
        """
        Navigating on pages at single musics and collect the detail page of musics.
        :return: Post link of each music to reach a single music
        """
        super().collect_links()

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
        # Thumbnail
        link_thumbnail = soup.find('div', class_='insidercover').find('a').attrs['href']
        return "/".join(filter(None, map(lambda x: str(x).rstrip('/'), (self.base_url, link_thumbnail[1:]))))

    def get_content_section_info(self, soup):
        # Name of Music, Artist and Publish Date
        content_section = soup.find('div', class_='content')
        song_name_en = content_section.find('h2').get_text()
        artist_name_en = content_section.find('div', class_='thisinfo').find('a').get_text()
        publish_date = per_num_to_eng(self.fix_jdate(
            content_section.find('div', class_='feater').find('b').get_text(),
            jalali_months
        ))
        publish_date = datetime.strptime(publish_date, '%m , %d , %Y')
        return song_name_en, artist_name_en, publish_date

    def get_title(self, soup):
        # Title
        title_section = soup.find('div', class_='tinle')
        return f"{title_section.find('b').get_text()} {title_section.find('i').get_text()}"

    def collect_link_singles(self):
        for link in self.collect_post_links('archive/single/'):
            yield link

    def collect_single_musics(self):
        """
        Getting the detail of each Music. collecting all data of musics.
        :return:
        """
        for post_page_url in self.collect_link_singles():
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
                post_name_url=post_page_url,
                defaults=dict(
                    artist=self.create_artist(artist_name_en),  # get or create Artist
                    song_name_en=song_name_en,
                    link_mp3_128=link_128,
                    link_mp3_320=link_320,
                    link_thumbnail=link_thumbnail,
                    lyrics=lyric_text or '',
                    title=title,
                    published_date=publish_date,
                    post_type='single'
                )
            )
            self.create_music(**kwargs)  # get or create CMusic

    def collect_link_albums(self):
        for link in self.collect_post_links('archive/album/'):
            yield link

    def collect_album_musics(self):
        for post_page_url in self.collect_link_albums():
            print(post_page_url)
            soup = BeautifulSoup(self.make_request(post_page_url).text, "html.parser")

            link_128, link_320 = self.get_download_link(soup)  # zip files
            link_thumbnail = self.get_thumbnail(soup)
            album_name_en, artist_name_en, publish_date = self.get_content_section_info(soup)
            title = self.get_title(soup)

            data = dict(
                artist=self.create_artist(name_en=artist_name_en),
                link_mp3_128=link_128,
                link_mp3_320=link_320,
                link_thumbnail=link_thumbnail,
                title=title,
                published_date=publish_date,
            )
            album = self.create_album(album_name_en, **data)

            # getting and creating all musics
            album_musics = soup.find('div', class_='mCSB_5_container').find_all('div', class_='trklines')

            for m in album_musics:
                kwargs = dict(
                    song_name_en=m.find('div', class_='rightf2').get_text(),
                    defaults=dict(
                        link_mp3_128=m.find('div', class_='rightf3 plyiter').find('a').attrs['href'],
                        link_mp3_320=m.find('div', class_='rightf3').find('a').attrs['href'],
                        album=album
                    )
                )
                self.create_music(**kwargs)

    def collect_post_links(self, main_page_url):
        logger.info(f'>> Collect single music links {self.website_name}')

        # Getting the first page musics
        first_page = self.make_request(f"{self.base_url}{main_page_url}")
        soup = BeautifulSoup(first_page.text, "html.parser")
        next_page_link = soup.find('div', class_='pagenumbers').find('a', class_="next page-numbers").attrs['href']
        for post_detail in soup.find_all('div', class_='postbox'):
            yield post_detail.find('a', class_='iaebox').attrs['href']

        # Crawling the next pages
        while next_page_link:
            page = self.make_request(next_page_link)
            soup = BeautifulSoup(page.text, "html.parser")
            for post_detail in soup.find_all('div', class_='postbox'):
                yield post_detail.find('a', class_='iaebox').attrs['href']
            next_page_link = soup.find('div', class_='pagenumbers').find('a', class_="next page-numbers").attrs['href']
            logger.info(f'>>> Next Page URL: {next_page_link}')
