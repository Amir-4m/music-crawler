from urllib.parse import urlparse

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_better_admin_arrayfield.models.fields import ArrayField

from .utils import UploadTo, url_join


class Artist(models.Model):
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)

    wp_id = models.CharField(_('wordpress id'), max_length=30, blank=True)

    name_en = models.CharField(_('full name en'), max_length=150, unique=True)
    name_fa = models.CharField(_('full name fa'), max_length=150, blank=True)

    note = models.CharField(_('note'), max_length=150, blank=True)
    description = models.TextField(_('bio'), blank=True)

    is_approved = models.BooleanField(_('is approved'), default=False)
    correct_names = ArrayField(models.CharField(max_length=150), verbose_name=_('correct names'), null=True)

    file_thumbnail = models.ImageField(
        _("file thumbnail photo"), upload_to=UploadTo('thumbnail'), null=True, blank=True
    )

    @property
    def name(self):
        return self.name_fa or self.name_en or self.id

    def __str__(self):
        return self.name


class Album(models.Model):
    VOID_STATUS = 'void'
    JUNK_STATUS = 'junk'
    EDITABLE_STATUS = 'editable'
    APPROVED_STATUS = 'approved'
    STATUS_CHOICES = (
        (VOID_STATUS, _('void')),
        (JUNK_STATUS, _('junk')),
        (EDITABLE_STATUS, _('editable')),
        (APPROVED_STATUS, _('approved')),
    )

    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    published_date = models.DateField(_("published date"), max_length=20)

    title = models.CharField(_("title"), max_length=250, blank=True)
    title_tag = models.CharField(_('title tag'), max_length=150, blank=True)

    album_name_en = models.CharField(_("album name en"), max_length=250, blank=True)
    album_name_fa = models.CharField(_("album name fa"), max_length=250, blank=True)

    artist = models.ForeignKey('Artist', on_delete=models.CASCADE, verbose_name=_('artist'), blank=True)

    page_url = models.TextField(_('page url'))
    site_id = models.CharField(_('album site id'), max_length=50, unique=True, blank=True)

    link_thumbnail = models.TextField(_("link thumbnail"))
    link_mp3_128 = models.TextField(_("quality of 128 mp3 link"), blank=True)
    link_mp3_320 = models.TextField(_("quality of 320 mp3 link"), blank=True)

    is_downloaded = models.BooleanField(_('is downloaded'), default=False)
    file_thumbnail = models.ImageField(
        _("file thumbnail photo"), upload_to=UploadTo('thumbnail'), null=True, blank=True
    )

    status = models.CharField(_('status'), max_length=8, choices=STATUS_CHOICES, default=VOID_STATUS)
    wp_category_id = models.PositiveSmallIntegerField(_('category'), blank=True)
    wp_post_id = models.PositiveIntegerField(_('wordpress post id'), blank=True, null=True)

    @property
    def name(self):
        return self.album_name_fa or self.album_name_en or str(self.id)

    @property
    def website_name(self):
        return urlparse(self.page_url).netloc

    def __str__(self):
        return self.name

    def get_artist_info(self):
        return f"{self.artist.name_fa}\n{self.artist.name_en}"


class CMusic(models.Model):
    SINGLE_TYPE = 'single'
    ALBUM_MUSIC_TYPE = 'album-music'
    POST_TYPE_CHOICE = (
        (SINGLE_TYPE, _('single')),
        (ALBUM_MUSIC_TYPE, _('album-music'))
    )

    VOID_STATUS = 'void'
    JUNK_STATUS = 'junk'
    EDITABLE_STATUS = 'editable'
    APPROVED_STATUS = 'approved'
    STATUS_CHOICES = (
        (VOID_STATUS, _('void')),
        (JUNK_STATUS, _('junk')),
        (EDITABLE_STATUS, _('editable')),
        (APPROVED_STATUS, _('approved')),
    )

    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    published_date = models.DateField(_("published date"), max_length=20)

    title = models.CharField(_("title"), max_length=250, blank=True)
    title_tag = models.CharField(_('title tag'), max_length=150, blank=True)
    lyrics = models.TextField(_("lyrics"), blank=True)
    song_name_fa = models.CharField(_("song name in fa"), max_length=200, blank=True)
    song_name_en = models.CharField(_("song name in en"), max_length=200)

    album = models.ForeignKey('Album', on_delete=models.CASCADE, verbose_name=_('album'), null=True, blank=True)
    artist = models.ForeignKey('Artist', on_delete=models.CASCADE, verbose_name=_('artist'))

    page_url = models.TextField(_("post url"), blank=True)
    post_type = models.CharField(_("post type"), max_length=20, choices=POST_TYPE_CHOICE)
    site_id = models.CharField(_('album site id'), max_length=60, unique=True)

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

    status = models.CharField(_('status'), max_length=8, choices=STATUS_CHOICES, default=VOID_STATUS)
    wp_category_id = models.PositiveSmallIntegerField(_('category'), blank=True)
    wp_post_id = models.PositiveIntegerField(_('wordpress post id'), blank=True, null=True)

    @property
    def name(self):
        return self.song_name_fa or self.song_name_en or str(self.id)

    @property
    def website_name(self):
        return urlparse(self.page_url).netloc

    def __str__(self):
        return f"{self.name}"

    def get_artist_info(self):
        return f"{self.artist.name_fa}\n{self.artist.name_en}"

    def get_absolute_wp_url_128(self):
        if self.file_mp3_128:
            return url_join(settings.FTP_MEDIA_URL, self.file_mp3_128.url[14:])

    def get_absolute_wp_url_320(self):
        if self.file_mp3_320:
            return url_join(settings.FTP_MEDIA_URL, self.file_mp3_320.url[14:])
