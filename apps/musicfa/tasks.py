from celery import shared_task
from celery.task import periodic_task
from celery.schedules import crontab

from .crawler import NicMusicCrawler, Ganja2MusicCrawler
from .utils import stop_duplicate_task


# @periodic_task(run_every=crontab(hour="*/6"))
@shared_task
@stop_duplicate_task
def collect_musics_nic():
    NicMusicCrawler().collect_musics()
    collect_files_nic.delay()


# @periodic_task(run_every=crontab(hour="*/10"))
@shared_task
@stop_duplicate_task
def collect_files_nic():
    NicMusicCrawler().collect_files()


@shared_task
@stop_duplicate_task
def collect_musics_ganja():
    Ganja2MusicCrawler().collect_files()


@shared_task
@stop_duplicate_task
def collect_files_ganja():
    Ganja2MusicCrawler().collect_files()
