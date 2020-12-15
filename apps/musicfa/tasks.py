from celery.task import periodic_task
from celery.schedules import crontab

from .crawler import MusicfaCrawler


@periodic_task(run_every=crontab(hour="*/6"))
def collect_musics():
    MusicfaCrawler().collect_musics()


@periodic_task(run_every=crontab(hour="*/10"))
def collect_musics():
    MusicfaCrawler().collect_files()

