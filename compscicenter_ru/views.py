# -*- coding: utf-8 -*-

import itertools
import math
import random
from enum import Enum
from typing import NamedTuple, Optional

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.cache import cache, caches
from django.core.exceptions import ValidationError
from django.core.validators import validate_integer
from django.db.models import Q
from django.http import Http404
from django.utils.timezone import now
from django.utils.translation import gettext, pgettext_lazy, ugettext_lazy as _
from django.views import generic
from django_filters.views import FilterMixin
from rest_framework.renderers import JSONRenderer
from vanilla import TemplateView

from announcements.models import Announcement
from compscicenter_ru.serializers import CoursesSerializer
from compscicenter_ru.utils import group_terms_by_academic_year
from core.exceptions import Redirect
from core.models import Faq
from core.urls import reverse
from courses.models import Course, Semester
from courses.settings import SemesterTypes
from courses.utils import get_current_term_pair, \
    get_term_index_academic_year_starts, get_term_by_index
from learning.models import Branch, Enrollment, GraduateProfile
from learning.projects.constants import ProjectTypes
from learning.projects.models import ProjectStudent
from learning.settings import Branches
from online_courses.models import OnlineCourse, OnlineCourseTuple
from publications.models import ProjectPublication
from stats.views import StudentsDiplomasStats
from study_programs.models import StudyProgram, AcademicDiscipline
from users.models import User, SHADCourseRecord
from .filters import CoursesFilter

# FIXME: remove?
TESTIMONIALS_CACHE_KEY = 'v2_index_page_testimonials'


