from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.db.models import Count
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin
from import_export.admin import ExportActionMixin

from .models import CMusic, Album, Artist
from .export_admin import AlbumResource, CMusicResource, ArtistResource
from .tasks import create_single_music_post_task, create_album_post_task, create_artist_wordpress_task
from .views import start_new_crawl
from .utils import checking_task_status, PersianNameHandler
from .forms import CMusicForm
from .admin_filters import AlbumFilter, ArtistFilter


class NullFilterSpec(SimpleListFilter):
    title = u''
    parameter_name = u''
    parameter_value = ''

    def lookups(self, request, model_admin):
        return (
            ('1', _('Has value'), ),
            ('0', _('empty'), ),
        )

    def queryset(self, request, queryset):
        kwargs = {'%s' % self.parameter_name: self.parameter_value}
        if self.value() == '0':
            return queryset.filter(**kwargs)
        if self.value() == '1':
            return queryset.exclude(**kwargs)
        return queryset


class SongNameFaNullFilterSpec(NullFilterSpec):
    title = u'song persian name'
    parameter_name = u'song_name_fa'


class AlbumNameFaNullFilterSpec(NullFilterSpec):
    title = u'album persian name'
    parameter_name = u'album_name_fa'


class ArtistNameFaNullFilterSpec(NullFilterSpec):
    title = u'artist persian name'
    parameter_name = u'name_fa'


class WPIDNullFilterSpec(NullFilterSpec):
    title = u'wordpress id'
    parameter_name = u'wp_post_id'
    parameter_value = None


class WPIDArtistNullFilterSpec(NullFilterSpec):
    title = u'wordpress id'
    parameter_name = u'wp_id'


class WPIDArtistNullFilterSpec(NullFilterSpec):
    title = u'wordpress id'
    parameter_name = u'wp_id'


class MusicAlbumWPIDArtistNullFilterSpec(NullFilterSpec):
    title = u'wordpress id of artist'
    parameter_name = u'artist__wp_id'


class BIOArtistNullFilterSpec(NullFilterSpec):
    title = u'Artist Bio'
    parameter_name = u'description'


class ImageArtistNullFilterSpec(NullFilterSpec):
    title = u'Artist Image'
    parameter_name = u'file_thumbnail'
    parameter_value = None


class WebsiteCrawledFilter(admin.SimpleListFilter):
    title = _('website')
    parameter_name = 'website'

    def lookups(self, request, model_admin):
        return (1, _('nic music')), (0, _('ganja2'))

    def queryset(self, request, queryset):
        if self.value() == "0":
            return queryset.filter(page_url__contains='ganja2music')
        if self.value() == "1":
            return queryset.filter(page_url__contains='nicmusic')

        return queryset


class AutoFilter:
    """
    `admin.ModelAdmin` classes that has a filter field by `admin_auto_filters.filters.AutocompleteFilter`
     should extends from this class.
    """
    class Media:
        pass


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


class ModelAdminDisplayTaskStatus(admin.ModelAdmin, AutoFilter):

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        if request.method == 'GET':
            response.context_data['crawl_status_nic'] = checking_task_status('collect_musics_nic')
            response.context_data['crawl_status_ganja'] = checking_task_status('collect_musics_ganja')
        return response

    def get_urls(self):
        from django.urls import path
        url_patterns = [
            path('start-crawl/<str:site_name>/', start_new_crawl, name='start-crawl')
        ]
        url_patterns += super().get_urls()
        return url_patterns


