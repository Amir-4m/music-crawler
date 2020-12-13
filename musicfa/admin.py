from django.contrib import admin

# Register your models here.
from musicfa.models import NicMusic


@admin.register(NicMusic)
class NicMusicAdmin(admin.ModelAdmin):
    list_display = ("title", "song_name_fa", "artist_name_fa", "song_name_en", "artist_name_en", "post_type")
    list_filter = ("artist_name_fa",)


admin.site.empty_value_display = "Unknown"
