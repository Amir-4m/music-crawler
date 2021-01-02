from importlib import import_module

from celery import shared_task
from celery.task import periodic_task
from celery.schedules import crontab

from .crawler import NicMusicCrawler, Ganja2MusicCrawler
from .utils import stop_duplicate_task, WordPressClient
from .models import CMusic, Album


@shared_task
def create_single_music_post_task(object_ids):
    """
    Creating a post (single music) on Word press from CMusic object
    :param object_ids: list of CMusic's id object
    :return: None
    """
    for q in CMusic.objects.filter(id__in=object_ids):
        WordPressClient(q).create_single_music()


@shared_task
def create_album_post_task(object_ids):
    """
    Creating a post (album) on Word press from Album and CMusic object
    :param object_ids: list of Album's id object
    :return: None
    """
    for q in Album.objects.get(id__in=object_ids):
        WordPressClient(q).create_single_music()


@shared_task
def run_crawl(func_name):
    """
    Getting an name of function to start crawling.
    This task could call from `change_list` of CMusic.
    :param func_name:  `collect_musics_nic` or `collect_musics_ganja` an function name from this module
    :return: None
    """
    module = import_module('apps.musicfa.tasks')
    getattr(module, func_name)()  # Starting Crawl


@periodic_task(run_every=crontab(hour="*/24", minute=0))
def periodic_crawler_ganja():
    collect_musics_ganja()


@periodic_task(run_every=crontab(hour="*/24", minute=0))
def periodic_crawler_nic():
    collect_musics_nic()


@stop_duplicate_task
def collect_musics_nic():
    NicMusicCrawler().collect_musics()  # start collecting single music
    collect_files_nic()


@stop_duplicate_task
def collect_musics_ganja():
    Ganja2MusicCrawler().collect_musics()  # start collecting both album and single music
    collect_files_ganja()


@stop_duplicate_task
def collect_files_nic():
    NicMusicCrawler().collect_files()


@stop_duplicate_task
def collect_files_ganja():
    Ganja2MusicCrawler().collect_files()
