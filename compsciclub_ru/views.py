import datetime

import pytz
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import caches
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import Http404
from django.utils import timezone
from django.utils.timezone import now
from django.views import generic
from django_ical.views import ICalFeed
from registration import signals
from registration.backends.default.views import RegistrationView
from vanilla import DetailView

import core.utils
from auth.tasks import send_activation_email, ActivationEmailContext
from core.urls import reverse
from courses.calendar import CalendarEvent
from courses.constants import SemesterTypes
from courses.models import Course, Semester, CourseClass
from courses.utils import get_current_term_pair, MonthPeriod, \
    extended_month_date_range
from courses.views.calendar import MonthEventsCalendarView
from learning.gallery.models import Image
from learning.services import get_classes
from users.constants import Roles
from users.models import User, StudentProfile, StudentTypes

_TIME_ZONE = pytz.timezone('Europe/Moscow')


class AsyncEmailRegistrationView(RegistrationView):
    """Send activation email using redis queue"""
    def register(self, form):
        site = get_current_site(self.request)
        new_user = form.save(commit=False)
        new_user.branch = self.request.branch
        new_user.is_active = False
        # Since we calculate the RegistrationProfile expiration from this date,
        # we want to ensure that it is current
        new_user.date_joined = timezone.now()

        with transaction.atomic():
            new_user.save()
            student_profile = StudentProfile(
                user=new_user,
                type=StudentTypes.REGULAR,
                branch=new_user.branch,
                year_of_admission=new_user.date_joined.year)
            student_profile.save()
            self.registration_profile.objects.create_profile(new_user)

        signals.user_registered.send(sender=self.__class__,
                                     user=new_user,
                                     request=self.request)
        activation_url = reverse("registration_activate", kwargs={
            "activation_key": new_user.registrationprofile.activation_key
        })
        context = ActivationEmailContext(
            site_name=site.name,
            activation_url=self.request.build_absolute_uri(activation_url),
            language_code=self.request.LANGUAGE_CODE)
        send_activation_email.delay(context, new_user.registrationprofile.pk)
        return new_user


class CalendarClubScheduleView(MonthEventsCalendarView):
    """Shows classes from public courses."""
    calendar_type = "public_full"
    template_name = "learning/calendar.html"

    def get_events(self, month_period: MonthPeriod, **kwargs):
        start, end = extended_month_date_range(month_period)
        fs = [Q(date__range=[start, end]),
              ~Q(course__semester__type=SemesterTypes.SUMMER)]
        for c in get_classes(branch_list=[self.request.branch], filters=fs):
            yield CalendarEvent(c)


class IndexView(generic.TemplateView):
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
            courses = list(
                Course.objects
                .available_in(self.request.branch)
                .filter(semester=featured_term.pk)
                .select_related('meta_course', 'semester', 'main_branch')
                .prefetch_related(
                    'teachers',
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
        return context

    @staticmethod
    def cmp_courses_by_nearest_class(course):
        if not course.classes:
            nearest = datetime.date(year=now().year + 1, month=1, day=1)
        else:
            nearest = course.classes[0].date
        return course.is_completed, nearest


class TeachersView(generic.ListView):
    template_name = "compsciclub_ru/users/teacher_list.html"

    @property
    def get_queryset(self):
        lecturers = list(Course.objects
                         .filter(is_open=True,
                                 main_branch=self.request.branch, )
                         .distinct()
                         .values_list("teachers__pk", flat=True))
        return (User.objects
                .has_role(Roles.TEACHER)
                .filter(courseteacher__teacher_id__in=lecturers)
                .distinct)


class TeacherDetailView(DetailView):
    template_name = "compsciclub_ru/users/teacher_detail.html"
    context_object_name = 'teacher'

    def get_queryset(self):
        co_queryset = (Course.objects
                       .filter(is_open=True,
                               main_branch=self.request.branch, )
                       .select_related('semester', 'meta_course',
                                       'main_branch'))
        return (get_user_model()._default_manager
                .prefetch_related(
                    Prefetch('teaching_set',
                             queryset=co_queryset.all(),
                             to_attr='course_offerings'),
                    Prefetch('images',
                             queryset=Image.objects.select_related(
                                 "course",
                                 "course__semester"))
                    ))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = context[self.context_object_name]
        if not teacher.is_teacher:
            raise Http404
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

    def item_start_datetime(self, item):
        tz = _TIME_ZONE
        return tz.localize(datetime.datetime.combine(item.date, item.starts_at))

    def item_end_datetime(self, item):
        tz = _TIME_ZONE
        return tz.localize(datetime.datetime.combine(item.date, item.ends_at))

    def item_created(self, item):
        return item.created

    def item_updateddate(self, item):
        return item.modified

    def item_location(self, item):
        return item.venue.address


class CoursesListView(generic.ListView):
    model = Semester
    template_name = "compsciclub_ru/course_offerings.html"

    def get_queryset(self):
        courses_qs = (Course.objects
                      .available_in(self.request.branch)
                      .select_related('meta_course', 'main_branch')
                      .prefetch_related('teachers')
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

        return context
