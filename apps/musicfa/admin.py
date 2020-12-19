from django.contrib import admin

from .models import CMusic, Album, Artist


@admin.register(CMusic)
class CMusicAdmin(admin.ModelAdmin):
    list_display = ("title", "song_name_en", "post_type")
    ordering = ['-id']


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    pass

@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    pass



admin.site.empty_value_display = "Unknown"
