from django.contrib import admin

from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin

from .models import CMusic, Album, Artist
from .views import start_new_crawl


@admin.register(CMusic)
class CMusicAdmin(admin.ModelAdmin):
    change_list_template = 'change_list.html'
    list_display = ("song_name_en", "title", "post_type", 'is_downloaded')
    readonly_fields = ['album']
    ordering = ['-id']

    def get_urls(self):
        from django.urls import path
        url_patterns = [
            path('start-crawl/<str:site_name>/', start_new_crawl, name='start-crawl')
        ]
        url_patterns += super().get_urls()
        return url_patterns


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ("album_name_en", 'site_id')


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin, DynamicArrayMixin):
    pass


admin.site.empty_value_display = "Unknown"
