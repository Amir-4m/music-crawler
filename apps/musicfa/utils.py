import json
import os
import logging
from urllib.parse import unquote

from django.conf import settings
from django.core.cache import cache

import requests
from pid import PidFile

logger = logging.getLogger(__file__)
file_handle = None


class UploadTo:
    """
    This class handle the path of each file that download.
    """

    def __init__(self, field_name):
        self.field_name = field_name

    def __call__(self, instance, filename):
        try:
            path = self.path_creator(instance) or f'{filename}'
        except Exception as e:
            logger.error(
                f'[creating file path failed]-[exc: {e}]-[obj id: {instance.id}]-[obj type: {type(instance)}]-[file: {filename}]')
        else:
            path = path.replace(' ', '')
            path = f'crawled/{path}'
            logger.debug(
                f'[saving new file "{path}"]-[obj id: {instance.id}]-[obj type: {type(instance)}]-[file: {filename}]')
            return path

    def path_creator(self, instance):
        """
        thumbnail example url: https://nicmusic.net/wp-content/uploads/***.jpg
        music example url: http://dl.nicmusic.net/nicmusic/024/093/***.mp3
        :param instance: CMusic object.
        :return: Created path from URL of site.
        """
        value = unquote(getattr(instance, f'link_{self.field_name}', ''))
        if value.find('/nicmusic/') != -1:
            return f"{value[value.index('/nicmusic/') + 10:]}"
        elif value.find('/wp-content/') != -1:
            return f"{value[value.index('wp-content/'):]}"
        elif value.find('/Ganja2Music/') != -1:
            return f"{value[value.index('/Ganja2Music/') + 13:]}"
        elif value.find('/Image/') != -1:
            return f"{value[value.index('Image/'):]}"

    def generate_name(self, filename):
        base_filename, file_extension = os.path.splitext(filename)
        return base_filename, file_extension

    def deconstruct(self):
        return 'apps.musicfa.utils.UploadTo', [self.field_name], {}


def url_join(base_url, path):
    return "/".join(filter(None, map(lambda x: str(x).rstrip('/'), (base_url, path))))


def per_num_to_eng(number):
    intab = '۱۲۳۴۵۶۷۸۹۰١٢٣٤٥٦٧٨٩٠'
    outtab = '12345678901234567890'
    translation_table = str.maketrans(intab, outtab)
    return number.translate(translation_table)


def checking_task_status(func_name):
    if os.path.exists('./locks'):
        items = os.listdir('./locks')
        return True if f'{func_name}.pid' in items else False
    return False


def check_running(function_name):
    if not os.path.exists('./locks'):
        os.mkdir('./locks')
    file_lock = PidFile(str(function_name), piddir='./locks')
    try:
        file_lock.create()
        return file_lock
    except:
        return None


def stop_duplicate_task(func):
    def inner_function():
        file_lock = check_running(func.__name__)
        if not file_lock:
            logger.info(f">> [Another {func.__name__} is already running]")
            return False
        func()
        if file_lock:
            file_lock.close()
        return True

    return inner_function


