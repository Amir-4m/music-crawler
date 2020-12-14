from django.db import models
from django.utils.translation import ugettext_lazy as _

from .utils import UploadTo

# title,description,post_name_url,status,post_type,category_fa,category_en,artist_name,link_mp3_one,link_mp3_two,link_mp3_three,thumbnail_photo
# class Music(models.Model):
#     created_time = models.DateTimeField(_('created time'), auto_now_add=True)
#     updated_time = models.DateTimeField(_('updated time'), auto_now=True)
#     song_site_id = models.BigIntegerField(_("song site id"))
#     title = models.CharField(_("title"), max_length=300)
#     song_name_fa = models.CharField(_("song name in fa"), max_length=100, blank=True, null=True)
#     song_name_en = models.CharField(_("song name in en"), max_length=100, blank=True, null=True)
#     lyrics = models.TextField(_("lyrics"))
#     post_name_url = models.CharField(_("post name url"), max_length=300)
#     post_type = models.CharField(_("post type"), max_length=100)
#     artist_name_fa = models.CharField(_("artist name in fa"), max_length=100)
#     artist_name_en = models.CharField(_("artist name in en"), max_length=100)
#     link_mp3_demo = models.CharField(_("demo link"), max_length=500, blank=True, null=True)
#     link_mp3_128 = models.CharField(_("quality of 128 mp3 link"), max_length=500, blank=True, null=True)
#     link_mp3_320 = models.CharField(_("quality of 320 mp3 link"), max_length=500, blank=True, null=True)
#     thumbnail_photo = models.CharField(_("thumbnail photo"), max_length=500)
#     published_date = models.CharField(_("published date"), max_length=50)
#
#     def __str__(self):
#         return self.title
#


class CrawledMusic(models.Model):
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    published_date = models.CharField(_("published date"), max_length=20)

    title = models.CharField(_("title"), max_length=300)
    song_name_fa = models.CharField(_("song name in fa"), max_length=200)
    song_name_en = models.CharField(_("song name in en"), max_length=200)

    lyrics = models.TextField(_("lyrics"), blank=True, null=True)

    post_name_url = models.CharField(_("post name url"), max_length=300)
    post_type = models.CharField(_("post type"), max_length=100)

    artist_name_fa = models.CharField(_("artist name in fa"), max_length=200)
    artist_name_en = models.CharField(_("artist name in en"), max_length=200)
    thumbnail_photo = models.CharField(_("thumbnail photo"), max_length=500)

    link_mp3_128 = models.CharField(_("quality of 128 mp3 link"), max_length=500)
    link_mp3_320 = models.CharField(_("quality of 320 mp3 link"), max_length=500)

    is_downloaded = models.BooleanField(_('is downloaded'), default=False)
    file_mp3_128 = models.FileField(_('file mp3 128'), upload_to=UploadTo('mp3_128'), null=True)
    file_mp3_328 = models.FileField(_('file mp3 328'), upload_to=UploadTo('mp3_328'), null=True)

    # TODO Add field for thumbnail

    def __str__(self):
        return self.title

