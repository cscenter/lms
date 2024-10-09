import math
import random
from enum import Enum
from typing import NamedTuple, Optional

from djchoices import C, DjangoChoices
from vanilla import DetailView, TemplateView

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.cache import cache, caches
from django.core.exceptions import ValidationError
from django.core.validators import validate_integer
from django.db.models import Count, F, Max, Min, Prefetch, Q, prefetch_related_objects
from django.http import Http404
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.views import generic

from announcements.models import Announcement
from compscicenter_ru.utils import (
    Tab, TabList, course_class_public_url, course_public_url
)
from core.exceptions import Redirect
from core.models import Branch
from core.urls import reverse
from core.utils import bucketize
from courses.constants import SemesterTypes, TeacherRoles
from courses.models import Course, CourseClass, CourseTeacher, MetaCourse, Semester
from courses.permissions import ViewCourseClassMaterials, can_view_private_materials
from courses.selectors import course_teachers_prefetch_queryset, get_lecturers
from courses.services import CourseService, group_teachers
from courses.utils import get_current_term_pair, get_term_index
from courses.views.mixins import CoursePublicURLParamsMixin
from faq.models import Question
from learning.models import Enrollment, GraduateProfile
from learning.services import course_access_role
from learning.settings import Branches, GradeTypes
from online_courses.models import OnlineCourse, OnlineCourseTuple
from projects.constants import ProjectGradeTypes, ProjectTypes
from projects.models import ProjectStudent
from stats.views import AlumniStats
from study_programs.models import AcademicDiscipline, StudyProgram
from study_programs.services import get_study_programs
from users.constants import Roles, SHADCourseGradeTypes
from users.models import SHADCourseRecord, User

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
                        .get_only_required_fields()
                        .prefetch_related("academic_disciplines")
                        .order_by('?'))[:count]
        # Can't pickle local object 'create_forward_many_to_many_manager..ManyRelatedManager'" when pickling academic_disciplines
        # cache.set(cache_key, testimonials, 3600)
    return testimonials


class PublicURLMixin:
    @staticmethod
    def public_url(obj, **kwargs):
        if isinstance(obj, Course):
            return course_public_url(obj, **kwargs)
        elif isinstance(obj, CourseClass):
            return course_class_public_url(obj)
        elif isinstance(obj, MetaCourse):
            return reverse('meta_course_detail',
                           kwargs={'course_slug': obj.slug})
        raise TypeError(f"{obj.__class__} is not supported")


class IndexView(TemplateView):
    template_name = 'compscicenter_ru/index.html'
    VK_CACHE_KEY = 'v2_index_vk_social_news'
    INSTAGRAM_CACHE_KEY = 'v2_index_instagram_posts'

    def get_context_data(self, **kwargs):
        # Online programs + online courses
        online_courses = [
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
            online_courses.append(OnlineCourseTuple(name=course.name,
                                                    link=course.link,
                                                    avatar_url=course.avatar_url,
                                                    tag='Онлайн-курс'))
        testimonials = get_random_testimonials(4, TESTIMONIALS_CACHE_KEY)
        _cache = caches['social_networks']
        context = {
            'testimonials': testimonials,
            'online_courses': online_courses,
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
        site_branches = Branch.objects.for_site(self.request.site.pk, all=True)
        total = (GraduateProfile.active
                 .filter(student_profile__branch__in=site_branches)
                 .with_testimonial()
                 .count())
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
                    "pageSize": page_size,
                    "endpoint": reverse("public-api:v2:testimonials"),
                    "total": total,
                }
            }
        }


class TeachersView(TemplateView):
    template_name = "compscicenter_ru/teachers.html"

    def get_context_data(self, **kwargs):
        # Calculates the min term index in the last 3 academic years.
        term_pair = get_current_term_pair()
        term_index = get_term_index(term_pair.academic_year,
                                    SemesterTypes.AUTUMN)
        term_index -= 2 * len(SemesterTypes.choices)
        app_data = {
            "state": {
                "branch": self.kwargs.get("city", None),
            },
            "props": {
                "endpoint": reverse("public-api:v2:teachers"),
                "coursesURL": reverse("public-api:v2:teachers_meta_courses"),
                "branchOptions": _get_branch_choices(),
                "termIndex": term_index,
            }
        }
        return {"app_data": app_data}