class WordPressClient:
    base_url = settings.WP_BASE_URL
    token_cache_key = 'wordpress_auth_token'
    urls = {
        'token': 'jwt-auth/v1/token',
        'validate-token': 'jwt-auth/v1/token/validate',
        'artist': 'wp/v2/artist/',
        'media': 'wp/v2/media/',
        'album': 'wp/v2/album/',
        'single_music': 'wp/v2/music/',
        'acf_fields_artist': 'acf/v3/artist/',
        'acf_fields_music': 'acf/v3/music/',
        'acf_fields_album': 'acf/v3/album/',
    }

    def __init__(self, instance):
        """
        This class will be used to create post (single music and album) at word press and update ACF fields
         (custom fields).
        Args:
            instance: Instance is CMusic or Album or Artist object.
        """
        logger.debug(f'[sending {type(instance)} to wordpress]-[WP_URL: {self.base_url}]')
        self.thumbnail_download_error = False
        self.instance = instance
        self.token = cache.get(self.token_cache_key) or self.get_token()
        self.validate_token()

    def post_request(self, url, method='post', json_content=None, auth=None, **kwargs):
        headers = {}
        if json_content:
            headers.update({'Content-Type': 'application/json'})
        if auth:
            headers.update({'Authorization': f"Bearer {self.token}"})

        kwargs.update({'headers': headers})
        url = f"{self.base_url + url}"
        try:
            r = requests.request(method, url, **kwargs)
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(
                f'[request failed]-[exc: HTTP ERROR]-[response: {e.response.text}]-[status code: {e.response.status_code}]-[URL: {url}]')
            raise
        except Exception as e:
            logger.error(f"[request failed]-[exc: {e}]-[URL: {url}]")
            raise
        return r

    def get_token(self):
        logger.debug(f"[getting new token]-[URL: {self.urls['token']}]")
        req = self.post_request(
            self.urls['token'],
            json=dict(username=settings.WP_USER, password=settings.WP_PASS),
        )
        if req.ok:
            token = req.json()['data']['token']
            logger.debug(f'[new token successfully added]-[token: {token}]')
            cache.set(self.token_cache_key, token, 604800)  # 7 days default expire time
            return token
        else:
            logger.critical(f'[Getting token failed]-[]')

    def validate_token(self):
        logger.debug(f"[validating the JWT Token]-[URL: {self.urls['validate-token']}]")
        req = self.post_request(
            self.urls['validate-token'],
            auth=True,
        )
        if req.ok:
            logger.debug(f'[Token is valid]')
        else:
            logger.debug(f'[JWT Token of WP is not valid or expired]-[token: {self.token}]')
            self.token = self.get_token()

    def create_artist(self):
        payload_data = dict(
            description=self.instance.description,
            name=self.instance.name_fa,
            slug=self.instance.name_fa,
        )

        req = self.post_request(
            self.urls['artist'],
            json_content=True,
            auth=True,
            json=payload_data,
        )

        if req.ok:
            logger.info(f'[creating artist]-[payload: {payload_data}]-[instance id: {self.instance.id}]')

            wp_id = req.json()['id']
            logger.debug(f'[music posted successfully]-[wordpress id: {wp_id}]')
            self.instance.wp_id = wp_id
            self.instance.save()
            media_id = ''

            if self.instance.file_thumbnail:
                media_id = self.create_media()

            fields = dict(
                acf_fields=dict(
                    artist_image=media_id,
                    about_the_artist=self.instance.description,
                )
            )
            logger.info(f'[updating artist acf fields]-[payload: {fields}]')

            self.update_acf_fields(fields, f"{self.urls['acf_fields_artist']}{wp_id}/")

        else:
            logger.error(f'[creating artist failed]-[obj id: {self.instance.id}]-[status code: {req.status_code}]')
        return req

    def create_single_music(self):
        """
        Create a new Music to Wordpress from CMusic and Album object.
        Returns: None
        """
        from .models import CMusic

        media_id = self.create_media()  # Create media for this music
        payload_data = dict(
            title=f'دانلود آهنگ {self.instance.song_name_fa} از {self.instance.artist.name}',
            content=f"{self.instance.get_artist_info()}\n{self.instance.lyrics}",
            status='publish',  # publish, private, draft, pending, future, auto-draft
            excerpt=self.instance.song_name_en,
            author=9,
            format='standard',
            categories=[self.instance.wp_category_id],
            artist=[self.instance.artist.wp_id],
            featured_media=media_id,
        )
        if 'ganja' in self.instance.page_url:
            payload_data.update(
                dict(slug=f"{self.instance.song_name_fa}-{self.instance.artist.name}")
            )
        else:
            payload_data.update(dict(slug=f"{self.instance.song_name_fa}"))
        req = self.post_request(
            self.urls['single_music'],
            json_content=True,
            auth=True,
            json=payload_data,
        )
        logger.info(f'[create single music]-[payload: {payload_data}]-[instance id: {self.instance.id}]')

        if req.ok:
            post_wp_id = req.json()['id']
            logger.debug(f'[music posted successfully]-[wordpress id: {post_wp_id}]')
            self.update_instance(
                post_wp_id,
                CMusic.APPROVED_STATUS
            )
            # ACF fields of single music
            fields = dict(
                acf_fields=dict(
                    artist_name_persian=self.instance.artist.name_fa,
                    artist_name_english=self.instance.artist.name_en,
                    music_name_persian=self.instance.song_name_fa,
                    music_name_english=self.instance.song_name_en,
                ))
            # 128 link
            if self.instance.file_mp3_128:
                fields['acf_fields']['link_128'] = self.instance.get_absolute_wp_url_128()
            else:
                logger.debug(f'[file_mp3_128 field is empty]-[obj: {self.instance}]')
                fields['acf_fields']['link_128'] = self.download_music_file(
                    self.instance.link_mp3_128, 'file_mp3_128', self.instance
                ).get_absolute_wp_url_128()

            # 320 link
            if self.instance.file_mp3_320:
                fields['acf_fields']['link_320'] = self.instance.get_absolute_wp_url_320()
            else:
                logger.debug(f'[file_mp3_320 field is empty]-[obj: {self.instance}]')
                fields['acf_fields']['link_320'] = self.download_music_file(
                    self.instance.link_mp3_128, 'file_mp3_320', self.instance
                ).get_absolute_wp_url_320()

            logger.info(f'[updating acf fields]-[payload: {fields}]-[instance id: {self.instance.id}]')
            self.update_acf_fields(fields, f"{self.urls['acf_fields_music']}{self.instance.wp_post_id}/")
        else:
            logger.error(
                f'[creating single music post failed]-[obj id: {self.instance.id}]-[status code: {req.status_code}]')

    def create_album(self):
        """
        :return: None
        """
        from .models import Album, CMusic

        # Create media for this album
        media_id = self.create_media()

        musics_link = "".join([
            f"<a href={music.get_absolute_wp_url_320() if music.get_absolute_wp_url_320() else self.download_music_file(music.link_mp3_320, 'file_mp3_320', music).get_absolute_wp_url_320()}>"
            f"{music.song_name_fa or music.song_name_en}</a></br>"
            for music in CMusic.objects.filter(album=self.instance)
        ])  # track's link

        # updating the track's status of this album
        CMusic.objects.filter(album=self.instance).update(status=CMusic.APPROVED_STATUS)

        payload_data = dict(
            title=f'دانلود آلبوم {self.instance.album_name_fa} از {self.instance.artist.name}',
            content=f"{self.instance.get_artist_info()}",
            status='publish',  # publish, private, draft, pending, future, auto-draft
            excerpt=self.instance.album_name_en,
            author=9,
            format='standard',
            artist=[self.instance.artist.wp_id],
            categories=[self.instance.wp_category_id],
            featured_media=media_id
        )
        if 'ganja' in self.instance.page_url:
            payload_data.update(
                dict(slug=f"{self.instance.album_name_fa}-{self.instance.artist.name}")
            )
        else:
            payload_data.update(dict(slug=f"{self.instance.album_name_fa}"))

        req = self.post_request(
            self.urls['album'],
            json_content=True,
            auth=True,
            json=payload_data,
        )
        logger.info(f'[create album music]-[payload: {payload_data}]-[instance id: {self.instance.id}]')

        if req.ok:
            self.update_instance(
                req.json()['id'],
                Album.APPROVED_STATUS
            )

            # ACF fields of album
            fields = dict(
                acf_fields=dict(
                    artist_name_persian=self.instance.artist.name_fa,
                    artist_name_english=self.instance.artist.name_en,
                    music_name_persian=self.instance.album_name_fa,
                    music_name_english=self.instance.album_name_en,
                    album_link=musics_link
                ))
            logger.info(f'[updating acf fields]-[payload: {fields}]-[instance id: {self.instance.id}]')

            self.update_acf_fields(fields, f"{self.urls['acf_fields_album']}{self.instance.wp_post_id}/")

    def create_media(self):
        from .crawler import Crawler

        """
        Create a new Media object in Wordpress site to assign it to Wordpress Post as a `featured_media`.
        this media will create with thumbnail_file field at CMusic or Album if this field is empty
        this method will download it.
        Returns: media's id of uploaded image to wordpress site
        """
        if self.instance.file_thumbnail:
            file_name = self.instance.file_thumbnail.name.split('/')[-1]
            payload_data = dict(status='draft')
            req = self.post_request(
                self.urls['media'],
                auth=True,
                data={'file': file_name, 'data': json.dumps(payload_data)},
                files={'file': (
                    file_name,
                    open(self.instance.file_thumbnail.path, 'rb'),
                    f'image/{file_name.split(".")[-1]}',
                    {'Expires': '0'}
                )},
            )
            media_id = req.json()['id']
            logger.debug(f'[media uploaded]-[instance id: {self.instance.id}]-[media id: {media_id}]')
            return media_id
        else:
            logger.debug(
                f'[creating media failed]-[obj: {self.instance}]-[err: (thumbnail) has no file '
                f' associated with it]'
            )
            logger.debug(f'[downloading thumbnail file...]-[obj: {self.instance}]')

            # downloading the thumbnail
            self.instance.file_thumbnail = Crawler.download_content(self.instance.link_thumbnail)
            try:
                self.instance.save()
            except Exception as e:
                logger.error(f'[Downloading thumbnail file failed]-[obj: {self.instance}] = [{e}]')
            else:
                if not self.thumbnail_download_error:
                    self.thumbnail_download_error = True  # adding this to break the possible loop
                    return self.create_media()

    def download_music_file(self, url, field_name, instance):
        from .crawler import Crawler

        logger.debug(f'[downloading {field_name}]-[obj: {instance}]-[URL: {url}] ')
        file = Crawler.download_content(url)
        setattr(instance, field_name, file)
        try:
            instance.save()
            return instance
        except Exception:
            logger.error(f'[downloading music file failed]-[obj: {instance}]-[URL: {url}]')

    def update_instance(self, wp_id, status, **kwargs):
        self.instance.wp_post_id = wp_id
        self.instance.status = status
        self.instance.save()

    def update_acf_fields(self, fields, url):
        req = self.post_request(
            url,
            method='put',
            json_content=True,
            auth=True,
            json=fields,
        )
        if req.ok:
            logger.debug(f'[ACF field updated successfully]-[instance id: {self.instance.id}]')
        else:
            logger.error(
                f'[updating the ACF fields failed]-[instance id: {self.instance.id}]-[status code: {req.status_code}]')


