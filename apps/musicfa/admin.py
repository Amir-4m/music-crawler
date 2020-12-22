from django.contrib import admin

from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin

from .models import CMusic, Album, Artist
from .views import start_new_crawl
from .utils import checking_task_status
from .forms import CMusicForm


@admin.register(CMusic)
class CMusicAdmin(admin.ModelAdmin):
    form = CMusicForm
    change_list_template = 'change_list.html'
    list_display = ("song_name_en", 'artist', "title", "post_type", 'is_downloaded')
    list_filter = ['is_downloaded']
    readonly_fields = ['album']
    ordering = ['-id']

    def get_urls(self):
        from django.urls import path
        url_patterns = [
            path('start-crawl/<str:site_name>/', start_new_crawl, name='start-crawl')
        ]
        url_patterns += super().get_urls()
        return url_patterns

    def changelist_view(self, request, extra_context=None):
        response = super(CMusicAdmin, self).changelist_view(request, extra_context)
        if request.method == 'GET':
            response.context_data['crawl_status_nic'] = checking_task_status('collect_musics_nic')
            response.context_data['crawl_status_ganja'] = checking_task_status('collect_musics_ganja')
        return response


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ("album_name_en", 'artist')
    ordering = ['-id']


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin, DynamicArrayMixin):
    list_display = ['name_en', 'name_fa']
    search_fields = ['name_en', 'name_fa']
    ordering = ['-id']


admin.site.empty_value_display = "Unknown"