def get_alumni_bucket_key(graduate_profile):
    branch = graduate_profile.student_profile.branch
    return branch.order, branch.code, branch.name


def get_alumni_tabs(grouped_alumni):
    tabs = TabList()
    for i, (order, code, name) in enumerate(grouped_alumni.keys()):
        tabs.add(Tab(target=code, name=name, order=order, active=(i == 0)))
    tabs.sort()
    return tabs


class AlumniHonorBoardView(TemplateView):
    def get_template_names(self):
        graduation_year = int(self.kwargs['year'])
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
            manager = GraduateProfile.objects
        site_branches = Branch.objects.for_site(self.request.site.pk, all=True)
        graduates = list(manager
                         .filter(graduation_year=graduation_year,
                                 student_profile__branch__in=site_branches)
                         .get_only_required_fields()
                         .order_by("student_profile__user__last_name",
                                   "student_profile__user__first_name"))
        if not graduates:
            raise Http404
        # Get random testimonials
        with_testimonial = [gp for gp in graduates if gp.testimonial]
        indexes = random.sample(range(len(with_testimonial)),
                                min(len(with_testimonial), 4))
        random_testimonials = [with_testimonial[index] for index in indexes]
        if random_testimonials:
            prefetch_related_objects(random_testimonials, 'academic_disciplines')
        context = {
            "bucketize": bucketize,
            "get_bucket_key": get_alumni_bucket_key,
            "get_tabs": get_alumni_tabs,
            "graduation_year": graduation_year,
            "graduates": graduates,
            "testimonials": random_testimonials
        }
        if graduation_year <= 2017:
            key_pattern = GraduateProfile.STATS_CACHE_KEY_PATTERN
            cache_key = key_pattern.format(graduation_year=graduation_year,
                                           site_id=self.request.site.pk)
            stats = cache.get(cache_key)
            if stats is None:
                stats = AlumniStats.as_view()(self.request,
                                              graduation_year,
                                              **kwargs).data
                cache.set(cache_key, stats, 3600 * 24 * 31)
            context["stats"] = stats
        return context


class AlumniView(TemplateView):
    template_name = "compscicenter_ru/alumni/index.html"

    def get_context_data(self):
        cache_key_pattern = GraduateProfile.HISTORY_CACHE_KEY_PATTERN
        cache_key = cache_key_pattern.format(site_id=self.request.site.pk)
        history = cache.get(cache_key)
        today = now().date()
        site_branches = Branch.objects.for_site(self.request.site.pk, all=True)
        if history is None:
            history = (GraduateProfile.active
                       .filter(graduated_on__lte=today,
                               student_profile__branch__in=site_branches)
                       .aggregate(latest_graduation=Max('graduation_year'),
                                  first_graduation=Min('graduation_year')))
            cache.set(cache_key, history, 86400)  # cache for 1 day
        if history['first_graduation'] is None:
            raise Http404
        the_first_graduation = history['first_graduation']
        latest_graduation = history['latest_graduation']
        years_range = range(the_first_graduation, latest_graduation + 1)
        years = [{"label": str(y), "value": y} for y in reversed(years_range)]
        show_year = self.kwargs.get("year")
        if show_year not in years_range:
            show_year = latest_graduation
        year_option = next((y for y in years if y['value'] == show_year))
        # Branches
        branch_options = []
        for branch in site_branches:
            # TODO: aggregate number of graduates for each branch and filter out branches without graduates instead
            if today.year < branch.established + 2:
                # 2 year program is the minimum period for graduation
                continue
            row = {"label": str(branch.name), "value": branch.code}
            branch_options.append(row)
        # Area state and props
        areas = [{"label": a.name, "value": a.pk} for a in
                 AcademicDiscipline.objects.filter(code__in=['cs', 'se', 'ds'])]
        area = self.kwargs.get("area", None)
        area_option = next((a for a in areas if a['value'] == area), None)
        app_data = {
            "state": {
                "year": year_option,
                "area": area_option,
                "branch": self.kwargs.get("branch", None),
            },
            "props": {
                "endpoint": reverse("public-api:v2:alumni"),
                "branchOptions": branch_options,
                "areaOptions": areas,
                "yearOptions": years
            }
        }
        return {"app_data": app_data}


