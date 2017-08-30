# -*- coding: utf-8 -*-

import itertools
import random

from collections import Counter, OrderedDict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http.response import HttpResponseRedirect, HttpResponseNotFound
from django.urls import reverse
from django.db.models import Q, Count, Prefetch, Case, When, Value
from django.http import Http404
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.views import generic
from django_filters.views import FilterView
from rest_framework.renderers import JSONRenderer

from core.exceptions import Redirect
from core.models import Faq
from cscenter.serializers import CourseOfferingSerializer
from learning.models import CourseOffering, CourseOfferingTeacher, \
    OnlineCourse, AreaOfStudy, StudyProgram, Semester
from learning.settings import CENTER_FOUNDATION_YEAR, TERMS_IN_ACADEMIC_YEAR
from learning.utils import get_current_term_pair, get_term_index, \
    get_term_index_academic_year_starts, get_term_by_index
from stats.views import StudentsDiplomasStats
from users.models import CSCUser
from .filters import CourseFilter


class IndexView(generic.TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        pool = cache.get('index_page_spb_courses_with_video')
        if pool is None:
            # Note: Show courses based on SPB timezone
            year, term_type = get_current_term_pair(settings.DEFAULT_CITY_CODE)
            current_term_index = get_term_index(year, term_type)
            term_index = get_term_index_academic_year_starts(year, term_type)
            # Subtract 1 academic year
            term_index -= TERMS_IN_ACADEMIC_YEAR
            pool = list(CourseOffering.objects
                        .in_city(self.request.city_code)
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
                 .filter(groups=CSCUser.group.GRADUATE_CENTER)
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
        context['is_admission_active'] = False
        return context


class TeamView(generic.TemplateView):
    template_name = "orgs.html"

    # TODO: Add cache for users query?
    def get_context_data(self, **kwargs):
        context = super(TeamView, self).get_context_data(**kwargs)
        board = {
            863: "andrey_ivanov",
            5: "alexander_kulikov",
            607: "evgeniya_kulikova",
        }
        curators = {
            38: "katya_lebedeva",
            617: "kristina_smolnikova",
            1213: "katya_artamonova",
            2605: "mojina_alina",
            3173: "komissarov_alexander",
        }
        tech = {
            1780: "aleksey_belozerov",
            865: "sergey_zherevchuk"
        }
        context["board"] = {}
        context["curators"] = {}
        context["tech"] = {}
        users_pk = list(board)
        users_pk.extend(curators.keys())
        users_pk.extend(tech.keys())
        for u in CSCUser.objects.filter(pk__in=users_pk).all():
            if u.pk in board:
                context["board"][board[u.pk]] = u
            elif u.pk in tech:
                context["tech"][tech[u.pk]] = u
            else:
                context["curators"][curators[u.pk]] = u
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
                .filter(groups=CSCUser.group.GRADUATE_CENTER)
                .exclude(csc_review='').exclude(photo='')
                .prefetch_related("areas_of_study")
                .order_by("-graduation_year", "last_name"))


class TeachersView(generic.ListView):
    template_name = "center_teacher_list.html"
    context_object_name = "teachers"

    def get_queryset(self):
        user_model = get_user_model()
        qs = (user_model.objects
              .filter(groups=user_model.group.TEACHER_CENTER,
                      courseofferingteacher__roles=CourseOfferingTeacher.roles.lecturer)
              .distinct())
        return qs

    def get_context_data(self, **kwargs):
        context = super(TeachersView, self).get_context_data(**kwargs)
        # Consider the last 3 academic years. Teacher is active, if he read
        # course in this period or will in the future.
        year, term_type = get_current_term_pair(settings.DEFAULT_CITY_CODE)
        term_index = get_term_index_academic_year_starts(year, term_type)
        term_index -= 2 * TERMS_IN_ACADEMIC_YEAR
        active_lecturers = Counter(
            CourseOffering.objects.filter(semester__index__gte=term_index)
            .values_list("teachers__pk", flat=True)
        )
        context["active"] = filter(lambda t: t.pk in active_lecturers,
                                   context[self.context_object_name])
        context["other"] = filter(lambda t: t.pk not in active_lecturers,
                                  context[self.context_object_name])
        return context


class AlumniView(generic.ListView):
    filter_by_year = None
    template_name = "users/alumni_list.html"

    def get(self, request, *args, **kwargs):
        # Validate query params
        code = self.kwargs.get("area_of_study_code", False)
        # Support old code "dm" for `Data Mining`
        if code == "dm":
            redirect_to = reverse("alumni_by_area_of_study", kwargs={
                "area_of_study_code": "ds"})
            return HttpResponseRedirect(redirect_to)
        self.areas_of_study = AreaOfStudy.objects.all()
        if code and code not in (s.code for s in self.areas_of_study):
            # TODO: redirect to alumni/ page
            raise Http404
        return super(AlumniView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        user_model = get_user_model()
        graduate_pk = user_model.group.GRADUATE_CENTER
        params = {
            "groups__pk": graduate_pk
        }
        if self.filter_by_year is not None:
            params["graduation_year"] = self.filter_by_year
        code = self.kwargs.get("area_of_study_code", False)
        if code:
            params["areas_of_study"] = code
        return (user_model.objects
                .filter(**params)
                .order_by("-graduation_year", "last_name", "first_name"))

    def get_context_data(self, **kwargs):
        context = super(AlumniView, self).get_context_data(**kwargs)
        code = self.kwargs.get("area_of_study_code", False)
        context["selected_area_of_study"] = code
        context["areas_of_study"] = self.areas_of_study
        if self.filter_by_year:
            context["base_url"] = reverse(
                "alumni_{}".format(self.filter_by_year))
        else:
            context["base_url"] = reverse("alumni")
        return context


class AlumniByYearView(generic.ListView):
    context_object_name = "alumni_list"
    template_name = "users/alumni_by_year.html"

    def get(self, request, *args, **kwargs):
        year = int(self.kwargs['year'])
        now__year = now().year
        # No graduates in first 2 years after foundation
        if year < CENTER_FOUNDATION_YEAR + 2 or year > now__year:
            return HttpResponseNotFound()
        return super(AlumniByYearView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        user_model = get_user_model()
        year = int(self.kwargs['year'])
        filters = (Q(groups__pk=user_model.group.GRADUATE_CENTER) &
                   Q(graduation_year=year))
        if year == now().year and self.request.user.is_curator:
            filters = filters | Q(status=CSCUser.STATUS.will_graduate)
        return (user_model.objects
                .filter(filters)
                .distinct()
                .order_by("-graduation_year", "last_name", "first_name"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = int(self.kwargs['year'])
        context["year"] = year
        testimonials = cache.get('alumni_{}_testimonials'.format(year))
        if testimonials is None:
            s = (CSCUser.objects
                 .filter(
                    groups=CSCUser.group.GRADUATE_CENTER,
                    graduation_year=year,
                 )
                 .exclude(csc_review='').exclude(photo='')
                 .prefetch_related("areas_of_study"))
            testimonials = s[:]
            cache.set('alumni_{}_testimonials'.format(year),
                      testimonials, 3600)
        context['testimonials'] = self.testimonials_random(testimonials)

        is_curator = self.request.user.is_curator
        stats = cache.get('alumni_{}_stats_{}'.format(year, is_curator))
        if stats is None:
            stats = StudentsDiplomasStats.as_view()(self.request, year,
                                                    **kwargs).data
            cache.set('alumni_{}_stats_{}'.format(year, is_curator), stats,
                      24 * 3600)
        context["stats"] = stats
        return context

    @staticmethod
    def testimonials_random(testimonials):
        indexes = random.sample(range(len(testimonials)),
                                min(len(testimonials), 5))
        return [testimonials[index] for index in indexes]


class SyllabusView(generic.TemplateView):
    template_name = "syllabus.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        syllabus = (StudyProgram.objects
                    .syllabus()
                    .filter(year=2017)
                    .order_by("city_id", "area__name_ru"))
        context["programs"] = self.group_programs_by_city(syllabus)
        # TODO: validate entry city
        context["selected_city"] = self.request.GET.get('city', 'spb')
        return context

    def group_programs_by_city(self, syllabus):
        grouped = {}
        for city_id, g in itertools.groupby(syllabus,
                                            key=lambda sp: sp.city_id):
            grouped[city_id] = list(g)
        return grouped


class OpenNskView(generic.TemplateView):
    template_name = "open_nsk.html"


class TestCoursesListView(FilterView):
    model = CourseOffering
    context_object_name = "courses"
    filterset_class = CourseFilter
    template_name = "learning/courses/offerings_test.html"

    def get_queryset(self):
        return CourseOffering.objects.get_offerings_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # TODO: remove `dictkey` templatetag?
        context["TERM_TYPES"] = {
            Semester.TYPES.autumn: pgettext_lazy("adjective", "autumn"),
            Semester.TYPES.spring: pgettext_lazy("adjective", "spring"),
        }
        # FIXME: Нужно решить, что делать, если список курсов пустой. Пока не знаю, завтра с утра подумать надо бы.
        # if not self.filterset.form.is_valid():
        #     raise Redirect(to=reverse("course_list"))
        context["cities"] = self.filterset.form.fields['city'].choices
        # FIXME: replace courses with serializer?
        context["terms"] = self.get_terms_by_academic_year(context["courses"])
        serializer = CourseOfferingSerializer(context["courses"])
        context["by_slug"] = serializer.data
        # FIXME: replace with json.dumps
        context["json"] = JSONRenderer().render(serializer.data)
        context["active_city"] = self.filterset.data['city']
        # FIXME: What if form is invalid?
        year, term_type = self.filterset.get_term()
        context["active_year"] = year
        context["active_type"] = term_type
        context["active_slug"] = "{}-{}".format(year, term_type)
        return context

    @staticmethod
    def get_terms_by_academic_year(courses):
        """
        Group terms by academic year for provided list of courses

        Courses have to be sorted  by (-year, -semester__index) to make it work
        """
        terms = OrderedDict()
        prev_visited = object()
        for course in courses:
            term = course.semester
            if term != prev_visited:
                idx = get_term_index_academic_year_starts(term.year, term.type)
                academic_year, _ = get_term_by_index(idx)
                terms.setdefault(academic_year, []).append(term.type)
                prev_visited = term
        return terms
