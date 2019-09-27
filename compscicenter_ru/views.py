# -*- coding: utf-8 -*-

import math
import random
from enum import Enum
from typing import NamedTuple, Optional

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.cache import cache, caches
from django.core.exceptions import ValidationError
from django.core.validators import validate_integer
from django.db.models import Q, Max, Prefetch
from django.http import Http404
from django.utils.timezone import now
from django.utils.translation import gettext, ugettext_lazy as _
from django.views import generic
from vanilla import TemplateView, DetailView

from announcements.models import Announcement
from compscicenter_ru.utils import Tab, TabList
from core.exceptions import Redirect
from core.models import Branch
from core.urls import reverse
from core.utils import bucketize
from courses.constants import SemesterTypes, TeacherRoles, ClassTypes
from courses.models import Course, Semester, MetaCourse, CourseTeacher, \
    group_course_teachers
from courses.utils import get_current_term_pair, \
    first_term_in_academic_year
from courses.views.mixins import CourseURLParamsMixin
from faq.models import Question
from learning.models import Enrollment, GraduateProfile
from learning.roles import Roles
from learning.settings import Branches
from online_courses.models import OnlineCourse, OnlineCourseTuple
from projects.constants import ProjectTypes
from projects.models import ProjectStudent
from publications.models import ProjectPublication
from stats.views import StudentsDiplomasStats
from study_programs.models import StudyProgram, AcademicDiscipline
from study_programs.services import get_study_programs
from users.models import User, SHADCourseRecord

# FIXME: remove?
TESTIMONIALS_CACHE_KEY = 'v2_index_page_testimonials'


def _get_branch_choices():
    """Restrict displayed branches on /alumni/ and /teachers/ pages"""
    choices = []
    for branch_code in (Branches.SPB, Branches.NSK):
        branch = Branches.get_choice(branch_code)
        choices.append({"label": str(branch.label), "value": branch.value})
    return choices


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
        return (Question.objects
                .filter(site=settings.SITE_ID)
                .order_by("sort"))


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
                    "entry_url": reverse("public-api:v2:testimonials"),
                    "total": total,
                }
            }
        }


class TeachersView(TemplateView):
    template_name = "compscicenter_ru/teachers.html"

    def get_context_data(self, **kwargs):
        # Get terms in last 3 academic years.
        year, term_type = get_current_term_pair()
        term_index = first_term_in_academic_year(year, term_type)
        term_index -= 2 * len(SemesterTypes.choices)
        app_data = {
            "state": {
                "branch": self.kwargs.get("city", None),
            },
            "props": {
                "entryURL": reverse("public-api:v2:teachers"),
                "coursesURL": reverse("public-api:v2:teachers_courses"),
                "branchOptions": _get_branch_choices(),
                "termIndex": term_index,
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
        first_graduation = 2013
        cache_key = 'cscenter_last_graduation_year'
        last_graduation_year = cache.get(cache_key)
        if last_graduation_year is None:
            d = GraduateProfile.objects.aggregate(year=Max('graduation_year'))
            last_graduation_year = d['year'] if d['year'] else first_graduation
            cache.set(cache_key, last_graduation_year, 86400 * 31)
        years_range = range(first_graduation, last_graduation_year + 1)
        years = [{"label": str(y), "value": y} for y in reversed(years_range)]
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
                "branch": self.kwargs.get("city", None),
            },
            "props": {
                "entryURL": reverse("public-api:v2:alumni"),
                "branchOptions": _get_branch_choices(),
                "areaOptions": areas,
                "yearOptions": years
            }
        }
        return {"app_data": app_data}


class OnCampusProgramsView(generic.TemplateView):
    template_name = "compscicenter_ru/programs/on_campus.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Active programs grouped by branch
        current_programs = (StudyProgram.objects
                            .filter(is_active=True)
                            .exclude(branch__city=None)
                            .select_related("branch", "academic_discipline")
                            .order_by("branch",
                                      "academic_discipline__name_ru"))
        current_programs = bucketize(current_programs, key=lambda sp: sp.branch)
        tabs = TabList()
        selected_branch = self.request.GET.get('branch', Branches.SPB)
        for i, branch in enumerate(current_programs):
            tab = Tab(target=branch.code,
                      name=branch.name,
                      url=f"{self.request.path}?branch={branch.code}",
                      order=branch.order)
            # Mark first tab as active by default
            if i == 0:
                tab.active = True
            tabs.add(tab)
            if branch.code == selected_branch:
                tabs.set_active(branch.code)
        tabs.sort()
        context["tabs"] = tabs
        context["programs"] = current_programs
        return context