class OnCampusProgramsView(generic.TemplateView):
    template_name = "compscicenter_ru/syllabus/syllabus.html"


class OnCampusProgramDetailView(PublicURLMixin, generic.TemplateView):
    def get_template_names(self):
        return f"compscicenter_ru/syllabus/{self.kwargs['discipline_code']}.html"

    def get_context_data(self, discipline_code, **kwargs):
        selected_branch = self.request.GET.get('branch', settings.DEFAULT_BRANCH_CODE)
        study_program = (StudyProgram.objects
                         .filter(academic_discipline__code=discipline_code,
                                 branch__code=selected_branch,
                                 branch__site=self.request.site,
                                 branch__active=True,
                                 is_active=True)
                         .exclude(branch__city=None)
                         .first())
        if not study_program:
            raise Http404
        # Randomize testimonials
        cache_key = f"{TESTIMONIALS_CACHE_KEY}_{discipline_code}"
        random_testimonials = get_random_testimonials(4, cache_key, academic_disciplines__code=discipline_code)
        context = {
            "study_program": study_program,
            "selected_branch": selected_branch,
            "testimonials": random_testimonials,
        }
        return context


class DistanceProgramView(generic.TemplateView):
    """Distance branch 2019 view."""
    template_name = "compscicenter_ru/syllabus/distance.html"


class CourseVideoTypes(DjangoChoices):
    COURSE = C('course', _('Course'))
    LECTURE = C('lecture', _('Lecture'))


class CourseVideoListView(TemplateView):
    template_name = "compscicenter_ru/courses_video_list.html"

    def get_context_data(self, **kwargs):
        video_types = [{"value": v, "label": str(l)} for v, l
                       in CourseVideoTypes.choices]
        filtered_types = self.request.GET.get('types', None)
        if filtered_types is not None:
            filtered_types = [t for t in filtered_types.split(',')
                              if t in CourseVideoTypes.values]
        else:
            filtered_types = [item["value"] for item in video_types]
        app_data = {
            "props": {
                "endpoints": [
                    reverse("public-api:v2:course_videos"),
                    reverse("public-api:v2:recorded_events_videos"),
                ],
                "videoOptions": video_types
            },
            "state": {
                "videoTypes": filtered_types
            },
        }
        return {"app_data": app_data}


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
                               url=course_public_url(obj.course),
                               grade=obj.get_grade_display())
    else:
        raise TypeError("timeline_element_factory: Unsupported object")


class GraduateProfileView(generic.DetailView):
    slug_field = 'student_profile__id'
    slug_url_kwarg = "student_profile_id"
    template_name = "compscicenter_ru/profiles/graduate.html"

    def get_queryset(self):
        return (GraduateProfile.active
                .filter(student_profile__branch__site=self.request.site)
                .select_related("student_profile"))

    def get_context_data(self, **kwargs):
        graduate_profile = self.object
        student_profile = graduate_profile.student_profile
        timeline_elements = []
        # TODO: move to timeline queryset
        enrollments = (Enrollment.active
                       .filter(student_id=student_profile.user_id,
                               grade__in=GradeTypes.satisfactory_grades)
                       .select_related('course',
                                       'course__semester',
                                       'course__main_branch',
                                       'course__meta_course')
                       .order_by("course__semester__index",
                                 "course__meta_course__name"))
        for e in enrollments:
            timeline_elements.append(timeline_element_factory(e))
        shad_courses = (SHADCourseRecord.objects
                        .filter(student_id=student_profile.user_id,
                                grade__in=SHADCourseGradeTypes.satisfactory_grades)
                        .select_related("semester")
                        .order_by("semester__index", "name"))
        for c in shad_courses:
            timeline_elements.append(timeline_element_factory(c))
        projects = (ProjectStudent.objects
                    .filter(student_id=student_profile.user_id,
                            final_grade__in=ProjectGradeTypes.satisfactory_grades)
                    .select_related('project', 'project__semester')
                    .order_by('project__semester__index'))
        for c in projects:
            timeline_elements.append(timeline_element_factory(c))
        timeline_elements.sort(key=lambda o: (o.term.index, o.type.value))
        timeline = bucketize(timeline_elements, key=lambda o: o.term)
        context = {
            "graduate_profile": graduate_profile,
            "student_profile": student_profile,
            "timeline": timeline,
            "timeline_element_types": TimelineElementTypes
        }
        return context


