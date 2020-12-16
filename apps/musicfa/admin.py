from django.contrib import admin

# Register your models here.
from .models import CMusic


@admin.register(CMusic)
class CMusicAdmin(admin.ModelAdmin):
    list_display = ("title", "song_name_en", "artist_name_en", "post_type")
    ordering = ['-id']


admin.site.empty_value_display = "Unknown"
