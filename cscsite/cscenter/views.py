# -*- coding: utf-8 -*-

import itertools
import json
import random

from collections import Counter, OrderedDict
from datetime import datetime
from django.contrib.staticfiles.storage import staticfiles_storage
from typing import NamedTuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache, caches, InvalidCacheBackendError
from django.http.response import HttpResponseRedirect, HttpResponseNotFound
from django.urls import reverse
from django.db.models import Q, Count, Prefetch, Case, When, Value
from django.http import Http404
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.views import generic
from django_filters.views import FilterView, FilterMixin
from rest_framework.renderers import JSONRenderer
from vanilla import TemplateView, ListView

from core.api.utils import SocialPost
from core.exceptions import Redirect
from core.models import Faq
from cscenter.serializers import CourseOfferingSerializer
from cscenter.utils import group_terms_by_academic_year, PublicRoute, \
    PublicRouteException
from learning.api.views import TestimonialList
from learning.models import CourseOffering, CourseOfferingTeacher, \
    OnlineCourse, AreaOfStudy, StudyProgram, Semester
from learning.settings import CENTER_FOUNDATION_YEAR, TERMS_IN_ACADEMIC_YEAR
from learning.utils import get_current_term_pair, get_term_index, \
    get_term_index_academic_year_starts, get_term_by_index
from stats.views import StudentsDiplomasStats
from users.models import CSCUser
from .filters import CoursesFilter


class OnlineCourseTuple(NamedTuple):
    name: str
    link: str
    avatar_url: str
    tag: str


class IndexView(TemplateView):
    template_name = 'cscenter/index.html'
    TESTIMONIALS_CACHE_KEY = 'v2_index_page_testimonials'
    VK_CACHE_KEY = 'v2_index_vk_social_news'
    INSTAGRAM_CACHE_KEY = 'v2_index_instagram_posts'

    def get(self, request, *args, **kwargs):
        if request.user.index_redirect:
            try:
                section_code = request.user.index_redirect
                url = PublicRoute.url_by_code(section_code)
                return HttpResponseRedirect(redirect_to=url)
            except PublicRouteException:
                pass
        context = self.get_context_data()
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        # Online programs + online courses
        courses = [
            OnlineCourseTuple('Алгоритмы и эффективные вычисления',
                              'https://code.stepik.org/algo/',
                              staticfiles_storage.url('v2/img/pages/index/online_programs/algo.png'),
                              'Онлайн-программа'),
            OnlineCourseTuple('Математика для разработчика',
                              'https://code.stepik.org/math/',
                              staticfiles_storage.url('v2/img/pages/index/online_programs/math.png'),
                              'Онлайн-программа'),
            OnlineCourseTuple('Разработка на C++, Java и Haskell',
                              'https://code.stepik.org/dev/',
                              staticfiles_storage.url('v2/img/pages/index/online_programs/dev.png'),
                              'Онлайн-программа')
        ]
        today = now().date()
        pool = list(OnlineCourse.objects
                    .filter(Q(end__date__gt=today) | Q(is_self_paced=True))
                    .only('name', 'link', 'photo')
                    .order_by("start", "name"))
        random.shuffle(pool)
        for course in pool[:3]:
            courses.append(OnlineCourseTuple(name=course.name,
                                             link=course.link,
                                             avatar_url=course.avatar_url,
                                             tag='Онлайн-курс'))
        # Testimonials
        testimonials = cache.get(self.TESTIMONIALS_CACHE_KEY)
        if testimonials is None:
            # TODO: Выбрать только нужные поля
            s = (CSCUser.objects
                 .filter(groups=CSCUser.group.GRADUATE_CENTER)
                 .exclude(csc_review='').exclude(photo='')
                 .prefetch_related("areas_of_study")
                 .order_by('?'))[:4]
            testimonials = s
            cache.set(self.TESTIMONIALS_CACHE_KEY, testimonials, 3600)
        _cache = caches['social_networks']
        context = {
            'testimonials': testimonials,
            'courses': courses,
            'vk_news': _cache.get(self.VK_CACHE_KEY),
            'instagram_posts': _cache.get(self.INSTAGRAM_CACHE_KEY),
            'is_admission_active': False
        }
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


class TestimonialsListV2View(TemplateView):
    template_name = "cscenter/testimonials.html"

    def get_context_data(self, **kwargs):
        try:
            current_page = int(self.request.GET.get("page"))
            current_page = max(current_page, 1)
        except (ValueError, TypeError):
            # TODO: redirect instead?
            current_page = 1
        return {
            "app_data": {
                "state": {
                    "page": current_page,
                },
                "props": {
                    "entry_url": reverse("api:testimonials"),
                    "total": TestimonialList.get_base_queryset().count(),
                }
            }
        }