class MetaCourseDetailView(PublicURLMixin, generic.DetailView):
    model = MetaCourse
    slug_url_kwarg = 'course_slug'
    template_name = "compscicenter_ru/courses/meta_course_detail.html"
    context_object_name = 'meta_course'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        branches = Branch.objects.for_site(site_id=self.request.site.pk)
        lecturers = Prefetch('course_teachers', queryset=get_lecturers())
        courses = (Course.objects
                   .filter(meta_course=self.object)
                   .made_by(branches)
                   .select_related("meta_course", "semester", "main_branch")
                   .prefetch_related(lecturers)
                   .order_by('-semester__index'))
        # Don't divide center and club courses from the same city
        courses_by_branch = bucketize(
            courses,
            key=lambda c: (c.main_branch.code, c.main_branch.name))
        # Aggregate tabs
        tabs = TabList()
        for (code, name), values in courses_by_branch.items():
            if values:
                tabs.add(Tab(target=code, name=name))
        if tabs:
            selected_tab = self.request.GET.get('branch', Branches.SPB)
            tabs.set_active(selected_tab)  # deactivates all other tabs
            if selected_tab not in tabs:
                first_tab = next(iter(tabs))
                first_tab.active = True
            tabs.sort()
        context['tabs'] = tabs
        context['grouped_courses'] = courses_by_branch
        active_study_programs = get_study_programs(
            self.object.pk,
            filters=[
                Q(is_active=True),
                Q(branch__site=self.request.site, branch__active=True)
            ])
        context['study_programs'] = active_study_programs
        return context


class TeacherDetailView(PublicURLMixin, DetailView):
    template_name = "compscicenter_ru/teacher_detail.html"
    context_object_name = 'teacher'

    def get_queryset(self, *args, **kwargs):
        return User.objects.has_role(Roles.TEACHER)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        site_branches = Branch.objects.for_site(site_id=self.request.site.pk)
        min_established = min(b.established for b in site_branches)
        site_branches_p = Prefetch(
            'branches',
            queryset=(Branch.objects
                      .filter(site_id=self.request.site.pk)
                      .order_by('order')))
        any_hidden_role = CourseTeacher.has_any_hidden_role(lookup='course_teachers__roles')
        courses = (Course.objects
                   .made_by(site_branches)
                   .filter(~any_hidden_role,
                           semester__year__gte=min_established,
                           teachers=self.object.pk)
                   .select_related('semester', 'meta_course', 'main_branch')
                   .order_by('-semester__index')
                   .prefetch_related(site_branches_p))
        context['courses'] = courses
        return context


class CourseOfferingsView(TemplateView):
    template_name = "compscicenter_ru/courses/course_list.html"

    def get_context_data(self, **kwargs):
        term_pair = get_current_term_pair()
        # TODO: use Branch.objects.for_site()
        branches = list(Branch.objects
                        .filter(site_id=settings.SITE_ID,
                                established__lte=term_pair.academic_year)
                        .annotate(value=F('code'), label=F('name'))
                        .order_by('order')
                        .values('value', 'label', 'established'))
        terms = [
            {'value': SemesterTypes.AUTUMN, 'label': str(_('Autumn|adjective'))},
            {'value': SemesterTypes.SPRING, 'label': str(_('Spring|adjective'))}
        ]

        filtered_terms = self.request.GET.get('terms', None)
        if filtered_terms is not None:
            filtered_terms = [t for t in filtered_terms.split(',')
                              if t in SemesterTypes.values]
        else:
            filtered_terms = [item["value"] for item in terms]
        # Get state based on URL params
        branch_query = self.request.GET.get("branch", branches[0]['value'])
        branch = next((b for b in branches if b['value'] == branch_query), None)
        if not branch:
            raise Http404
        try:
            year = int(self.request.GET.get("academic_year",
                                            term_pair.academic_year))
            established = branch['established'] - 1
            if year > term_pair.academic_year or year < established:
                raise ValueError("Invalid academic year")
        except ValueError:
            raise Http404
        app_data = {
            'props': {
                'endpoints': [reverse('public-api:v2:course_list')],
                'currentYear': term_pair.academic_year,
                'branchOptions': branches,
                'semesterOptions': terms
            },
            'state': {
                'branch': branch,
                'academicYear': {"value": year, "label": f"{year}/{year + 1}"},
                'terms': filtered_terms
            },
        }
        return {"app_data": app_data}