class OnCampusProgramDetailView(generic.TemplateView):
    template_name = "compscicenter_ru/programs/on_campus_detail.html"

    def get_context_data(self, discipline_code, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_branch = self.request.GET.get('branch', Branches.SPB)
        study_program = (StudyProgram.objects
                         .filter(academic_discipline__code=discipline_code,
                                 branch__code=selected_branch,
                                 is_active=True)
                         .exclude(branch__city=None)
                         .prefetch_core_courses_groups()
                         .select_related("branch", "academic_discipline")
                         .first())
        if not study_program:
            raise Http404

        # Collect tabs with cities where academic discipline is presented
        tabs = TabList()
        branches = (Branch.objects
                    .filter(study_programs__academic_discipline__code=discipline_code,
                            study_programs__is_active=True)
                    .exclude(city=None))
        for branch in branches:
            tab = Tab(target=branch.code, name=branch.name,
                      url=f"{self.request.path}?branch={branch.code}",
                      order=branch.order)
            if branch.code == selected_branch:
                tab.active = True
            tabs.add(tab)
        tabs.sort()

        cache_key = f"{TESTIMONIALS_CACHE_KEY}_{discipline_code}"
        random_testimonials = get_random_testimonials(
            4, cache_key, academic_disciplines=discipline_code)

        context["study_program"] = study_program
        context["tabs"] = tabs
        context["testimonials"] = random_testimonials
        return context


class DistanceProgramView(generic.TemplateView):
    template_name = "compscicenter_ru/programs/distance.html"


class OpenNskView(generic.TemplateView):
    template_name = "open_nsk.html"


class CourseVideoListView(TemplateView):
    template_name = "compscicenter_ru/courses_video_list.html"

    def get_context_data(self, **kwargs):
        video_types = [
            {"value": "course", "label": gettext("Course")},
            {"value": "lecture", "label": gettext("Lecture")},
        ]
        app_data = {
            "props": {
                "entryURL": [
                    reverse("public-api:v2:course_videos"),
                    reverse("public-api:v2:recorded_events_videos"),
                ],
                "videoOptions": video_types
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
        return User.objects.select_related("branch", "graduate_profile")

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
        timeline = bucketize(timeline_elements, key=lambda o: o.term)
        context["timeline"] = timeline
        context["timeline_element_types"] = TimelineElementTypes
        return context


class MetaCourseDetailView(generic.DetailView):
    model = MetaCourse
    slug_url_kwarg = 'course_slug'
    template_name = "compscicenter_ru/courses/meta_course_detail.html"
    context_object_name = 'meta_course'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Collect courses including compsciclub.ru records
        branches = [code for code, _ in Branches.choices]
        lecturers = CourseTeacher.lecturers_prefetch()
        courses = (Course.objects
                   .filter(meta_course=self.object,
                           branch__code__in=branches)
                   .select_related("meta_course", "semester", "branch")
                   .prefetch_related(lecturers)
                   .order_by('-semester__index'))
        grouped = bucketize(courses, key=lambda c: c.branch.code)
        # Aggregate tabs
        tabs = TabList()
        for branch_code in grouped:
            if grouped[branch_code]:
                branch = Branches.get_choice(branch_code)
                tabs.add(Tab(target=branch.value, name=branch.label,
                             order=branch.order))
        if tabs:
            selected_tab = self.request.GET.get('branch', Branches.SPB)
            tabs.set_active(selected_tab)  # deactivates all other tabs
            if selected_tab not in tabs:
                first_tab = next(iter(tabs))
                first_tab.active = True
            tabs.sort()
        context['tabs'] = tabs
        context['grouped_courses'] = grouped
        active_study_programs = get_study_programs(self.object.pk,
                                                   filters=[Q(is_active=True)])
        context['study_programs'] = active_study_programs
        return context


class CourseDetailView(CourseURLParamsMixin, generic.DetailView):
    model = MetaCourse
    template_name = "compscicenter_ru/courses/course_detail.html"
    context_object_name = 'course'

    def get_course_queryset(self):
        course_teachers = Prefetch('course_teachers',
                                   queryset=(CourseTeacher.objects
                                             .select_related("teacher")))
        return (super().get_course_queryset()
                .select_related('meta_course', 'semester', 'branch')
                .prefetch_related(course_teachers))

    def get_object(self):
        return self.course

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tabs = TabList([
            Tab(target='about',
                name=_('About the Course'),
                url=self.course.get_absolute_url(subdomain=None),
                active=True),
            Tab(target='classes',
                name=_('Lectures List'),
                url=self.course.get_absolute_url(tab='classes',
                                                 subdomain=None)),
        ])
        show_tab = self.kwargs.get('tab', 'about')
        tabs.set_active(show_tab)
        teachers = group_course_teachers(self.course.course_teachers
                                         .order_by('teacher__last_name',
                                                   'teacher__first_name'))
        context['tabs'] = tabs
        context['teachers'] = {TeacherRoles.get_choice(k): v for k, v in
                               teachers.items()}
        context['classes'] = (self.course.courseclass_set
                              .filter(type=ClassTypes.LECTURE)
                              .order_by("date", "starts_at"))
        return context


class TeacherDetailView(DetailView):
    template_name = "users/teacher_detail.html"
    context_object_name = 'teacher'

    def get_queryset(self, *args, **kwargs):
        branches = [code for code, _ in Branches.choices]
        courses = (Course.objects
                   .filter(branch__code__in=branches)
                   .select_related('semester', 'meta_course', 'branch')
                   .order_by('-semester__index'))
        return (User.objects
                .filter(group__role=Roles.TEACHER)
                .distinct()
                .prefetch_related(
                    Prefetch('teaching_set',
                             queryset=courses,
                             to_attr='course_offerings')))


class CourseOfferingsView(TemplateView):
    template_name = "compscicenter_ru/courses/course_list.html"

    def get_context_data(self, **kwargs):
        branches = [{"label": str(l), "value": v} for v, l in Branches.choices]
        academic_disciplines = [{'label': a.name, 'value': a.code} for a in
                                AcademicDiscipline.objects.all()]
        current, term = get_current_term_pair()
        years = [{"label": str(y), "value": y} for y in
                 range(current, settings.CENTER_FOUNDATION_YEAR - 1, -1)]
        semesters = [
            {'value': SemesterTypes.AUTUMN, 'label': str(_('Autumn|adjective'))},
            {'value': SemesterTypes.SPRING, 'label': str(_('Spring|adjective'))}
        ]
        app_data = {
            'props': {
                'entryURL': [reverse('public-api:v2:course_list')],
                'branchOptions': branches,
                'yearOptions': years,
                'academicDisciplinesOptions': academic_disciplines,
                'semesterOptions': semesters
            },
            'state': {
                'year': years[0],
                'branch': branches[0]['value'],
                'semesters': [term],
            },
        }
        return {"app_data": app_data}
