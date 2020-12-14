from django.shortcuts import render

from .models import CrawledMusic


# Create your views here.

def export_musicfa_songs(request):
    musics = CrawledMusic.objects.all()
    response = render(request,
                      'export_songs.html',
                      {'musics': musics, },
                      content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="musicfa_songs.csv"'
    return response


def export_nicmusic_songs(request):
    musics = CrawledMusic.objects.all()
    response = render(request,
                      'export_nimusic.html',
                      {'musics': musics, },
                      content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="nicmusic_songs.csv"'
    return response
