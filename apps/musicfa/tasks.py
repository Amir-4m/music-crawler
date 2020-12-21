from importlib import import_module

from celery import shared_task

from .crawler import NicMusicCrawler, Ganja2MusicCrawler
from .utils import stop_duplicate_task


@shared_task
def run_crawl(func_name):
    module = import_module('apps.musicfa.tasks')
    getattr(module, func_name)()  # Starting Crawl


@stop_duplicate_task
def collect_musics_nic():
    NicMusicCrawler().collect_musics()
    collect_files_nic()


@stop_duplicate_task
def collect_files_nic():
    NicMusicCrawler().collect_files()


@stop_duplicate_task
def collect_musics_ganja():
    Ganja2MusicCrawler().collect_musics()
    collect_files_ganja()


@stop_duplicate_task
def collect_files_ganja():
    Ganja2MusicCrawler().collect_files()
