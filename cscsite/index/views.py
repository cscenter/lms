from django.shortcuts import render
from django.views.generic import TemplateView, ListView
from django.contrib.auth import get_user_model
from django.db.models import F

from news.models import News

class IndexView(TemplateView):
    template_name="index.html"

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context['news_objects'] = News.public.all()[:3]
        return context

# TODO: test it
class AlumniView(ListView):
    model = get_user_model()
    template_name = "alumni.html"

    def get_queryset(self):
        queryset = super(AlumniView, self).get_queryset()
        graduate_pk = self.model.IS_GRADUATE_PK
        return queryset.filter(groups__pk=graduate_pk)

# TODO: this view should make a distinction between professors that have active
#       courses and that who don't
# TODO: test it
class ProfView(ListView):
    model = get_user_model()
    template_name = "alumni.html"

    def get_queryset(self):
        queryset = super(ProfView, self).get_queryset()
        teacher_pk = self.model.IS_TEACHER_PK
        return queryset.filter(groups__pk=teacher_pk)
