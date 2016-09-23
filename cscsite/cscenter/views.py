# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import random

from collections import Counter

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db.models import Q, Count
from django.http import Http404
from django.utils.timezone import now
from django.views import generic

from core.models import Faq
from learning.models import Semester, CourseOffering, CourseOfferingTeacher, \
    OnlineCourse, StudyProgram
from learning.settings import SEMESTER_TYPES
from learning.utils import get_current_semester_pair, get_term_index, \
    get_term_index_academic
from users.models import CSCUser


class IndexView(generic.TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        pool = cache.get('index_page_spb_courses_with_video')
        if pool is None:
            year, term_type = get_current_semester_pair()
            current_term_index = get_term_index(year, term_type)
            term_index = get_term_index_academic(year, term_type,
                                                 rewind_years=2)
            pool = list(CourseOffering.custom.site_related(self.request)
                .filter(is_published_in_video=True,
                        is_open=False,
                        semester__index__gte=term_index,
                        semester__index__lte=current_term_index)
                .defer('description')
                .select_related('course')
                .prefetch_related('teachers', 'semester')
                .annotate(Count('courseclass')))
            cache.set('index_page_spb_courses_with_video', pool, 3600)
        random.shuffle(pool)
        context['courses'] = pool[:3]
        testimonials = cache.get('index_page_testimonials')
        if testimonials is None:
            s = (CSCUser.objects
                 .filter(groups=CSCUser.group_pks.GRADUATE_CENTER)
                 .exclude(csc_review='').exclude(photo='')
                 .order_by('?')
                 .first())
            if s and s.csc_review.strip():
                testimonials = [s]
            cache.set('index_page_testimonials', testimonials, 3600)
        context['testimonials'] = testimonials
        # Don't care about performance for online courses
        today = now().date()
        pool = list(OnlineCourse
                    .objects
                    .filter(Q(end__date__gt=today) |
                            Q(is_self_paced=True))
                    .order_by("start", "name"))
        random.shuffle(pool)
        context['online_courses'] = pool[:1]
        return context


class QAListView(generic.ListView):
    context_object_name = "faq"
    template_name = "faq.html"

    def get_queryset(self):
        return Faq.objects.filter(site=settings.CENTER_SITE_ID).order_by("sort")


class TestimonialsListView(generic.ListView):
    context_object_name = "testimonials"
    template_name = "testimonials.html"
    paginate_by = 10

    def get_queryset(self):
        return (CSCUser.objects
                .filter(groups=CSCUser.group_pks.GRADUATE_CENTER)
                .exclude(csc_review='').exclude(photo='')
                .prefetch_related("study_programs")
                .order_by("-graduation_year", "last_name"))


class TeachersView(generic.ListView):
    template_name = "center_teacher_list.html"
    context_object_name = "teachers"

    def get_queryset(self):
        user_model = get_user_model()
        qs = (user_model.objects
              .filter(groups=user_model.group_pks.TEACHER_CENTER,
                      courseofferingteacher__roles=CourseOfferingTeacher.roles.lecturer)
              .distinct())
        return qs

    def get_context_data(self, **kwargs):
        context = super(TeachersView, self).get_context_data(**kwargs)
        # Consider the last 3 academic years. Teacher is active, if he read
        # course in this period or will in the future.
        year, term_type = get_current_semester_pair()
        term_index = get_term_index_academic(year, term_type, rewind_years=3)
        active_lecturers = Counter(
            CourseOffering.objects.filter(semester__index__gte=term_index)
            .values_list("teachers__pk", flat=True)
        )
        context["active"] = filter(lambda t: t.pk in active_lecturers,
                                   context[self.context_object_name])
        context["other"] = filter(lambda t: t.pk not in active_lecturers,
                                  context[self.context_object_name])
        return context


# TODO: Rewrite filter by study programs with js and 1 additional db query?
class AlumniView(generic.ListView):
    filter_by_year = None
    study_programs = None
    template_name = "users/alumni_list.html"

    def get(self, request, *args, **kwargs):
        # Validate query params
        code = self.kwargs.get("study_program_code", False)
        self.study_programs = StudyProgram.objects.all()
        if code and code not in (s.code for s in self.study_programs):
            # TODO: redirect to alumni/ page
            raise Http404
        return super(AlumniView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        user_model = get_user_model()
        graduate_pk = user_model.group_pks.GRADUATE_CENTER
        params = {
            "groups__pk": graduate_pk
        }
        if self.filter_by_year is not None:
            params["graduation_year"] = self.filter_by_year
        code = self.kwargs.get("study_program_code", False)
        if code:
            params["study_programs"] = code
        return (user_model.objects
                .filter(**params)
                .order_by("-graduation_year", "last_name", "first_name"))

    def get_context_data(self, **kwargs):
        context = super(AlumniView, self).get_context_data(**kwargs)
        code = self.kwargs.get("study_program_code", False)
        context["selected_study_program"] = code
        context["study_programs"] = self.study_programs
        if self.filter_by_year:
            context["base_url"] = reverse(
                "alumni_{}".format(self.filter_by_year))
        else:
            context["base_url"] = reverse("alumni")
        return context


class AlumniByYearView(generic.ListView):
    filter_by_year = None
    context_object_name = "alumni_list"
    template_name = "users/alumni_by_year.html"

    def get_queryset(self):
        user_model = get_user_model()
        graduate_pk = user_model.group_pks.GRADUATE_CENTER
        params = {
            "groups__pk": graduate_pk,
        }
        assert self.filter_by_year is not None
        params["graduation_year"] = self.filter_by_year
        return (user_model.objects
                .filter(**params)
                .order_by("-graduation_year", "last_name", "first_name"))

    def get_context_data(self, **kwargs):
        context = super(AlumniByYearView, self).get_context_data(**kwargs)
        testimonials = cache.get('alumni_2016_testimonials')
        if testimonials is None:
            s = (CSCUser.objects
                 .filter(
                    groups=CSCUser.group_pks.GRADUATE_CENTER,
                    graduation_year=self.filter_by_year,
                 )
                 .exclude(csc_review='').exclude(photo='')
                 .prefetch_related("study_programs"))
            testimonials = s[:]
            cache.set('alumni_2016_testimonials', testimonials, 3600)
        context['testimonials'] = self.testimonials_random(testimonials)
        context["year"] = self.filter_by_year
        return context

    @staticmethod
    def testimonials_random(testimonials):
        indexes = random.sample(range(len(testimonials)),
                                min(len(testimonials), 5))
        for index in indexes:
            yield testimonials[index]
