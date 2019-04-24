# -*- coding: utf-8 -*-

import itertools
import math
import random

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.cache import cache, caches
from django.core.exceptions import ValidationError
from django.core.validators import validate_integer
from django.db.models import Q, Prefetch
from django.http import Http404
from django.http.response import HttpResponseNotFound
from django.utils.timezone import now
from django.utils.translation import pgettext_lazy
from django.views import generic
from django.views.generic import ListView
from django_filters.views import FilterMixin
from rest_framework.renderers import JSONRenderer
from vanilla import TemplateView

from compscicenter_ru.serializers import CoursesSerializer
from compscicenter_ru.utils import group_terms_by_academic_year
from core.exceptions import Redirect
from core.models import Faq
from core.settings.base import CENTER_FOUNDATION_YEAR
from core.urls import reverse
from courses.models import Course, CourseTeacher
from courses.settings import SemesterTypes
from courses.utils import get_current_term_pair, \
    get_term_index_academic_year_starts, get_term_by_index
from learning.api.views import TestimonialList
from learning.models import Branch
from learning.projects.models import Project
from learning.settings import StudentStatuses, Branches
from online_courses.models import OnlineCourse, OnlineCourseTuple
from publications.models import ProjectPublication
from stats.views import StudentsDiplomasStats
from study_programs.models import StudyProgram, AcademicDiscipline
from users.models import User
from .filters import CoursesFilter

TESTIMONIALS_CACHE_KEY = 'v2_index_page_testimonials'


def get_random_testimonials(count, cache_key, filters=None):
    """Returns reviews from graduated students with photo"""
    testimonials = cache.get(cache_key)
    filters = filters or {}
    if testimonials is None:
        # TODO: Выбрать только нужные поля
        s = (User.objects
             .filter(groups=User.roles.GRADUATE_CENTER, **filters)
             .exclude(csc_review='').exclude(photo='')
             .prefetch_related("areas_of_study")
             .order_by('?'))[:count]
        testimonials = s
        cache.set(cache_key, testimonials, 3600)
    return testimonials


