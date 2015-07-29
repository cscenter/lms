from django.conf import settings
from django.views import generic
from django.utils import translation

from news.models import News


class NewsDetailView(generic.DetailView):
    model = News


class NewsListView(generic.ListView):
    model = News

    def get_queryset(self):
        return News.public.filter(sites__id=settings.SITE_ID,
                                  language=translation.get_language())


class NewsCreateView(generic.CreateView):
    model = News


class NewsUpdateView(generic.UpdateView):
    model = News
