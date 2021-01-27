from django.test import TestCase

# Create your tests here.

# from apps.musicfa.models import Artist, CMusic, Album
# from django.db.models.functions import Lower
# from django.db.models import Count
#
#
# def clean_duplicate_artists():
#     duplicate_artists = Artist.objects.values(
#         name_lower=Lower('name_en')
#     ).annotate(Count('name_en')).filter(name_en__count__gt=1)
#
#     for dup_artist in duplicate_artists:
#         artists = Artist.objects.filter(name_en__iexact=dup_artist['name_lower'])
#         print("artists >> ", artists)
#
#         artists_id = artists.values_list('id', flat=True)
#         best_artist = max(artists_id)
#         print("selected artist >> ", best_artist)
#
#         albums = Album.objects.filter(artist_id__in=artists_id)
#         albums.update(artist_id=best_artist)
#         print(albums)
#
#         musics = CMusic.objects.filter(artist_id__in=artists_id)
#         musics.update(artist_id=best_artist)
#         print(musics, '\n\n')
#         artists.exclude(id=best_artist).delete()
