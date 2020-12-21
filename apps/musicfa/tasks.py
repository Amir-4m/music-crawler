import logging

from celery import shared_task
from celery.task import periodic_task
from celery.schedules import crontab
from django.utils import timezone

from .crawler import NicMusicCrawler, Ganja2MusicCrawler
from .utils import stop_duplicate_task

logger = logging.getLogger(__name__)


# @periodic_task(run_every=crontab(hour="*/6"))
@shared_task
@stop_duplicate_task
def collect_musics_nic():
    NicMusicCrawler().collect_musics()
    collect_files_nic.delay()


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