class IndexView(TemplateView):
    template_name = 'compscicenter_ru/index.html'
    VK_CACHE_KEY = 'v2_index_vk_social_news'
    INSTAGRAM_CACHE_KEY = 'v2_index_instagram_posts'

    def get_context_data(self, **kwargs):
        # Online programs + online courses
        courses = [
            OnlineCourseTuple('Алгоритмы и эффективные вычисления',
                              'https://code.stepik.org/algo/',
                              staticfiles_storage.url('v2/img/pages/index/online_programs/algo.jpg'),
                              'Онлайн-программа'),
            OnlineCourseTuple('Математика для разработчика',
                              'https://code.stepik.org/math/',
                              staticfiles_storage.url('v2/img/pages/index/online_programs/math.jpg'),
                              'Онлайн-программа'),
            OnlineCourseTuple('Разработка на C++, Java и Haskell',
                              'https://code.stepik.org/dev/',
                              staticfiles_storage.url('v2/img/pages/index/online_programs/dev.jpg'),
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
        testimonials = get_random_testimonials(4, TESTIMONIALS_CACHE_KEY)
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
    template_name = "compscicenter_ru/team.html"


class QAListView(generic.ListView):
    context_object_name = "faq"
    template_name = "compscicenter_ru/faq.html"

    def get_queryset(self):
        return Faq.objects.filter(site=settings.CENTER_SITE_ID).order_by("sort")


class EnrollmentChecklistView(generic.TemplateView):
    template_name = "compscicenter_ru/enrollment_checklist.html"


def positive_integer(value):
    validate_integer(value)
    value = int(value)
    if value <= 0:
        raise ValidationError("Negative integer is not allowed here")
    return value


class TestimonialsListView(TemplateView):
    template_name = "compscicenter_ru/testimonials.html"

    def get_context_data(self, **kwargs):
        total = TestimonialList.get_base_queryset().count()
        page_size = 16
        try:
            current_page = positive_integer(self.request.GET.get("page", 1))
        except ValidationError:
            raise Http404
        max_page = math.ceil(total / page_size)
        if current_page > max_page:
            base_url = reverse('testimonials')
            raise Redirect(to=f"{base_url}?page={max_page}")
        return {
            "app_data": {
                "state": {
                    "page": current_page,
                },
                "props": {
                    "page_size": page_size,
                    "entry_url": reverse("api:testimonials"),
                    "total": total,
                }
            }
        }


class TeachersView(TemplateView):
    template_name = "compscicenter_ru/teachers.html"

    def get_context_data(self, **kwargs):
        # Get terms in last 3 academic years.
        year, term_type = get_current_term_pair(settings.DEFAULT_CITY_CODE)
        term_index = get_term_index_academic_year_starts(year, term_type)
        term_index -= 2 * len(SemesterTypes.choices)
        app_data = {
            "state": {
                "city": self.kwargs.get("city", None),
            },
            "props": {
                "entry_url": reverse("api:teachers"),
                "courses_url": reverse("api:courses"),
                "cities": [{"label": str(v), "value": k} for k, v
                           in settings.CITIES.items()],
                "term_index": term_index,
            }
        }
        return {"app_data": app_data}


class AlumniByYearView(generic.ListView):
    context_object_name = "alumni_list"
    template_name = "compscicenter_ru/alumni_by_year.html"

    def get(self, request, *args, **kwargs):
        year = int(self.kwargs['year'])
        now__year = now().year
        # No graduates in first 2 years after foundation
        if year < CENTER_FOUNDATION_YEAR + 2 or year > now__year:
            return HttpResponseNotFound()
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        year = int(self.kwargs['year'])
        filters = (Q(groups__pk=User.roles.GRADUATE_CENTER) &
                   Q(graduation_year=year))
        if year == now().year and self.request.user.is_curator:
            filters = filters | Q(status=StudentStatuses.WILL_GRADUATE)
        return (User.objects
                .filter(filters)
                .distinct()
                .order_by("-graduation_year", "last_name", "first_name"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = int(self.kwargs['year'])
        context["year"] = year
        testimonials = cache.get('alumni_{}_testimonials'.format(year))
        if testimonials is None:
            s = (User.objects
                 .filter(
                    groups=User.roles.GRADUATE_CENTER,
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
            f"compscicenter_ru/alumni/{graduation_year}.html",
            "compscicenter_ru/alumni/fallback_year.html"
        ]

    def get_graduates(self, filters):
        return (User.objects
                .filter(**filters)
                .distinct()
                .only("pk", "first_name", "last_name", "patronymic", "gender",
                      "cropbox_data", "photo")
                .order_by("last_name", "first_name"))

    def get_context_data(self, **kwargs):
        graduation_year = int(self.kwargs['year'])
        preview = self.request.GET.get('preview', False)
        filters = {
            "groups__pk": User.roles.GRADUATE_CENTER,
            "graduation_year": graduation_year
        }
        if preview and self.request.user.is_curator:
            filters = {"status": StudentStatuses.WILL_GRADUATE}
        graduates = self.get_graduates(filters)
        if not len(graduates):
            raise Http404
        cache_key = f'alumni_{graduation_year}_testimonials'
        testimonials = cache.get(cache_key)
        if testimonials is None:
            s = (User.objects
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


class AlumniView(TemplateView):
    template_name = "compscicenter_ru/alumni/index.html"

    def get_context_data(self):
        # TODO: Move to the proxy model `Graduate`
        first_graduation_year = 2013
        cache_key = 'cscenter_last_graduation_year'
        last_graduation_year = cache.get(cache_key)
        if last_graduation_year is None:
            from_last_graduation = (User.objects
                                    .filter(groups=User.roles.GRADUATE_CENTER)
                                    .exclude(graduation_year__isnull=True)
                                    .order_by("-graduation_year")
                                    .only("graduation_year")
                                    .first())
            if from_last_graduation:
                last_graduation_year = from_last_graduation.graduation_year
            else:
                last_graduation_year = first_graduation_year
            cache.set(cache_key, last_graduation_year, 86400 * 31)
        years_range = range(first_graduation_year, last_graduation_year + 1)
        years = [{"label": y, "value": y} for y in reversed(years_range)]
        year = self.kwargs.get("year")
        if year not in years_range:
            year = last_graduation_year
        year = next((y for y in years if y['value'] == year))
        # Area state and props
        areas = [{"label": a.name, "value": a.code} for a in
                 AcademicDiscipline.objects.all()]
        area = self.kwargs.get("area", None)
        if area:
            try:
                area = next((a for a in areas if a['value'] == area))
            except StopIteration:
                raise Http404
        app_data = {
            "state": {
                "year": year,
                "area": area,
                "city": self.kwargs.get("city", None),
            },
            "props": {
                "entry_url": reverse("api:alumni"),
                "cities": [{"label": str(v), "value": k} for k, v
                           in settings.CITIES.items()],
                "areas": areas,
                "years": years
            }
        }
        return {"app_data": app_data}


class OnCampusProgramsView(generic.TemplateView):
    template_name = "compscicenter_ru/programs/on_campus.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        study_programs = (StudyProgram.objects
                          .filter(is_active=True,
                                  branch__is_remote=False)
                          .select_related("branch", "academic_discipline")
                          .order_by("branch_id", "academic_discipline__name_ru"))
        context["programs"] = self.group_programs_by_branch(study_programs)
        context["selected_branch"] = self.request.GET.get('branch', Branches.SPB)
        return context

    def group_programs_by_branch(self, syllabus):
        grouped = {}
        for branch, g in itertools.groupby(syllabus, key=lambda sp: sp.branch):
            grouped[branch] = list(g)
        return grouped


class OnCampusProgramDetailView(generic.TemplateView):
    template_name = "compscicenter_ru/programs/on_campus_detail.html"

    def get_context_data(self, discipline_code, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_branch = self.request.GET.get('branch', Branches.SPB)
        study_program = (StudyProgram.objects
                         .filter(academic_discipline__code=discipline_code,
                                 branch__code=selected_branch,
                                 branch__is_remote=False,
                                 is_active=True)
                         .prefetch_core_courses_groups()
                         .select_related("branch", "academic_discipline")
                         .first())
        if not study_program:
            raise Http404
        context["study_program"] = study_program
        # Testimonials
        cache_key = f"{TESTIMONIALS_CACHE_KEY}_{discipline_code}"
        filters = {"areas_of_study": discipline_code}
        context["testimonials"] = get_random_testimonials(4, cache_key, filters)
        context["branches"] = (Branch.objects
                               .filter(study_programs__academic_discipline__code=discipline_code,
                                       study_programs__is_active=True,
                                       is_remote=False))
        context["selected_branch"] = selected_branch
        return context


class DistanceProgramView(generic.TemplateView):
    template_name = "compscicenter_ru/programs/distance.html"


class OpenNskView(generic.TemplateView):
    template_name = "open_nsk.html"


class CourseOfferingsView(FilterMixin, TemplateView):
    filterset_class = CoursesFilter
    template_name = "compscicenter_ru/course_offerings.html"

    def get_queryset(self):
        return (Course.objects
                .get_offerings_base_queryset()
                .exclude(semester__type=SemesterTypes.SUMMER))

    def get_context_data(self, **kwargs):
        filterset_class = self.get_filterset_class()
        filterset = self.get_filterset(filterset_class)
        if not filterset.is_valid():
            raise Redirect(to=reverse("course_list"))
        term_options = {
            SemesterTypes.AUTUMN: pgettext_lazy("adjective", "autumn"),
            SemesterTypes.SPRING: pgettext_lazy("adjective", "spring"),
        }
        courses = filterset.qs
        terms = group_terms_by_academic_year(courses)
        active_academic_year, active_type = self.get_term(filterset, courses)
        if active_type == SemesterTypes.SPRING:
            active_year = active_academic_year + 1
        else:
            active_year = active_academic_year
        active_slug = "{}-{}".format(active_year, active_type)
        active_city = filterset.data['city']
        serializer = CoursesSerializer(courses)
        courses = serializer.data
        context = {
            "TERM_TYPES": term_options,
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
                "termOptions": term_options,
                "courses": courses
            }).decode('utf-8'),
        }
        return context

    def get_term(self, filters, courses):
        # Not sure this is the best place for this method
        assert filters.is_valid()
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


class CourseVideoListView(ListView):
    model = Course
    template_name = "compscicenter_ru/courses_video_list.html"
    context_object_name = 'course_list'

    def get_queryset(self):
        lecturer = CourseTeacher.roles.lecturer
        lecturers = Prefetch(
            'course_teachers',
            queryset=(CourseTeacher.objects
                      .filter(roles=lecturer)
                      .select_related('teacher')))
        # FIXME: filter by completed_at
        return (Course.objects
                .filter(is_published_in_video=True)
                .in_center_branches()
                .order_by('-semester__year', 'semester__type')
                .select_related('meta_course', 'semester')
                .prefetch_related(lecturers))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_data'] = {
            "props": {
                "entry_url": reverse("api:course_video_records")
            }
        }
        return context


class ProjectsListView(TemplateView):
    template_name = "compscicenter_ru/projects/project_list.html"

    def get_context_data(self, **kwargs):
        return {
            "publications": (ProjectPublication.objects
                             .filter(is_draft=False,
                                     type=Project.ProjectTypes.practice)
                             .order_by('title'))
        }
