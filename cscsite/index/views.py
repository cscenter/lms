from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import F
from django.shortcuts import render
from django.views.generic import TemplateView, ListView

from news.models import News


class IndexView(TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context['news_objects'] = News.public.all()[:3]
        return context


# TODO: test it
class AlumniView(ListView):
    template_name = "alumni_list.html"

    def get_queryset(self):
        user_model = get_user_model()
        graduate_pk = user_model.IS_GRADUATE_PK
        return (user_model.objects
                .filter(groups__pk=graduate_pk)
                .order_by("-graduation_year", "last_name", "first_name"))


# TODO: this view should make a distinction between professors that have active
#       courses and that who don't
# TODO: test it
class ProfView(ListView):
    template_name = "teacher_list.html"

    def get_queryset(self):
        user_model = get_user_model()
        teacher_pk = user_model.IS_TEACHER_PK
        return user_model.objects.filter(groups__pk=teacher_pk)
