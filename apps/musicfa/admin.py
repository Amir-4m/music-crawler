from django.contrib import admin, messages
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin

from .models import CMusic, Album, Artist
from .tasks import create_single_music_post_task, create_album_post_task
from .views import start_new_crawl
from .utils import checking_task_status
from .forms import CMusicForm


class CMusicInline(admin.TabularInline):
    model = CMusic
    readonly_fields = ('song_name_en', 'get_download_link', 'is_downloaded')
    fields = ('song_name_en', 'get_download_link', 'is_downloaded')
    show_change_link = True
    extra = 0

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj):
        return False

    def get_download_link(self, obj):
        return mark_safe(f'<a href="{obj.link_mp3_320}">320 link</a>    <a href="{obj.link_mp3_128}">128 link</a>')
    get_download_link.short_description = _('download link')


@admin.register(CMusic)
class CMusicAdmin(admin.ModelAdmin):
    form = CMusicForm
    raw_id_fields = ['artist']
    change_form_template = 'changes.html'
    change_list_template = 'change_list.html'
    actions = ['send_to_word_press']
    list_display = ("name", 'artist', "title", "post_type", 'status', 'is_downloaded')
    list_filter = ['is_downloaded', 'post_type']
    search_fields = ['artist_id', 'song_name_fa', 'song_name_en', 'album_id']
    readonly_fields = [
        'album', 'get_thumbnail', 'site_id', 'is_downloaded', 'wp_post_id', 'published_date', 'album', 'post_type'
    ]
    ordering = ['-id']
    fieldsets = (
        ('Music', {'fields': ('title', 'song_name_fa', 'song_name_en', 'artist', 'lyrics', 'status', 'album')}),
        (
            'Extra Data', {
                'classes': ('collapse',), 'fields': (
                    'page_url', 'site_id', 'post_type', 'wp_category_id', 'wp_post_id', 'is_downloaded',
                    'published_date'
                )
            }
        ),
        ('Links', {'classes': ('collapse',), 'fields': ('link_mp3_128', 'link_mp3_320', 'link_thumbnail')}),
        ('Files', {'classes': ('collapse',), 'fields': (
            'file_mp3_128', 'file_mp3_320', 'file_thumbnail', 'get_thumbnail'
        )})
    )

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

    def change_view(self, request, object_id, **kwargs):
        if '_sned_to_wp' in request.POST:
            instance = self.get_object(request, object_id)
            if instance.post_type == CMusic.SINGLE_TYPE:
                create_single_music_post_task.apply_async(args=(object_id,))
                messages.info(request, _('creating new single music on wordpress'))
            else:
                create_album_post_task.apply_async(args=(instance.album_id,))
                messages.info(request, _('creating new album on wordpress'))
        return super().change_view(request, object_id, **kwargs)

    def get_thumbnail(self, obj):
        from django.utils.html import escape
        return mark_safe(
            f'<img src="{escape(obj.file_thumbnail.url if obj.file_thumbnail else obj.link_thumbnail)}" '
            f'height="20%" width="20%"/>'
        )
    get_thumbnail.short_description = _('current thumbnail')

    def send_to_word_press(self, request, queryset):
        # creating the album post from tracks of it
        create_album_post_task.apply_async(
            args=tuple(
                [
                    q.album_id
                    for q in queryset.filter(
                        post_type=CMusic.ALBUM_MUSIC_TYPE
                    ).order_by('album_id').distinct('album_id')
                ]
            )
        )
        # creating single music post
        create_single_music_post_task.apply_async(
            args=tuple(
                [q.id for q in queryset.filter(post_type=CMusic.SINGLE_TYPE)]
            )
        )
        messages.info(request, _('selected musics created at wordpress!'))


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    inlines = [CMusicInline]
    raw_id_fields = ['artist']
    list_display = ("name", 'artist', 'status')
    search_fields = ['album_name_en', 'album_name_fa', 'title']
    list_filter = ['is_downloaded']
    ordering = ['-id']
    readonly_fields = ['get_thumbnail', 'site_id', 'wp_post_id']
    actions = ['send_to_word_press']
    fieldsets = (
        ('Album', {'fields': ('title', 'album_name_en', 'album_name_fa', 'artist', 'status')}),
        (
            'Extra Data', {
                'classes': ('collapse',), 'fields': ('page_url', 'site_id', 'wp_category_id', 'wp_post_id')
            }
        ),
        ('Links', {'classes': ('collapse',), 'fields': (
            'link_mp3_128', 'link_mp3_320', 'link_thumbnail', 'file_thumbnail', 'get_thumbnail'
        )}),
    )

    def get_thumbnail(self, obj):
        from django.utils.html import escape
        return mark_safe(f'<img src="{escape(obj.file_thumbnail.url if obj.file_thumbnail else obj.link_thumbnail)}"'
                         f' height="20%" width="20%"/>')
    get_thumbnail.short_description = _('current thumbnail')

    def send_to_word_press(self, request, queryset):
        create_album_post_task.apply_async(args=([q.id for q in queryset]))
        messages.info(request, _('selected albums created at wordpress!'))


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin, DynamicArrayMixin):
    list_display = ['name', 'name_en', 'name_fa']
    search_fields = ['name_en', 'name_fa']
    ordering = ['-id']


admin.site.empty_value_display = "Unknown"
