from django.contrib.admin import SimpleListFilter
from django.utils.translation import ugettext_lazy as _

from admin_auto_filters.filters import AutocompleteFilter


class ArtistFilter(AutocompleteFilter):
    title = 'Artist'
    field_name = 'artist'


class AlbumFilter(AutocompleteFilter):
    title = 'Album'
    field_name = 'album'


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


class WebsiteCrawledFilter(SimpleListFilter):
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
