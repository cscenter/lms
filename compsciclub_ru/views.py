import datetime
from functools import partial

import pytz
from django_ical.views import ICalFeed
from registration import signals
from registration.backends.default.views import RegistrationView
from vanilla import DetailView

from django.contrib.auth.views import redirect_to_login
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import caches
from django.db import transaction
from django.db.models import Prefetch, Q
from django.utils import timezone
from django.utils.timezone import now
from django.views import generic

import core.utils
from auth.tasks import ActivationEmailContext, send_activation_email
from compscicenter_ru.utils import course_class_public_url, course_public_url
from compsciclub_ru.forms import RegistrationUniqueEmailAndUsernameForm
from core.exceptions import Redirect
from core.models import Branch
from core.urls import reverse
from courses.calendar import CalendarEventFactory
from courses.constants import SemesterTypes, TeacherRoles
from courses.models import Course, CourseClass, CourseTeacher, MetaCourse, Semester
from courses.selectors import course_teachers_prefetch_queryset
from courses.services import group_teachers
from courses.tabs import CourseInfoTab, TabNotFound, get_course_tab_list
from courses.utils import MonthPeriod, extended_month_date_range, get_current_term_pair
from courses.views.calendar import MonthEventsCalendarView
from courses.views.mixins import CoursePublicURLParamsMixin
from learning.gallery.models import Image
from learning.services import get_classes
from users.constants import Roles
from users.models import StudentTypes, User
from users.services import (
    create_account, create_registration_profile, create_student_profile
)

_TIME_ZONE = pytz.timezone('Europe/Moscow')


class PublicURLContextMixin:
    def get_public_urls(self):
        code = self.request.branch.code
        return {
            'course_public_url': partial(course_public_url,
                                         default_branch_code=code),
            'course_class_public_url': partial(course_class_public_url,
                                               default_branch_code=code)
        }


class AsyncEmailRegistrationView(RegistrationView):
    """Send activation email using redis queue"""
    form_class = RegistrationUniqueEmailAndUsernameForm

    def register(self, form) -> User:
        site = get_current_site(self.request)
        data = form.cleaned_data
        branch = self.request.branch
        with transaction.atomic():
            new_user = create_account(
                username=data['username'],
                password=data['password1'],
                email=data['email'],
                gender=data['gender'],
                time_zone=branch.time_zone,
                is_active=False,
                branch=branch)
            registration_profile = create_registration_profile(user=new_user)
            create_student_profile(user=new_user,
                                   branch=new_user.branch,
                                   profile_type=StudentTypes.REGULAR,
                                   year_of_admission=new_user.date_joined.year,
                                   year_of_curriculum=new_user.date_joined.year)
        signals.user_registered.send(sender=self.__class__,
                                     user=new_user,
                                     request=self.request)
        activation_url = reverse("registration_activate", kwargs={
            "activation_key": registration_profile.activation_key
        })
        context = ActivationEmailContext(
            site_name=site.name,
            activation_url=self.request.build_absolute_uri(activation_url),
            language_code=self.request.LANGUAGE_CODE)
        send_activation_email.delay(context, registration_profile.pk)
        return new_user


class CalendarClubScheduleView(MonthEventsCalendarView):
    """Shows course classes in the time zone of the requested branch"""
    calendar_type = "public_full"
    template_name = "lms/courses/calendar.html"

    def get_events(self, month_period: MonthPeriod, **kwargs):
        start, end = extended_month_date_range(month_period, expand=1)
        fs = [Q(date__range=[start, end]),
              ~Q(course__semester__type=SemesterTypes.SUMMER)]
        public_url_builder = partial(course_class_public_url,
                                     default_branch_code=self.request.branch.code)
        for c in get_classes(branch_list=[self.request.branch], filters=fs):
            yield CalendarEventFactory.create(c,
                                              url_builder=public_url_builder,
                                              time_zone=self.request.branch.get_timezone())