@admin.register(CMusic)
class CMusicAdmin(ExportActionMixin, ModelAdminDisplayTaskStatus):
    form = CMusicForm
    resource_class = CMusicResource
    change_form_template = 'changes.html'
    change_list_template = 'change_list.html'
    raw_id_fields = ['artist']
    actions = (*ExportActionMixin.actions, 'send_to_WordPress', 'translate')
    list_display = (
        "name", 'artist', "title", "post_type", 'status', 'is_downloaded', 'album', 'created_time', 'website_name'
    )
    list_filter = [
        ArtistFilter, AlbumFilter, WebsiteCrawledFilter, WPIDNullFilterSpec, MusicAlbumWPIDArtistNullFilterSpec,
        'created_time', 'published_date', 'is_downloaded',
        'post_type', 'status', SongNameFaNullFilterSpec
    ]
    search_fields = ['song_name_fa', 'song_name_en']
    readonly_fields = [
        'album', 'get_thumbnail', 'site_id', 'is_downloaded', 'wp_post_id', 'published_date', 'album', 'post_type'
    ]
    ordering = ['-id']
    fieldsets = (
        ('Music', {'fields': ('title', 'title_tag', 'song_name_fa', 'song_name_en', 'artist', 'lyrics', 'status', 'album')}),
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

    def change_view(self, request, object_id, **kwargs):
        if '_send_to_wp' in request.POST:
            instance = self.get_object(request, object_id)
            if instance.post_type == CMusic.SINGLE_TYPE and instance.artist.wp_id != '':
                create_single_music_post_task.apply_async(args=(object_id,))
                messages.info(request, _('creating new single music on wordpress'))
            else:
                messages.error(request, _(
                    'Please check the artist of music or send the album of this music' + f'{instance.album}'))
        return super().change_view(request, object_id, **kwargs)

    def get_thumbnail(self, obj):
        from django.utils.html import escape
        return mark_safe(
            f'<img src="{escape(obj.file_thumbnail.url if obj.file_thumbnail else obj.link_thumbnail)}" '
            f'height="20%" width="20%"/>'
        )
    get_thumbnail.short_description = _('current thumbnail')

    def send_to_WordPress(self, request, queryset):
        not_approved_artists = queryset.filter(artist__wp_id='')
        for q in not_approved_artists:
            messages.error(request, _(f'please approve artist of this music {q}'))

        queryset = queryset.exclude(artist__wp_id='')
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

    def translate(self, request, queryset):
        messages.info(request, _('wait...'))
        number = PersianNameHandler.update_single_musics(queryset.filter(page_url__contains='ganja2music'))
        messages.info(request, _(f'{number} Music updated. Translate is complete!'))


@admin.register(Album)
class AlbumAdmin(ExportActionMixin, ModelAdminDisplayTaskStatus):
    resource_class = AlbumResource
    change_form_template = 'changes.html'
    change_list_template = 'change_list.html'
    inlines = [CMusicInline]
    raw_id_fields = ['artist']
    list_display = ("name", 'artist', 'status', 'created_time', 'get_track_number', 'website_name')
    search_fields = ['album_name_en', 'album_name_fa', 'title']
    list_filter = [
        ArtistFilter, WebsiteCrawledFilter, 'created_time', 'published_date', 'is_downloaded', 'status',
        AlbumNameFaNullFilterSpec, WPIDNullFilterSpec, MusicAlbumWPIDArtistNullFilterSpec
    ]
    ordering = ['-id']
    readonly_fields = ['get_thumbnail', 'site_id', 'wp_post_id']
    actions = (*ExportActionMixin.actions, 'send_to_WordPress', 'translate')
    fieldsets = (
        ('Album', {'fields': ('title', 'title_tag', 'album_name_en', 'album_name_fa', 'artist', 'status')}),
        (
            'Extra Data', {
                'classes': ('collapse',), 'fields': ('page_url', 'site_id', 'wp_category_id', 'wp_post_id')
            }
        ),
        ('Links', {'classes': ('collapse',), 'fields': (
            'link_mp3_128', 'link_mp3_320', 'link_thumbnail', 'file_thumbnail', 'get_thumbnail'
        )}),
    )

    def change_view(self, request, object_id, **kwargs):
        if '_send_to_wp' in request.POST:
            album = Album.objects.get(id=object_id)
            if album.artist.wp_id != '':
                create_album_post_task.apply_async(args=(object_id,))
                messages.info(request, _('creating new album on wordpress'))
            else:
                messages.error(request, _(f'This artist is not approved! {album.artist}'))

        return super().change_view(request, object_id, **kwargs)

    # custom fields
    def get_thumbnail(self, obj):
        from django.utils.html import escape
        return mark_safe(f'<img src="{escape(obj.file_thumbnail.url if obj.file_thumbnail else obj.link_thumbnail)}"'
                         f' height="20%" width="20%"/>')
    get_thumbnail.short_description = _('current thumbnail')

    def get_track_number(self, obj):
        return CMusic.objects.filter(album=obj).count()
    get_track_number.short_description = _('current thumbnail')

    # actions
    def send_to_WordPress(self, request, queryset):
        not_approved_artists = queryset.filter(artist__wp_id='')
        for q in not_approved_artists:
            messages.error(request, _(f'please approve artist of this album {q}'))

        create_album_post_task.apply_async(args=([q.id for q in queryset]))
        messages.info(request, _('selected albums created at wordpress!'))

    def translate(self, request, queryset):
        messages.info(request, _('wait...'))
        number = PersianNameHandler.update_albums(queryset)
        messages.info(request, _(f'{number} Album updated. Translate is complete!'))


@admin.register(Artist)
class ArtistAdmin(ExportActionMixin, admin.ModelAdmin, DynamicArrayMixin):
    resource_class = ArtistResource
    change_form_template = 'changes.html'
    list_display = [
        'name', 'name_en', 'name_fa', 'note', 'wp_id', 'created_time', 'updated_time', 'albums', 'single_musics'
    ]
    search_fields = ['name_en', 'name_fa', 'note', 'wp_id']
    list_filter = [
        ArtistNameFaNullFilterSpec, WPIDArtistNullFilterSpec, BIOArtistNullFilterSpec, ImageArtistNullFilterSpec
    ]
    readonly_fields = ('id', 'updated_time', 'created_time')
    ordering = ['-id']
    actions = [*ExportActionMixin.actions, 'send_to_WordPress', 'translate']

    def change_view(self, request, object_id, **kwargs):
        if '_send_to_wp' in request.POST:
            obj = Artist.objects.get(id=object_id)

            if obj.file_thumbnail and obj.is_approved and obj.wp_id == '':
                create_artist_wordpress_task.apply_async(args=(object_id,))
                messages.info(request, _('creating new artist on wordpress'))
            else:
                messages.error(request, _('file is required or artist already exist in wordpress!'))

        return super().change_view(request, object_id, **kwargs)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _albums=Count('album', distinct=True),
            _single_music=Count('cmusic', distinct=True)
        )
        return queryset

    # actions
    def send_to_WordPress(self, request, queryset):
        create_artist_wordpress_task.apply_async(
            args=(list(queryset.filter(wp_id='', is_approved=True).values_list('id', flat=True)))
        )
        messages.info(request, _('selected artist created at wordpress!'))

    def translate(self, request, queryset):
        messages.info(request, _('wait...'))
        number = PersianNameHandler.update_artists(queryset)
        messages.info(request, _(f'{number} Artist updated. Translate is complete!'))

    def single_musics(self, obj):
        return obj._single_music
    single_musics.short_description = _('single musics number')
    single_musics.admin_order_field = '_single_music'

    def albums(self, obj):
        return obj._albums
    albums.short_description = _('albums number')
    albums.admin_order_field = '_albums'


admin.site.empty_value_display = "Empty"
