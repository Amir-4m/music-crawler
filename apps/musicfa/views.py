from importlib import import_module

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy

from .models import CMusic
from .tasks import collect_files_nic

@login_required
def export_musicfa_songs(request):
    musics = CMusic.objects.all()
    response = render(request,
                      'export_songs.html',
                      {'musics': musics},
                      content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="musicfa_songs.csv"'
    return response


@login_required
def export_nicmusic_songs(request):
    musics = CMusic.objects.all()
    response = render(request,
                      'export_nimusic.html',
                      {'musics': musics},
                      content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="nicmusic_songs.csv"'
    return response


@login_required
def start_new_crawl(request, site_name):
    """
    :param request: Django request object
    :param site_name: name of the function that start crawling. etc collect_musics_ganja
    :return:
    """
    module = import_module('apps.musicfa.tasks')
    getattr(module, site_name).delay()  # Starting Crawl
    messages.info(request, 'Starting crawl...')
    return HttpResponseRedirect(reverse_lazy('admin:index'))
