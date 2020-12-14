import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from khayyam import JalaliDate

from .models import CrawledMusic

jalali_months = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
months = ["ژانویه", "فوریه", "مارس", "آوریل", "می", "ژوئن", "جولای", "آگوست", "سپتامبر", "اکتبر", "نوامبر", "دسامبر"]
alpha = "A aB bC cD dE eF fG gH hI iJ jK kL lM mN nO oP pQ qR rS sT tU uV vW wX xY yZ z"

logger = logging.getLogger(__name__)


class Crawler:
    website_name = ''

    def collect_links(self):
        raise NotImplementedError()

    def collect_musics(self):
        raise NotImplementedError()

    # def download_image(self, url):
    #     """
    #     Args:
    #         url: url of news image that takes from page
    #         defaults: data for create a new field
    #
    #     Returns: Image <django.core.files.File> to save in ImageField <news_image>
    #     """
    #     r = requests.get(url, allow_redirects=False)
    #     img_temp = NamedTemporaryFile(delete=True)
    #     img_temp.write(r.content)
    #     img_temp.flush()  # deleting the file from RAM
    #     return File(img_temp, name=url.split('/')[-1])


class MusicfaCrawler(Crawler):
    website_name = 'music-fa'

    def __init__(self):
        print(f'Starting crawler for {self.website_name}')
        logger.info(f'Starting crawler for {self.website_name}')

    def collect_links(self):
        logger.info(f'{self.website_name} collect links starting...')
        main_page = requests.get("https://nicmusic.net/")
        main_soup = BeautifulSoup(main_page.text, "html.parser")
        nav_links = main_soup.find("div", class_="nav-links").find_all("a")
        total_pages = int(nav_links[-2].get_text())
        for i in range(1, total_pages + 1):
            page = requests.get(f"https://nicmusic.net/page/{i}/")
            soup = BeautifulSoup(page.text, "html.parser")
            post_urls_a = soup.find_all("a", class_="show-more")
            for post in post_urls_a:
                yield post.attrs["href"]

    def collect_musics(self):
        try:
            for url in self.collect_links():
                page = requests.get(url)
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

                    # if len(names) > 1:
                    #     if names[1].get_text() not in artist_name_fa:
                    #         song_name_fa = names[1].get_text()
                    #
                    # if len(song_name_fa) == 0 or song_name_fa[0] in alpha:
                    #     song_name_fa = None

                    song_name_fa_start_index = title.index("به نام")
                    song_name_fa = title[song_name_fa_start_index + 6:].strip().encode().decode('utf-8-sig')

                    if len(artist_name_fa) == 0 or artist_name_fa[0] in alpha:
                        # artist_name_fa = None
                        names2 = names[2].get_text()
                        if names2[0] not in alpha:
                            artist_name_fa = names[2].get_text()

                    # if artist_name_fa is None:
                    #     names2 = names[2].get_text()
                    #     if names2[0] not in alpha:
                    #         artist_name_fa = names[2].get_text()

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

                    publish_date = soup.find("div", class_="times").get_text().strip().replace(",", "").split(" ")
                    greek_published_date = str(
                        datetime(int(publish_date[2]), months.index(publish_date[0]) + 1, int(publish_date[1])).date())
                    # published_date_jalali_date = JalaliDate(datetime(int(publish_date[2]),
                    #                                                  months.index(publish_date[0]) + 1,
                    #                                                  int(publish_date[1])))
                    #
                    # published_date_jalali_str = str(published_date_jalali_date).split("-")
                    # publish_date_jalali = f"{int(published_date_jalali_str[2])}/{int(published_date_j
                    # alali_str[1])}/{int(published_date_jalali_str[0])}"
                    if len(artist_name_en) > 0:
                        music, created = CrawledMusic.objects.get_or_create(
                            post_name_url=url,
                            defaults={
                                "title": title,
                                "song_name_fa": song_name_fa,
                                "song_name_en": song_name_en,
                                "post_type": post_type,
                                "lyrics": lyrics,
                                "artist_name_fa": artist_name_fa,
                                "artist_name_en": artist_name_en,
                                "link_mp3_128": quality_128,
                                "link_mp3_320": quality_320,
                                "thumbnail_photo": thumbnail,
                                "published_date": greek_published_date
                            }
                        )
                        logger.info(f"{self.website_name} Song Created... post_url: {url}")
                except Exception as e:
                    logger.error(f'collect music {self.website_name} >>> inner{e}')
                    continue
        except Exception as e:
            logger.error(f'collect music {self.website_name} >>> inner{e}')

    def collect_musicfa_singers_pages(self):
        url = "https://music-fa.com"
        page = requests.get(url)
        soup = BeautifulSoup(page.text, "html.parser")

        singer_list = soup.find_all("div", class_="box_body")[4].find_all("li")

        singers_page_url = []
        for li in singer_list:
            singers_page_url.append(li.find("a").attrs["href"])

        return singers_page_url

    def last_page(self):
        url = "https://music-fa.com/"
        page = requests.get(url)
        soup = BeautifulSoup(page.text, "html.parser")
        last_page_url = soup.find("div", class_="pagination cf").find_all("a")[-1].attrs["href"]
        last_page_number = int(last_page_url.split("/")[-2])
        return last_page_number + 1

    def collect_full_album_urls(self):
        url = "https://iran-music.net/download-full-album-in-one/"
        page = requests.get(url)
        soup = BeautifulSoup(page.text, "html.parser")

        full_album_list = soup.find("div", class_="iranthemes_center").find("ul").find_all("li")
