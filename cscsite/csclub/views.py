import datetime

import django_rq
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import caches
from django.db.models import Prefetch, Q
from django.http import JsonResponse, Http404, HttpResponseRedirect
from django.utils.timezone import now, get_current_timezone
from django.views import generic
# TODO: (XXX) Dont' forget to remove it after old.* termination.
from django.views.decorators.csrf import requires_csrf_token
from django.shortcuts import redirect
from django_ical.views import ICalFeed
from registration.backends.default.views import RegistrationView
from vanilla import DetailView

from csclub import tasks
from learning.gallery.models import Image
from learning.models import CourseOffering, Semester, \
    CourseClass
from learning.settings import SEMESTER_TYPES, FOUNDATION_YEAR
from learning.utils import get_current_term_pair, now_local
from learning.views.generic import CalendarGenericView


class AsyncEmailRegistrationView(RegistrationView):
    """Send activation email with queue"""
    SEND_ACTIVATION_EMAIL = False  # Prevent sending email on request

    def register(self, form):
        new_user = super(AsyncEmailRegistrationView, self).register(form)
        queue = django_rq.get_queue('club')
        site = get_current_site(self.request)
        queue.enqueue(tasks.send_activation_email,
                      site.pk,
                      new_user.registrationprofile.pk,
                      self.request.LANGUAGE_CODE)
        return new_user


class CalendarClubScheduleView(CalendarGenericView):
    """Shows all classes from open course offerings."""
    calendar_type = "public_full"
    template_name = "learning/calendar.html"

    def get_events(self, year, month, **kwargs):
        classes = (CourseClass.objects
                   .for_calendar(self.request.user)
                   .in_month(year, month)
                   .for_city(self.request.city_code)
                   .open_only())
        return [classes]

    def get_user_city(self):
        return self.request.city_code


class IndexView(generic.TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        try:
            # All club courses in MSK timezone
            year, term_type = get_current_term_pair('spb')
            if term_type == SEMESTER_TYPES.summer:
                term_type = SEMESTER_TYPES.autumn
            featured_term = Semester.objects.get(year=year, type=term_type)
            context['featured_term'] = featured_term
            today = now().date()
            # TODO: add cache, limit classes returned values by 1
            courseclass_queryset = (CourseClass.objects
                                               .filter(date__gte=today)
                                               .order_by('date', 'starts_at'))
            courses = list(
                CourseOffering.objects
                .in_city(self.request.city_code)
                .filter(is_open=True, semester=featured_term.pk)
                .select_related('course', 'semester')
                .prefetch_related(
                    'teachers',
                    Prefetch(
                        'courseclass_set',
                        queryset=courseclass_queryset,
                        to_attr='classes'
                    ))
                .order_by('completed_at', 'course__name'))
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
    template_name = "users/teacher_list.html"

    @property
    def get_queryset(self):
        user_model = get_user_model()
        lecturers = list(CourseOffering
            .objects
            .filter(is_open=True,
                    city__pk=self.request.city_code)
            .distinct()
            .values_list("teachers__pk", flat=True))
        return (user_model.objects
                .filter(groups=user_model.group.TEACHER_CLUB,
                        courseofferingteacher__teacher_id__in=lecturers)
                .distinct)


class TeacherDetailView(DetailView):
    template_name = "users/teacher_club_detail.html"
    context_object_name = 'teacher'

    def get_queryset(self):
        co_queryset = (CourseOffering.objects
                       .in_city(self.request.city_code)
                       .filter(is_open=True)
                       .select_related('semester', 'course'))
        return (get_user_model()._default_manager
                .prefetch_related(
                    Prefetch('teaching_set',
                             queryset=co_queryset.all(),
                             to_attr='course_offerings'),
                    Prefetch('images',
                             queryset=Image.objects.select_related(
                                 "course_offering",
                                 "course_offering__semester"))
                    ))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = context[self.context_object_name]
        if not teacher.is_teacher:
            raise Http404
        return context


@requires_csrf_token
def custom_page_not_found(request, exception, template_name='404.html'):
    return redirect('http://old.compsciclub.ru' + request.path)


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

    def items(self):
        return (CourseClass.objects
                .filter(course_offering__is_open=True,
                        course_offering__city__code="spb")
                .select_related('venue',
                                'course_offering',
                                'course_offering__semester',
                                'course_offering__course'))

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
        tz = get_current_timezone()
        return tz.localize(datetime.datetime.combine(item.date, item.starts_at))

    def item_end_datetime(self, item):
        tz = get_current_timezone()
        return tz.localize(datetime.datetime.combine(item.date, item.ends_at))

    def item_created(self, item):
        return item.created

    def item_updateddate(self, item):
        return item.modified

    def item_location(self, item):
        return item.venue.address