def delete_empty_albums():
    from .models import Album

    Album.objects.filter(cmusic__isnull=True).delete()


def fix_link_128():
    from .models import CMusic

    for c in CMusic.objects.filter(
            page_url__icontains='ganja'
    ).exclude(
        link_mp3_128__icontains='ganja'
    ):
        if len(c.link_mp3_128) > 0:
            correct_link = c.link_mp3_320
            print(c.id)
            print("page url ", c.page_url)
            print("320 link", c.link_mp3_320)
            correct_link.replace('Archive/', 'Archive/128/')
            correct_link.replace(correct_link[correct_link.find('Single/'):], c.link_mp3_128)
            print("128 link", c.link_mp3_128)
            c.link_mp3_128 = correct_link
            print("corrected link", c.link_mp3_128, '\n')
            # c.save()
        else:
            print("Empty 128 link")


class PersianNameHandler:

    @staticmethod
    def get_name_fa(m):
        """
        :param m: CMusic or Album obj.
        :return: name_fa field.
        """
        try:
            name_fa = m.title_tag.split('|')[1].replace('آهنگ جدید', '').strip()
        except IndexError:
            name_fa = ''

        name_fa_len = len(name_fa)
        for correct_name in m.artist.correct_names + [m.artist.name_fa, m.artist.name_en]:
            name_fa = name_fa.replace(correct_name, '')  # removing the name of artist if find it

        if len(name_fa) == name_fa_len:
            name_fa = ''
        return name_fa

    @staticmethod
    def update_single_musics(musics):
        from .models import CMusic

        # musics = queryset.filter(song_name_fa='')
        for m in musics:
            if m.post_type == CMusic.SINGLE_TYPE:
                m.song_name_fa = PersianNameHandler.get_name_fa(m)  # updating this field
                try:
                    m.song_name_en = m.song_name_en.split('-')[1].strip()
                except Exception:
                    pass

            # if m.post_type == CMusic.ALBUM_MUSIC_TYPE:
            # m.song_name_fa = f2p(m.song_name_en)
            # m.title = f'{m.song_name_fa}-{m.artist.name}'

        CMusic.objects.bulk_update(musics, ['song_name_fa', 'song_name_en', 'updated_time'])
        return musics.count()

    @staticmethod
    def update_albums(albums):
        from .models import Album

        # albums = queryset.filter(album_name_fa='')
        for a in albums:
            a.album_name_fa = PersianNameHandler.get_name_fa(a)  # updating this field

        Album.objects.bulk_update(albums, ['album_name_fa', 'updated_time'])
        return albums.count()

    @staticmethod
    def update_artists(artists):
        from .models import Artist
        from finglish import f2p

        # artists = queryset.filter(name_fa='')
        for a in artists:
            a.name_fa = f2p(a.name_en)

        Artist.objects.bulk_update(artists, ['name_fa', 'updated_time'])
        return artists.count()