class IndexView(PublicURLContextMixin, generic.TemplateView):
    template_name = "compsciclub_ru/index.html"

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        try:
            # All club courses in MSK timezone
            current_term = get_current_term_pair()
            term_type = current_term.type
            if current_term.type == SemesterTypes.SUMMER:
                term_type = SemesterTypes.AUTUMN
            featured_term = Semester.objects.get(year=current_term.year,
                                                 type=term_type)
            context['featured_term'] = featured_term
            today = now().date()
            # TODO: add cache, limit classes returned values by 1
            courseclass_queryset = (CourseClass.objects
                                    .filter(date__gte=today)
                                    .order_by('date', 'starts_at'))
            site_branches = Branch.objects.for_site(self.request.site)
            courses = list(
                Course.objects
                .filter(semester=featured_term.pk)
                .available_in(self.request.branch)
                .made_by(site_branches)
                .select_related('meta_course', 'semester', 'main_branch')
                .prefetch_related(
                    Prefetch('course_teachers',
                             queryset=course_teachers_prefetch_queryset(role_priority=False)),
                    Prefetch(
                        'courseclass_set',
                        queryset=courseclass_queryset,
                        to_attr='classes'
                    ))
                .order_by('completed_at', 'meta_course__name'))
            # Sort courses by nearest class
            courses.sort(key=self.cmp_courses_by_nearest_class)
            context['courses'] = courses
        except Semester.DoesNotExist:
            pass
        context.update(self.get_public_urls())
        return context

    @staticmethod
    def cmp_courses_by_nearest_class(course):
        if not course.classes:
            nearest = datetime.date(year=now().year + 1, month=1, day=1)
        else:
            nearest = course.classes[0].date
        return course.is_completed, nearest


class TeachersView(generic.ListView):
    template_name = "compsciclub_ru/teacher_list.html"

    @property
    def get_queryset(self):
        lecturers = list(Course.objects
                         .filter(main_branch=self.request.branch)
                         .distinct()
                         .values_list("teachers__pk", flat=True))
        return (User.objects
                .has_role(Roles.TEACHER)
                .filter(courseteacher__teacher_id__in=lecturers)
                .distinct)


class TeacherDetailView(PublicURLContextMixin, DetailView):
    template_name = "compsciclub_ru/teacher_detail.html"
    context_object_name = 'teacher'

    def get_queryset(self, *args, **kwargs):
        images_qs = Image.objects.select_related("course", "course__semester")
        return (User.objects
                .has_role(Roles.TEACHER)
                .prefetch_related(Prefetch('images', queryset=images_qs)))

    def get_context_data(self, **kwargs):
        branches = Branch.objects.for_site(site_id=self.request.site.pk)
        min_established = min(b.established for b in branches)
        any_hidden_role = CourseTeacher.has_any_hidden_role(lookup='course_teachers__roles')
        courses = (Course.objects
                   .made_by(branches)
                   .available_in(self.request.branch)
                   .filter(~any_hidden_role,
                           semester__year__gte=min_established,
                           teachers=self.object.pk)
                   .select_related('semester', 'meta_course', 'main_branch')
                   .order_by('-semester__index'))
        context = {
            'teacher': self.object,
            'courses': courses,
            **self.get_public_urls()
        }
        return context


class ClubClassesFeed(ICalFeed):
    title = "Занятия CS клуба"
    description = """Календарь занятий."""
    product_id = "-//compsciclub.ru//Computer Science Club//"
    timezone = 'Europe/Moscow'
    file_name = "classes.ics"

    def __call__(self, request, *args, **kwargs):
        cache_key = self.get_cache_key(*args, **kwargs)
        response = caches['default'].get(cache_key)
        if response is None:
            response = super().__call__(request, *args, **kwargs)
            caches['default'].set(cache_key, response, 60 * 60)
        return response

    def get_cache_key(self, *args, **kwargs):
        return "%s-%s" % (self.__class__.__name__.lower(),
                          '/'.join("%s,%s" % (key, val) for key, val in
                                   kwargs.items()))

    def get_object(self, request, *args, **kwargs):
        # Expect request as the second parameter on method items
        return request

    def items(self, request):
        return (CourseClass.objects
                .in_branches(request.branch.pk)
                .select_related('venue',
                                'venue__location',
                                'course',
                                'course__main_branch',
                                'course__semester',
                                'course__meta_course'))

    def item_guid(self, item):
        return "courseclasses-{}@compsciclub.ru".format(item.pk)

    def item_title(self, item):
        return item.name

    def item_description(self, item):
        if item.description.strip():
            return "{} ({})".format(item.description, self.item_link(item))
        else:
            return item.get_type_display()

    def item_link(self, item):
        return item.get_absolute_url()

    def item_start_datetime(self, item: CourseClass):
        tz = _TIME_ZONE
        return item.starts_at_local(tz)

    def item_end_datetime(self, item: CourseClass):
        tz = _TIME_ZONE
        return item.ends_at_local(tz)

    def item_created(self, item):
        return item.created

    def item_updateddate(self, item):
        return item.modified

    def item_location(self, item):
        return item.venue.address


