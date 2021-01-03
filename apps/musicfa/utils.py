import json
import os
import linecache
import sys
import logging
from urllib.parse import unquote

from django.conf import settings
from django.core.cache import cache

import requests
from pid import PidFile
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__file__)


class UploadTo:
    """
    This class handle the path of each file that download.
    """

    def __init__(self, field_name):
        self.field_name = field_name

    def __call__(self, instance, filename):
        path = self.path_creator(instance) or f'{filename}'
        path = path.replace(' ', '')
        logger.info(f'>> New file saved in "{path}"')
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


def PrintException():
    """
    Print the exception cause and errors
    :return:
    """
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    logger.error('>> EXCEPTION IN ({}, LINE {} "{}"):\n {}'.format(filename, lineno, line.strip(), exc_obj))


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
    """
    By checking the PID file if file is exist will return False and do not execute (it's mean `func` is already
     running), will return True if file does not exist and will create the PID file.
    :param func: function.__name__ will be used to stop duplicate tasks.
    :return: True or False
    """

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
    base_url = 'https://test.delnava.com/wp-json/'
    token_cache_key = 'wordpress_auth_token'
    urls = {
        'token': 'jwt-auth/v1/token',
        'validate-token': 'jwt-auth/v1/token/validate',
        'media': 'wp/v2/media/',
        'album': 'wp/v2/album/',
        'single_music': 'wp/v2/music/',
        'acf_fields_music': 'acf/v3/music/',
        'acf_fields_album': 'acf/v3/album/'
    }

    def __init__(self, instance):
        """
        This class will be used to create post (single music and album) at word press and update ACF fields
         (custom fields).
        Args:
            instance: Instance is CMusic or Album object.
        """
        self.instance = instance
        self.token = cache.get(self.token_cache_key) or self.get_token()
        self.validate_token(self.token)

    def post_request(self, url, method='post', json_content=None, auth=None, **kwargs):
        headers = {}
        if json_content:
            headers.update({'Content-Type': 'application/json'})
        if auth:
            headers.update({'Authorization': f"Bearer {self.token}"})

        kwargs.update({'headers': headers})
        return requests.request(
            method,
            f"{self.base_url + url}",
            **kwargs
        )

    def get_token(self):
        logger.info('>> getting new token')
        req = self.post_request(
            self.urls['token'],
            json=dict(username=settings.WP_USER, password=settings.WP_PASS),
        )
        if req.ok:
            token = req.json()['data']['token']
            logger.info(f'>> new token successfully added token: {token}')
            cache.set(self.token_cache_key, token, 604800)  # 7 days default expire time
            return token
        else:
            logger.critical(f'>> Getting token failed. user: {settings.WP_USER} pass: {settings.WP_PASS}')

    def validate_token(self, token):
        req = self.post_request(
            self.urls['validate-token'],
            auth=True,
        )
        if req.ok:
            logger.info(f'>> token is valid.')
        else:
            logger.error(f'>> token is not valid')

    def create_single_music(self):
        """
        Create a new Music to Wordpress from CMusic and Album object.
        Returns: None
        """
        from .models import CMusic

        media_id = self.create_media()  # Create media for this music
        payload_data = dict(
            title=self.instance.title,
            content=f"{self.instance.get_artist_info()}\n{self.instance.lyrics}",
            slug=self.instance.song_name_en,
            status='publish',  # publish, private, draft, pending, future, auto-draft
            excerpt=self.instance.song_name_en,
            author=9,
            format='standard',
            categories=[self.instance.wp_category_id],
            featured_media=media_id,
        )
        req = self.post_request(
            self.urls['single_music'],
            json_content=True,
            auth=True,
            json=payload_data,
        )
        if req.ok:
            post_wp_id = req.json()['id']
            logger.info(f'>> Music posted successfully! wordpress id: {post_wp_id}')
            self.update_instance(
                post_wp_id,
                CMusic.APPROVED_STATUS
            )

            # ACF fields of single music
            fields = dict(
                fields=dict(
                    artist_name_persian=self.instance.artist.name_fa,
                    artist_name_english=self.instance.artist.name_en,
                    music_name_persian=self.instance.song_name_fa,
                    music_name_english=self.instance.song_name_en,
                ))
            if self.instance.file_mp3_128:
                fields['fields']['link_128'] = url_join(settings.SITE_DOMAIN, self.instance.file_mp3_128)
            if self.instance.file_mp3_320:
                fields['fields']['link_320'] = url_join(settings.SITE_DOMAIN, self.instance.file_mp3_320)
            self.update_acf_fields(fields, f"{self.urls['acf_fields_music']}{self.instance.wp_post_id}/")
        else:
            logger.error(f'>> Create Music post failed! CMusic id: {self.instance.id} status code: {req.status_code}')

    def create_album(self):
        """
        :return: None
        """
        from .models import Album, CMusic

        # Create media for this album
        first_music = self.instance.cmusic_set.first()
        media_id = self.create_media()

        musics_link = "".join([
            f"<a href={music.get_absolute_url_320()}>{music.song_name_fa or music.song_name_en}</a></br>"
            for music in CMusic.objects.filter(album=self.instance)
        ])  # track's link

        payload_data = dict(
            title=self.instance.title,
            content=f"{self.instance.get_artist_info()}",
            slug=self.instance.album_name_en,
            status='publish',  # publish, private, draft, pending, future, auto-draft
            excerpt=self.instance.album_name_en,
            author=9,
            format='standard',
            categories=[self.instance.wp_category_id],
            featured_media=media_id
        )
        req = self.post_request(
            self.urls['album'],
            json_content=True,
            auth=True,
            json=payload_data,
        )
        if req.ok:
            self.update_instance(
                req.json()['id'],
                Album.APPROVED_STATUS
            )

            # ACF fields of album
            fields = dict(
                fields=dict(
                    artist_name_persian=self.instance.artist.name_fa,
                    artist_name_english=self.instance.artist.name_en,
                    music_name_persian=first_music.song_name_fa,
                    music_name_english=first_music.song_name_en,
                    album_link=musics_link  # TODO fix the field
                ))

            self.update_acf_fields(fields, f"{self.urls['acf_fields_album']}{self.instance.wp_post_id}/")

    def create_media(self):
        """
        Create a new Media object in Wordpress site to assign it to Wordpress Post.

        Returns: media's id of uploaded image to wordpress site
        """
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
        if req.ok:
            return req.json()['id']

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
            logger.info(f'>> ACF field updated successfully wordpress id: {self.instance.wp_post_id}')
        else:
            logger.error(
                f'>> ACF Field update failed! wordpress id: {self.instance.wp_post_id}, status code: {req.status_code}')