def update_artists_by_wordpress():
    from .models import Artist
    import csv
    result = []
    with open('Artist-Export-2021-May-09-121222.csv') as f:
        file = csv.DictReader(f)
        for i, row in enumerate(file):

            try:
                a = Artist.objects.get(name_fa=row['Term Name'])
            except (Artist.DoesNotExist, Artist.MultipleObjectsReturned):
                pass

            a.wp_id = row['Term ID']
            result.append(a)

    Artist.objects.bulk_update(result, ['wp_id', 'updated_time'])


def update_title_tag_field_ganja2(limit):
    import requests
    from apps.musicfa.models import CMusic, Album
    from bs4 import BeautifulSoup

    # updating musics
    musics = CMusic.objects.filter(
        page_url__contains='ganja2',
        post_type=CMusic.SINGLE_TYPE,
        title_tag=''
    )[:limit]

    for m in musics:
        req = requests.get(m.page_url)
        soup = BeautifulSoup(req.text, "html.parser")
        title_tag = soup.find('title').get_text()
        m.title_tag = title_tag
        logger.debug(
            f'[updating title_tag music field]-[obj id:{m.id}]-[status code: {req.status_code}]-'
            f'[title: {title_tag}]-[url:{m.page_url}]'
        )

    CMusic.objects.bulk_update(musics, ['updated_time', 'title_tag'])

    # updating albums
    albums = Album.objects.filter(
        page_url__contains='ganja2',
        title_tag=''
    )[:limit]
    for a in albums:
        req = requests.get(a.page_url)
        soup = BeautifulSoup(req.text, "html.parser")
        title_tag = soup.find('title').get_text()
        a.title_tag = title_tag
        logger.debug(
            f'[updating title_tag album field]-[obj id:{a.id}]-[status code: {req.status_code}]-'
            f'[title: {title_tag}]-[url:{a.page_url}]'
        )

    Album.objects.bulk_update(albums, ['updated_time', 'title_tag'])


def update_artist_bio_image():
    import csv

    from apps.musicfa.models import Artist
    from apps.musicfa.crawler import Crawler

    with open('artists_bio_and_image.csv') as f:
        file = csv.DictReader(f)
        for i, row in enumerate(file):
            try:
                a = Artist.objects.get(wp_id=row['artist_id'])
                a.description = row['about_the_artist']
                a.file_thumbnail = Crawler.download_content(row['artist_image'])
                a.save()
            except (Artist.DoesNotExist, Artist.MultipleObjectsReturned):
                print('ERROR, \n')