def get_random_testimonials(count, cache_key, **filters):
    """Returns reviews from graduated students with photo"""
    testimonials = cache.get(cache_key)
    if testimonials is None:
        testimonials = (GraduateProfile.active
                        .filter(**filters)
                        .with_testimonial()
                        .prefetch_related("academic_disciplines")
                        .order_by('?'))[:count]
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
        testimonials = get_random_testimonials(4, TESTIMONIALS_CACHE_KEY)
        _cache = caches['social_networks']
        context = {
            'testimonials': testimonials,
            'courses': courses,
            'vk_news': _cache.get(self.VK_CACHE_KEY),
            'instagram_posts': _cache.get(self.INSTAGRAM_CACHE_KEY),
            'is_admission_active': False,
            'announcements': list(Announcement.current
                                  .select_related("event_details",
                                                  "event_details__venue")
                                  .prefetch_related("tags"))
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
    template_name = "compscicenter_ru/enrollment/checklist.html"


class EnrollmentPreparationProgramView(generic.TemplateView):
    template_name = "compscicenter_ru/enrollment/preparation_program.html"


def positive_integer(value):
    validate_integer(value)
    value = int(value)
    if value <= 0:
        raise ValidationError("Negative integer is not allowed here")
    return value


class TestimonialsListView(TemplateView):
    template_name = "compscicenter_ru/testimonials.html"

    def get_context_data(self, **kwargs):
        total = GraduateProfile.active.with_testimonial().count()
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


class AlumniHonorBoardView(TemplateView):
    def get_template_names(self):
        graduation_year = int(self.kwargs['year'])
        if graduation_year <= 2017:
            return "compscicenter_ru/alumni_by_year.html"
        return [
            f"compscicenter_ru/alumni/{graduation_year}.html",
            "compscicenter_ru/alumni/fallback_year.html"
        ]

    def get_context_data(self, **kwargs):
        graduation_year = int(self.kwargs['year'])
        preview = self.request.GET.get('preview', False)
        if not preview or not self.request.user.is_curator:
            manager = GraduateProfile.active
        else:
            manager = GraduateProfile.objects.select_related("student")
        graduates = list(manager
                         .filter(graduation_year=graduation_year)
                         .prefetch_related("academic_disciplines")
                         .order_by("student__last_name"))
        if not len(graduates):
            raise Http404
        # Get random testimonials
        # FIXME: Prefetch areas_of_study for random testimonials only
        with_testimonial = [gp for gp in graduates if gp.testimonial]
        indexes = random.sample(range(len(with_testimonial)),
                                min(len(with_testimonial), 4))
        random_testimonials = [with_testimonial[index] for index in indexes]
        context = {
            "graduation_year": graduation_year,
            "graduates": graduates,
            "testimonials": random_testimonials
        }
        if graduation_year <= 2017:
            is_curator = self.request.user.is_curator
            cache_key = f'alumni_{graduation_year}_stats_{is_curator}'
            stats = cache.get(cache_key)
            if stats is None:
                stats = StudentsDiplomasStats.as_view()(self.request,
                                                        graduation_year,
                                                        **kwargs).data
                cache.set(cache_key, stats, 3600 * 24 * 31)
            context["stats"] = stats
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
        context["testimonials"] = get_random_testimonials(
            4, cache_key, academic_disciplines=discipline_code)
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


class CourseVideoListView(TemplateView):
    template_name = "compscicenter_ru/courses_video_list.html"

    def get_context_data(self, **kwargs):
        video_types = [
            {"value": "course", "label": gettext("Course")},
            {"value": "lecture", "label": gettext("Lecture")},
        ]
        app_data = {
            "props": {
                "entry_url": [
                    reverse("api:course_video_records"),
                    reverse("api:recorded_events_videos"),
                ],
                "videoTypes": video_types
            },
            "state": {
                "videoTypes": [item["value"] for item in video_types]
            },
        }
        return {"app_data": app_data}


class ProjectsListView(TemplateView):
    template_name = "compscicenter_ru/projects/project_list.html"

    def get_context_data(self, **kwargs):
        return {
            "practice_projects": (ProjectPublication.objects
                                  .filter(is_draft=False,
                                          type=ProjectTypes.practice)
                                  .order_by('title')),
            "research_projects": (ProjectPublication.objects
                                  .filter(is_draft=False,
                                          type=ProjectTypes.research)
                                  .order_by('title'))
        }


class TimelineElementTypes(Enum):
    COURSE = 1
    SHAD = 2
    PRACTICE = 3
    RESEARCH = 4


class TimelineElement(NamedTuple):
    term: Semester
    type: Enum
    name: str
    url: Optional[str]
    grade: str


def timeline_element_factory(obj) -> TimelineElement:
    if isinstance(obj, SHADCourseRecord):
        return TimelineElement(term=obj.semester,
                               type=TimelineElementTypes.SHAD,
                               name=obj.name,
                               url=None,
                               grade=obj.get_grade_display())
    elif isinstance(obj, ProjectStudent):
        if obj.project.project_type == ProjectTypes.practice:
            project_type = TimelineElementTypes.PRACTICE
        else:
            project_type = TimelineElementTypes.RESEARCH
        return TimelineElement(term=obj.project.semester,
                               type=project_type,
                               name=obj.project.name,
                               url=None,
                               grade=obj.get_final_grade_display())
    elif isinstance(obj, Enrollment):
        return TimelineElement(term=obj.course.semester,
                               type=TimelineElementTypes.COURSE,
                               name=obj.course.meta_course.name,
                               url=obj.course.get_absolute_url(),
                               grade=obj.get_grade_display())
    else:
        raise TypeError("timeline_element_factory: Unsupported object")


class StudentProfileView(generic.DetailView):
    pk_url_kwarg = "student_id"
    context_object_name = "student"

    def get_queryset(self):
        return User.objects.select_related("graduate_profile")

    def get_template_names(self):
        if hasattr(self.object, 'graduate_profile'):
            return "compscicenter_ru/profiles/graduate.html"
        raise Http404

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.object
        timeline_elements = []
        # TODO: move to timeline queryset
        exclude_grades = [Enrollment.GRADES.NOT_GRADED,
                          Enrollment.GRADES.UNSATISFACTORY]
        enrollments = (Enrollment.active
                       .filter(student=student)
                       .exclude(grade__in=exclude_grades)
                       .select_related('course',
                                       'course__semester',
                                       'course__meta_course')
                       .order_by("course__semester__index",
                                 "course__meta_course__name"))
        for e in enrollments:
            timeline_elements.append(timeline_element_factory(e))
        shad_courses = (SHADCourseRecord.objects
                        .filter(student=student)
                        .exclude(grade__in=exclude_grades)
                        .select_related("semester")
                        .order_by("semester__index", "name"))
        for c in shad_courses:
            timeline_elements.append(timeline_element_factory(c))
        projects = (student.get_projects_queryset()
                    .exclude(final_grade__in=exclude_grades))
        for c in projects:
            timeline_elements.append(timeline_element_factory(c))
        timeline_elements.sort(key=lambda o: (o.term.index, o.type.value))
        timeline = {}
        for k, g in itertools.groupby(timeline_elements, key=lambda o: o.term):
            timeline[k] = list(g)
        context["timeline"] = timeline
        context["timeline_element_types"] = TimelineElementTypes
        return context
