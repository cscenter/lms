from collections import Counter

import datetime

import django_rq
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Prefetch, Q
from django.http import JsonResponse, Http404
from django.utils.timezone import now
from django.views import generic
# TODO: (XXX) Dont' forget to remove it after old.* termination.
from django.views.decorators.csrf import requires_csrf_token
from django.shortcuts import redirect
from registration.backends.default.views import RegistrationView

from csclub import tasks
from learning.gallery.models import Image
from learning.models import CourseOffering, Semester, \
    CourseClass
from learning.settings import SEMESTER_TYPES
from learning.utils import get_current_semester_pair
from learning.views import CalendarMixin


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


class CalendarClubScheduleView(CalendarMixin, generic.ListView):
    user_type = 'public_full'

    def get_queryset(self):
        qs = super(CalendarClubScheduleView, self).get_queryset()
        # Additionally check that we have classes in this month
        # Note: assume we never show up non-class events on club schedule
        return qs


class IndexView(generic.TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        try:
            year, term_type = get_current_semester_pair()
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
                CourseOffering
                .custom
                .site_related(self.request)
                .filter(semester=featured_term.pk)
                .select_related('course', 'semester')
                .prefetch_related(
                    'teachers',
                    Prefetch(
                        'courseclass_set',
                        queryset=courseclass_queryset,
                        to_attr='classes'
                    ))
                .order_by('is_completed', 'course__name'))
            # Sort courses by nearest class
            courses.sort(key=self.cmp_courses_by_nearest_class)
            context['courses'] = courses
        except Semester.DoesNotExist:
            pass
        return context

    @staticmethod
    def cmp_courses_by_nearest_class(course):
        if not course.classes:
            return datetime.date(year=now().year + 1, month=1, day=1)
        return course.classes[0].date


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


class TeacherDetailView(generic.DetailView):
    template_name = "users/teacher_club_detail.html"
    context_object_name = 'teacher'

    def get_queryset(self, *args, **kwargs):
        co_queryset = (CourseOffering.custom.site_related(self.request)
                       .select_related('semester', 'course'))
        return (get_user_model()._default_manager
                .all()
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
        context = super(TeacherDetailView, self).get_context_data(**kwargs)
        teacher = context[self.context_object_name]
        if not teacher.is_teacher:
            raise Http404
        return context


@requires_csrf_token
def custom_page_not_found(request, exception, template_name='404.html'):
    return redirect('http://old.compsciclub.ru' + request.path)