class CourseDetailView(PublicURLMixin, CoursePublicURLParamsMixin,
                       generic.DetailView):
    template_name = "compscicenter_ru/courses/course_detail.html"
    context_object_name = 'course'

    def get_course_queryset(self):
        course_teachers = course_teachers_prefetch_queryset()
        return (super().get_course_queryset()
                .select_related('meta_course', 'semester', 'main_branch')
                .prefetch_related(
                    Prefetch('course_teachers', queryset=course_teachers)
                ))

    def get_object(self, queryset=None):
        return self.course

    def get_context_data(self, **kwargs):
        tabs = TabList([
            Tab(target='about',
                name=_('About the Course'),
                url=course_public_url(self.course),
                active=True),
            Tab(target='classes',
                name=_('Syllabus'),
                url=course_public_url(self.course, tab='classes')),
        ])
        show_tab = self.kwargs.get('tab', 'about')
        tabs.set_active(show_tab)
        teachers = group_teachers(self.course.course_teachers.all())
        role_captions = {
            TeacherRoles.LECTURER: _("Reads lectures"),
            TeacherRoles.REVIEWER: _("Checks assignments"),
            TeacherRoles.SEMINAR: _("Leads seminars"),
        }
        # Update role names with narrative if possible
        teachers = {
            role_captions.get(k, TeacherRoles.values[k]): v for k, v in
            teachers.items()
        }
        role = course_access_role(course=self.course, user=self.request.user)
        classes = (CourseService.get_classes(self.course)
                   .annotate(attachments_count=Count('courseclassattachment'))
                   .select_related(None))
        context = {
            'view': self,
            'course': self.course,
            'tabs': tabs,
            'teachers': teachers,
            # FIXME: check permission instead
            'has_access_to_private_materials': can_view_private_materials(role),
            'classes': classes,
        }
        return context


class CourseClassDetailView(PublicURLMixin, generic.DetailView):
    model = CourseClass
    context_object_name = 'course_class'
    template_name = "compscicenter_ru/courses/class_detail.html"

    def get_queryset(self):
        url_params = self.kwargs
        main_branch_code = url_params.get("main_branch_code", None)
        main_branch_code = main_branch_code or settings.DEFAULT_BRANCH_CODE
        return (CourseClass.objects
                .filter(course__main_branch__site=self.request.site,
                        course__main_branch__active=True,
                        course__main_branch__code=main_branch_code,
                        course__meta_course__slug=url_params['course_slug'],
                        course__semester__type=url_params['semester_type'],
                        course__semester__year=url_params['semester_year'])
                .select_related("course",
                                "course__meta_course",
                                "course__semester",
                                "course__main_branch",
                                "venue",
                                "venue__location"))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        course_class = context[self.context_object_name]
        can_view_materials = self.request.user.has_perm(
            ViewCourseClassMaterials.name, course_class)
        recorded = (CourseClass.objects
                    .filter(course=course_class.course)
                    .exclude(video_url='')
                    .only('pk', 'name', 'video_url', 'course_id', 'date',
                          # FIXME: bug with a tracked field
                          'slides',
                          'starts_at', 'ends_at')
                    .order_by("date", "starts_at"))
        if not can_view_materials:
            recorded = recorded.with_public_materials()
        for lecture in recorded:
            lecture.course = course_class.course
        context['can_view_course_class_materials'] = can_view_materials
        context['recorded_classes'] = recorded
        context['attachments'] = course_class.courseclassattachment_set.order_by('created')
        return context
