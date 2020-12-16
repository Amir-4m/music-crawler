from django.db import models
from django.utils.translation import ugettext_lazy as _

from .utils import UploadTo


class CMusic(models.Model):
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    published_date = models.DateField(_("published date"), max_length=20)

    title = models.CharField(_("title"), max_length=300)
    song_name_fa = models.CharField(_("song name in fa"), max_length=200)
    song_name_en = models.CharField(_("song name in en"), max_length=200)

    lyrics = models.TextField(_("lyrics"), blank=True, null=True)

    post_name_url = models.CharField(_("post name url"), max_length=300, unique=True)
    post_type = models.CharField(_("post type"), max_length=100)

    artist_name_fa = models.CharField(_("artist name in fa"), max_length=200)
    artist_name_en = models.CharField(_("artist name in en"), max_length=200)

    link_mp3_128 = models.TextField(_("quality of 128 mp3 link"))
    link_mp3_320 = models.TextField(_("quality of 320 mp3 link"))
    link_thumbnail = models.TextField(_("link thumbnail"))

    is_downloaded = models.BooleanField(_('is downloaded'), default=False)
    file_mp3_128 = models.FileField(_('file mp3 128'), upload_to=UploadTo('mp3_128'), null=True, blank=True)
    file_mp3_320 = models.FileField(_('file mp3 320'), upload_to=UploadTo('mp3_320'), null=True, blank=True)
    file_thumbnail = models.ImageField(_("file thumbnail photo"), upload_to=UploadTo('thumbnail'), null=True, blank=True)

    def __str__(self):
        return self.title

