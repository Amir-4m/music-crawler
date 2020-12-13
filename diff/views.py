from django.shortcuts import render

# Create your views here.
from diff.models import Prototype


def see_changes(request):
    news = Prototype.objects.get(id=id)