class CoursesListView(PublicURLContextMixin, generic.ListView):
    model = Semester
    template_name = "compsciclub_ru/course_offerings.html"

    def get_queryset(self):
        course_teachers = Prefetch('course_teachers',
                                   queryset=course_teachers_prefetch_queryset(role_priority=False))
        courses_qs = (Course.objects
                      .available_in(self.request.branch)
                      .select_related('meta_course', 'main_branch')
                      .prefetch_related(course_teachers)
                      .order_by('meta_course__name'))
        courses_set = Prefetch('course_set',
                               queryset=courses_qs,
                               to_attr='courseofferings')
        return (Semester.objects
                .prefetch_related(courses_set))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        semester_list = [s for s in context["semester_list"]
                         if s.type != SemesterTypes.SUMMER]
        if not semester_list:
            context["semester_list"] = semester_list
            return context
        # Check if we only have the fall semester for the ongoing year.
        current = semester_list[0]
        if current.type == SemesterTypes.AUTUMN:
            semester = Semester(type=SemesterTypes.SPRING,
                                year=current.year + 1)
            semester.courseofferings = []
            semester_list.insert(0, semester)
        # Hide empty pairs
        context["semester_list"] = [
            (a, s) for s, a in core.utils.chunks(semester_list, 2) if \
            (a and a.courseofferings) or (s and s.courseofferings)
            ]

        context.update(self.get_public_urls())

        return context


class MetaCourseDetailView(PublicURLContextMixin, generic.DetailView):
    model = MetaCourse
    slug_url_kwarg = 'course_slug'
    template_name = "compsciclub_ru/meta_course_detail.html"

    def get_context_data(self, **kwargs):
        courses = (Course.objects
                   .filter(meta_course=self.object)
                   .available_in(self.request.branch)
                   .select_related("meta_course", "semester", "main_branch")
                   .order_by('-semester__index'))
        context = {
            'meta_course': self.object,
            'courses': courses,
            **self.get_public_urls()
        }
        return context


class CourseDetailView(PublicURLContextMixin,
                       CoursePublicURLParamsMixin, generic.DetailView):
    template_name = "compsciclub_ru/course_detail.html"
    context_object_name = 'course'

    def get_course_queryset(self):
        return (super().get_course_queryset()
                .prefetch_related(
                    Prefetch('course_teachers',
                             queryset=course_teachers_prefetch_queryset(role_priority=False)),
                    "branches"))

    def get_object(self):
        return self.course

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            raise Redirect(self.course.get_absolute_url())
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        course = self.course
        # Tabs
        tab_list = get_course_tab_list(self.request, course,
                                       codes=['about', 'classes', 'news'])
        try:
            show_tab = self.kwargs.get('tab', CourseInfoTab.type)
            tab_list.set_active_tab(show_tab)
        except TabNotFound:
            raise Redirect(to=redirect_to_login(self.request.get_full_path()))
        # Teachers
        by_role = group_teachers(course.course_teachers.all())
        teachers = {'main': [], 'others': []}
        for role, ts in by_role.items():
            if role in (TeacherRoles.LECTURER, TeacherRoles.SEMINAR):
                group = 'main'
            else:
                group = 'others'
            teachers[group].extend(ts)
        tz_override = None
        if self.request.user.is_authenticated:
            tz_override = self.request.user.time_zone
        context = {
            'course': course,
            'course_tabs': tab_list,
            'teachers': teachers,
            'tz_override': tz_override,
            **self.get_public_urls()
        }
        return context


class CourseClassDetailView(PublicURLContextMixin,
                            CoursePublicURLParamsMixin, generic.DetailView):
    template_name = "compsciclub_ru/course_class_detail.html"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.request.user.is_authenticated:
            raise Redirect(self.object.get_absolute_url())
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_queryset(self):
        url_params = self.kwargs
        main_branch_code = url_params.get("main_branch_code", None)
        main_branch_code = main_branch_code or self.request.branch.code
        return (CourseClass.objects
                .filter(course__main_branch__site=self.request.site,
                        course__main_branch__active=True,
                        course__main_branch__code=main_branch_code,
                        course__meta_course__slug=url_params['course_slug'],
                        course__semester__type=url_params['semester_type'],
                        course__semester__year=url_params['semester_year'])
                .select_related("course",
                                "course__meta_course",
                                "course__main_branch",
                                "course__semester",
                                "venue",
                                "venue__location",))

    def get_context_data(self, **kwargs):
        context = {
            'course_class': self.object,
            'attachments': self.object.courseclassattachment_set.all(),
            **self.get_public_urls(),
        }
        return context
