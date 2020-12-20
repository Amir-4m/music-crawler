from django.contrib import admin

from .models import CMusic, Album


@admin.register(CMusic)
class CMusicAdmin(admin.ModelAdmin):
    list_display = ("song_name_en", "title", "post_type", 'is_downloaded')
    readonly_fields = ['album']
    ordering = ['-id']


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ("album_name_en", "artist_name_en", 'site_id')


admin.site.empty_value_display = "Unknown"
