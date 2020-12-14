from celery.task import periodic_task
from celery.schedules import crontab


@periodic_task(run_every=crontab(hour="*/6"))
def collect_musics():
    pass

