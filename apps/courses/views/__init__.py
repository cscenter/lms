from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.db.models import Prefetch
from django.http import HttpResponseBadRequest, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse, NoReverseMatch
from django.views import generic
from vanilla import DetailView

from core.exceptions import Redirect
from core.settings.base import CENTER_FOUNDATION_YEAR
from core.utils import get_club_domain
from core.views import ProtectedFormMixin
from courses.forms import CourseEditDescrForm
from courses.models import Course, CourseTeacher
from courses.settings import SemesterTypes
from courses.tabs import CourseInfoTab, get_course_tab_list, TabNotFound
from courses.utils import get_term_index
from learning.models import CourseNewsNotification
from users.mixins import TeacherOnlyMixin
from users.utils import get_user_city_code
from .course_class import *
from .course_news import *
from .meta_course import *
from .calendar import *


class CourseDetailView(DetailView):
    model = Course
    template_name = "courses/course_detail.html"
    context_object_name = 'course'

    def get(self, request, *args, **kwargs):
        # FIXME: separate `semester_slug` on route url lvl?
        try:
            year, _ = self.kwargs['semester_slug'].split("-", 1)
            _ = int(year)
        except ValueError:
            return HttpResponseBadRequest()
        # Redirects old style links
        if "tab" in request.GET:
            url_params = dict(self.kwargs)
            try:
                tab_name = request.GET["tab"]
                url = reverse("course_detail_with_active_tab",
                              kwargs={**url_params, "tab": tab_name})
            except NoReverseMatch:
                url = reverse("course_detail", kwargs=url_params)
            return HttpResponseRedirect(url)
        # Redirects to login page if tab is not visible to authenticated user
        context = self.get_context_data()
        # Redirects to club if course was created before center establishment.
        co = context[self.context_object_name]
        if settings.SITE_ID == settings.CENTER_SITE_ID and co.is_open:
            index = get_term_index(CENTER_FOUNDATION_YEAR,
                                   SemesterTypes.AUTUMN)
            if co.semester.index < index:
                url = get_club_domain(co.city.code) + co.get_absolute_url()
                return HttpResponseRedirect(url)
        return self.render_to_response(context)

    def get_context_data(self, *args, **kwargs):
        co = self.get_object()
        request_user = self.request.user
        teachers_by_role = co.get_grouped_teachers()
        # For correspondence course try to override timezone
        tz_override = None
        if (not co.is_actual_teacher(request_user) and co.is_correspondence
                and request_user.city_code):
            tz_override = settings.TIME_ZONES[request_user.city_id]
        # TODO: set default value if `tz_override` is None
        request_user_enrollment = request_user.get_enrollment(co.pk)
        is_actual_teacher = co.is_actual_teacher(request_user)
        # Attach unread notifications count if request user in mailing list
        # FIXME: Перенести в модель User или пусть эту инфу дёргает таба?
        unread_news = None
        if request_user_enrollment or is_actual_teacher:
            unread_news = (CourseNewsNotification.unread
                           .filter(course_offering_news__course=co,
                                   user=request_user)
                           .count())
        context = {
            'course': co,
            'user_city': get_user_city_code(self.request),
            'tz_override': tz_override,
            'teachers': teachers_by_role,
            'request_user_enrollment': request_user_enrollment,
            # TODO: move to user method
            'is_actual_teacher': is_actual_teacher,
            'unread_news': unread_news,
            'course_tabs': self.make_tabs(co)
        }
        return context

    def get_object(self):
        year, semester_type = self.kwargs['semester_slug'].split("-", 1)
        qs = (Course.objects
              .filter(semester__type=semester_type,
                      semester__year=year,
                      meta_course__slug=self.kwargs['course_slug'])
              .in_city(self.request.city_code)
              .select_related('meta_course', 'semester', 'city')
              .prefetch_related(
                    Prefetch(
                        'course_teachers',
                        queryset=(CourseTeacher.objects
                                  .select_related("teacher")))))
        return get_object_or_404(qs)

    def make_tabs(self, course: Course):
        tab_list = get_course_tab_list(self.request, course)
        try:
            show_tab = self.kwargs.get('tab', CourseInfoTab.type)
            tab_list.set_active_tab(show_tab)
        except TabNotFound:
            login_page = redirect_to_login(self.request.get_full_path())
            raise Redirect(to=login_page)
        return tab_list


class CourseEditView(TeacherOnlyMixin, ProtectedFormMixin,
                     generic.UpdateView):
    model = Course
    template_name = "courses/simple_crispy_form.html"
    form_class = CourseEditDescrForm

    def get_object(self, queryset=None):
        try:
            year, semester_type = self.kwargs['semester_slug'].split("-", 1)
            year = int(year)
        except ValueError:
            raise Http404

        if queryset is None:
            queryset = self.get_queryset()

        return get_object_or_404(
            queryset.filter(semester__type=semester_type,
                            semester__year=year,
                            meta_course__slug=self.kwargs['course_slug']))

    def get_initial(self):
        """Keep in mind that `initial` overrides values from model dict"""
        initial = super().get_initial()
        # Note: In edit view we always have an object
        if not self.object.description_ru:
            initial["description_ru"] = self.object.meta_course.description_ru
        if not self.object.description_en:
            initial["description_en"] = self.object.meta_course.description_en
        return initial

    def is_form_allowed(self, user, obj):
        return user.is_curator or user in obj.teachers.all()

    def get_queryset(self):
        return Course.objects.in_city(self.request.city_code)

