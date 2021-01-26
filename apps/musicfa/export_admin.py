from import_export import resources

from .models import CMusic, Album, Artist


class CMusicResource(resources.ModelResource):
    class Meta:
        model = CMusic
        fields = (
            'id', 'song_name_en', 'song_name_fa', 'artist__name_en', 'artist__name_fa', 'artist_id', 'album',
            'website_name', 'title'
        )


class AlbumResource(resources.ModelResource):
    class Meta:
        model = Album
        fields = (
            'id', 'album_name_en', 'album_name_fa', 'artist__name_en', 'artist__name_fa', 'artist_id', 'album',
            'website_name', 'title'
        )


class ArtistResource(resources.ModelResource):
    class Meta:
        model = Artist
        fields = (
            'id', 'name_fa', 'name_en'
        )

