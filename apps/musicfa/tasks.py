import logging

from celery.task import periodic_task
from celery.schedules import crontab
from django.utils import timezone

from .crawler import NicMusicCrawler, Ganja2MusicCrawler
from .utils import check_running, close_running

logger = logging.getLogger(__name__)


@periodic_task(run_every=crontab(hour="*/6"))
def collect_musics_nic():
    NicMusicCrawler().collect_musics()


@periodic_task(run_every=crontab(hour="*/10"))
def collect_files_nic():
    file_lock = check_running(collect_musics_nic.__name__)
    if not file_lock:
        logger.info(
            "[Another {} is already running]".format(
                collect_musics_nic.__name__
            )
        )
        return False
    NicMusicCrawler().collect_files()
    if file_lock:
        close_running(file_lock)
    return True


@periodic_task(run_every=crontab(hour="*/6"))
def collect_musics_ganja():
    pass


@periodic_task(run_every=crontab(hour="*/6"))
def collect_files_ganja():
    file_lock = check_running(collect_musics_nic.__name__)
    if not file_lock:
        logger.info(
            "[Another {} is already running]".format(
                collect_musics_nic.__name__
            )
        )
        return False
    Ganja2MusicCrawler().collect_files()
    if file_lock:
        close_running(file_lock)
    return True