class TeachersView(generic.ListView):
    template_name = "center_teacher_list.html"
    context_object_name = "teachers"

    def get_queryset(self):
        qs = (CSCUser.objects
              .filter(groups=CSCUser.group.TEACHER_CENTER,
                      courseofferingteacher__roles=CourseOfferingTeacher.roles.lecturer)
              .distinct())
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Consider the last 3 academic years. Teacher is active, if he read
        # course in this period or will in the future.
        year, term_type = get_current_term_pair(settings.DEFAULT_CITY_CODE)
        term_index = get_term_index_academic_year_starts(year, term_type)
        term_index -= 2 * TERMS_IN_ACADEMIC_YEAR
        active_lecturers = Counter(
            CourseOffering.objects
            .filter(semester__index__gte=term_index)
            .values_list("teachers__pk", flat=True)
        )
        context["active"] = filter(lambda t: t.pk in active_lecturers,
                                   context[self.context_object_name])
        context["others"] = filter(lambda t: t.pk not in active_lecturers,
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


class AlumniHonorBoardView(TemplateView):
    def get_template_names(self):
        graduation_year = int(self.kwargs['year'])
        return [
            f"cscenter/alumni/{graduation_year}.html",
            "cscenter/alumni/fallback_year.html"
        ]

    def get_graduates(self, filters):
        return (CSCUser.objects
                .filter(**filters)
                .distinct()
                .only("pk", "first_name", "last_name", "patronymic", "gender",
                      "cropbox_data", "photo")
                .order_by("last_name", "first_name"))

    def get_context_data(self, **kwargs):
        graduation_year = int(self.kwargs['year'])
        preview = self.request.GET.get('preview', False)
        filters = {
            "groups__pk": CSCUser.group.GRADUATE_CENTER,
            "graduation_year": graduation_year
        }
        if preview and self.request.user.is_curator:
            filters = {"status": CSCUser.STATUS.will_graduate}
        graduates = self.get_graduates(filters)
        if not len(graduates):
            raise Http404
        cache_key = f'alumni_{graduation_year}_testimonials'
        testimonials = cache.get(cache_key)
        if testimonials is None:
            s = (CSCUser.objects
                 .filter(**filters)
                 .exclude(csc_review='')
                 .prefetch_related("areas_of_study"))
            testimonials = s[:]
            cache.set(cache_key, testimonials, 3600)
        # Get random testimonials
        testimonials_count = len(testimonials) if testimonials else 0
        indexes = random.sample(range(testimonials_count),
                                min(testimonials_count, 4))
        random_testimonials = [testimonials[index] for index in indexes]
        context = {
            "graduation_year": graduation_year,
            "graduates": graduates,
            "testimonials": random_testimonials
        }
        return context


class AlumniV2View(generic.TemplateView):
    template_name = "cscenter/alumni.html"

    def get_context_data(self, **kwargs):
        app_data = {
            "entry_url": reverse("api:alumni"),
            "state": {
                # FIXME: default values?
                "area": self.kwargs.get("area", None),
                "city": self.kwargs.get("city", None),
                "query": self.kwargs.get("query", ""),
                "year": self.kwargs.get("year", None)
            },
            "options": {
                "cities": [{"label": str(v), "value": k} for k, v
                           in settings.CITIES.items()],
                "areas": [{"label": a.name, "value": a.code} for a
                          in AreaOfStudy.objects.all()],
                # TODO: retrieve last year?
                "years": [{"label": y, "value": y} for y in range(2013, now().year)]
            }
        }
        return {
            "app_data": app_data
        }


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


class CourseOfferingsView(FilterMixin, TemplateView):
    filterset_class = CoursesFilter
    template_name = "learning/courses/offerings.html"

    def get_queryset(self):
        return (CourseOffering.objects
                .get_offerings_base_queryset()
                .exclude(semester__type=Semester.TYPES.summer))

    def get_context_data(self, **kwargs):
        filterset_class = self.get_filterset_class()
        filterset = self.get_filterset(filterset_class)
        if not filterset.form.is_valid():
            raise Redirect(to=reverse("course_list"))
        TERM_TYPES = {
            Semester.TYPES.autumn: pgettext_lazy("adjective", "autumn"),
            Semester.TYPES.spring: pgettext_lazy("adjective", "spring"),
        }
        courses = filterset.qs
        terms = group_terms_by_academic_year(courses)
        active_academic_year, active_type = self.get_term(filterset, courses)
        if active_type == Semester.TYPES.spring:
            active_year = active_academic_year + 1
        else:
            active_year = active_academic_year
        active_slug = "{}-{}".format(active_year, active_type)
        active_city = filterset.data['city']
        serializer = CourseOfferingSerializer(courses)
        courses = serializer.data
        context = {
            "TERM_TYPES": TERM_TYPES,
            "cities": filterset.form.fields['city'].choices,
            "terms": terms,
            "courses": courses,
            "active_city": active_city,
            "active_academic_year": active_academic_year,
            "active_type": active_type,
            "active_slug": active_slug,
            "json": JSONRenderer().render({
                "city": filterset.data['city'],
                "initialFilterState": {
                    "academicYear": active_academic_year,
                    "selectedTerm": active_type,
                    "termSlug": active_slug
                },
                "terms": terms,
                "termOptions": TERM_TYPES,
                "courses": courses
            }),
        }
        return context

    def get_term(self, filters, courses):
        # Not sure this is the best place for this method
        assert filters.form.is_valid()
        if "semester" in filters.data:
            valid_slug = filters.data["semester"]
            term_year, term_type = valid_slug.split("-")
            term_year = int(term_year)
        else:
            # By default, return academic year and term type for latest
            # available CO.
            if courses:
                # Note: may hit db if `filters.qs` not cached
                term = courses[0].semester
                term_year = term.year
                term_type = term.type
            else:
                return None
        idx = get_term_index_academic_year_starts(term_year, term_type)
        academic_year, _ = get_term_by_index(idx)
        return academic_year, term_type
