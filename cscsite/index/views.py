from django.shortcuts import render
from django.views.generic import TemplateView

from news.models import News

class IndexView(TemplateView):
    template_name="index.html"

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context['news_objects'] = News.public.all()[:3]
        return context
