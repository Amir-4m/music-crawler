from admin_auto_filters.filters import AutocompleteFilter


class ArtistFilter(AutocompleteFilter):
    title = 'Artist'
    field_name = 'artist'


class AlbumFilter(AutocompleteFilter):
    title = 'Album'
    field_name = 'album'

