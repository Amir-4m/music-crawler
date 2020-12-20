from django.db import models
from django.utils.translation import ugettext_lazy as _

from .utils import UploadTo


class Album(models.Model):
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    published_date = models.DateField(_("published date"), max_length=20)

    album_name_en = models.CharField(_("album name en"), max_length=250)
    site_id = models.CharField(_('album site id'), max_length=50, unique=True)

    title = models.CharField(_("title"), max_length=250)

    artist_name_fa = models.CharField(_("artist name in fa"), max_length=200)
    artist_name_en = models.CharField(_("artist name in en"), max_length=200)

    page_url = models.TextField(_('url field'))
    link_thumbnail = models.TextField(_("link thumbnail"))
    link_mp3_128 = models.TextField(_("quality of 128 mp3 link"))
    link_mp3_320 = models.TextField(_("quality of 320 mp3 link"))

    def __str__(self):
        return f"{self.title} {self.id}"


class CMusic(models.Model):
    SINGLE_TYPE = 'single'
    ALBUM_MUSIC_TYPE = 'album-music'

    POST_TYPE_CHOICE = (
        (SINGLE_TYPE, _('single')),
        (ALBUM_MUSIC_TYPE, _('album-music'))
    )

    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    published_date = models.DateField(_("published date"), max_length=20)

    title = models.CharField(_("title"), max_length=250, blank=True)
    lyrics = models.TextField(_("lyrics"), blank=True)
    song_name_fa = models.CharField(_("song name in fa"), max_length=200, blank=True)
    song_name_en = models.CharField(_("song name in en"), max_length=200)

    artist_name_fa = models.CharField(_("artist name in fa"), max_length=200, blank=True)
    artist_name_en = models.CharField(_("artist name in en"), max_length=200, blank=True)

    album = models.ForeignKey('Album', on_delete=models.CASCADE, verbose_name=_('album'), null=True, blank=True)

    post_name_url = models.CharField(_("post name url"), max_length=300, unique=True)
    post_type = models.CharField(_("post type"), max_length=20, choices=POST_TYPE_CHOICE)
    site_id = models.CharField(_('album site id'), max_length=50, unique=True, null=True)

    link_mp3_128 = models.TextField(_("quality of 128 mp3 link"), blank=True)
    link_mp3_320 = models.TextField(_("quality of 320 mp3 link"), blank=True)
    link_thumbnail = models.TextField(_("link thumbnail"), blank=True)

    is_downloaded = models.BooleanField(_('is downloaded'), default=False)
    file_mp3_128 = models.FileField(
        _('file mp3 128'), upload_to=UploadTo('mp3_128'), null=True, blank=True, max_length=150
    )
    file_mp3_320 = models.FileField(
        _('file mp3 320'), upload_to=UploadTo('mp3_320'), null=True, blank=True, max_length=150
    )
    file_thumbnail = models.ImageField(
        _("file thumbnail photo"), upload_to=UploadTo('thumbnail'), null=True, blank=True
    )

    def __str__(self):
        return f"{self.title} {self.id}"
