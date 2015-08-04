# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.contrib.syndication.views import Feed
from django.db.models import Q
from django.views import generic
from django.utils import translation
from django.contrib.sites.models import Site

from .models import News


class NewsFeed(Feed):
    title = "Новости CSC"
    link = "/news/"
    description = ""

    def __init__(self):
        pass
    def items(self):
        site = Site.objects.get_current()
        if site.domain == 'compsciclub.ru':
            self.title = 'Новости Computer Science Клуба'
        else:
            self.title = 'Новости Computer Science Центра'
        return (News.public.filter(site__pk=settings.SITE_ID, language='ru')
                            .order_by('-created')[:10])

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.text


class NewsDetailView(generic.DetailView):
    model = News

    def get_queryset(self):
        q = (self.model.objects
                .filter(site__pk=settings.SITE_ID,
                        language=translation.get_language()))
        if hasattr(self.request, 'city'):
            q = q.filter(
                Q(city__pk=self.request.city.code) | Q(city__isnull=True))
        return q


class NewsListView(generic.ListView):
    model = News

    def get_queryset(self):
        q = (News.public.filter(site__pk=settings.SITE_ID,
                                language=translation.get_language())
                        .select_related('city'))
        if hasattr(self.request, 'city'):
            q = q.filter(
                Q(city__pk=self.request.city.code) | Q(city__isnull=True))
        return q


class NewsCreateView(generic.CreateView):
    model = News


class NewsUpdateView(generic.UpdateView):
    model = News
