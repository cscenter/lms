import logging
from typing import List

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.db import transaction, IntegrityError
from django.db.models import Q, Prefetch, When, Value, Case, \
    IntegerField, BooleanField, Count
from django.http import HttpResponseBadRequest, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, NoReverseMatch
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.views import generic
from rest_framework.generics import ListAPIView
from vanilla import DeleteView, UpdateView, CreateView, DetailView, TemplateView

from api.permissions import CuratorAccessPermission
from core.exceptions import Redirect
from core.utils import get_club_domain, is_club_site
from core.views import ProtectedFormMixin
from learning.widgets import Tab, TabbedPane, CourseOfferingTabbedPane
from learning.forms import CourseEditDescrForm, CourseNewsForm
from learning.models import Course, CourseOfferingTeacher, \
    CourseOfferingNewsNotification, CourseClass, Assignment, StudentAssignment, \
    CourseOfferingNews
from learning.serializers import CourseOfferingNewsNotificationSerializer
from learning.settings import CENTER_FOUNDATION_YEAR, SEMESTER_TYPES, \
    STUDENT_STATUS
from learning.utils import get_term_index
from learning.viewmixins import TeacherOnlyMixin
from learning.views.utils import get_co_from_query_params, get_user_city_code
from users.models import User

__all__ = ['CourseOfferingDetailView', 'CourseOfferingEditView',
           'CourseOfferingNewsCreateView', 'CourseOfferingNewsUpdateView',
           'CourseOfferingNewsDeleteView']


logger = logging.getLogger(__name__)


class CourseOfferingDetailView(DetailView):
    model = Course
    context_object_name = 'course_offering'
    template_name = "learning/courseoffering_detail.html"
    default_tab = "about"

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
                url = reverse("course_offering_detail_with_active_tab",
                              kwargs={**url_params, "tab": tab_name})
            except NoReverseMatch:
                url = reverse("course_offering_detail", kwargs=url_params)
            return HttpResponseRedirect(url)
        # Redirects to login page if tab is not visible to authenticated user
        context = self.get_context_data()
        # Redirects to club if course was created before center establishment.
        co = context[self.context_object_name]
        if settings.SITE_ID == settings.CENTER_SITE_ID and co.is_open:
            index = get_term_index(CENTER_FOUNDATION_YEAR,
                                   SEMESTER_TYPES.autumn)
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
        unread_news = None
        if request_user_enrollment or is_actual_teacher:
            unread_news = (CourseOfferingNewsNotification.unread
                           .filter(course_offering_news__course_offering=co,
                                   user=request_user)
                           .count())
        context = {
            'course_offering': co,
            'user_city': get_user_city_code(self.request),
            'tz_override': tz_override,
            'teachers': teachers_by_role,
            'request_user_enrollment': request_user_enrollment,
            # TODO: move to user method
            'is_actual_teacher': is_actual_teacher,
            'unread_news': unread_news,
            'tabs': self.make_tabbed_pane(co)
        }
        return context

    def get_object(self):
        year, semester_type = self.kwargs['semester_slug'].split("-", 1)
        qs = (Course.objects
              .filter(semester__type=semester_type,
                      semester__year=year,
                      meta_course__slug=self.kwargs['course_slug'])
              .in_city(self.request.city_code)
              .select_related('meta_course', 'semester')
              .prefetch_related(
                    Prefetch(
                        'courseofferingteacher_set',
                        queryset=(CourseOfferingTeacher.objects
                                  .select_related("teacher")
                                  .prefetch_related("teacher__groups")))))
        return get_object_or_404(qs)

    def make_tabbed_pane(self, course_offering):
        pane = CourseOfferingTabbedPane(course_offering)
        # Tab name have to be validated by url() pattern.
        show_tab = self.kwargs.get('tab', self.default_tab)
        login_page = redirect_to_login(self.request.get_full_path())
        pane.make_tabs(self.request.user, show_tab, redirect_to=login_page)
        if show_tab not in pane:
            raise Http404
        pane.set_active_tab(pane[show_tab])
        return pane


class CourseOfferingStudentsView(TeacherOnlyMixin, TemplateView):
    # raise_exception = True
    template_name = "learning/courseoffering_students.html"

    def get(self, request, *args, **kwargs):
        try:
            year, _ = self.kwargs['semester_slug'].split("-", 1)
            _ = int(year)
        except ValueError:
            raise Http404
        return super().get(request, *args, **kwargs)

    def handle_no_permission(self, request):
        raise Http404

    def get_context_data(self, **kwargs):
        year, semester_type = self.kwargs['semester_slug'].split("-", 1)
        co = get_object_or_404(Course.objects
                               .filter(semester__type=semester_type,
                                       semester__year=year,
                                       meta_course__slug=self.kwargs['course_slug'])
                               .in_city(self.request.city_code))
        return {
            "co": co,
            "enrollments": (co.enrollment_set(manager="active")
                            .select_related("student"))
        }


# FIXME: Do I need ProtectedFormMixin?
class CourseOfferingEditView(TeacherOnlyMixin, ProtectedFormMixin,
                             generic.UpdateView):
    model = Course
    template_name = "learning/simple_crispy_form.html"
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


class CourseOfferingNewsCreateView(TeacherOnlyMixin, CreateView):
    model = CourseOfferingNews
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseNewsForm

    def get_form(self, **kwargs):
        form_class = self.get_form_class()
        co = get_co_from_query_params(self.kwargs, self.request.city_code)
        if not co:
            raise Http404('Course offering not found')
        if not self.is_form_allowed(self.request.user, co):
            raise Redirect(to=redirect_to_login(self.request.get_full_path()))
        kwargs["course_offering"] = co
        return form_class(**kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.author = self.request.user
        try:
            # Try to create news and notifications
            with transaction.atomic():
                self.object.save()
            messages.success(self.request, _("News was successfully created"),
                             extra_tags='timeout')
        except IntegrityError:
            messages.error(self.request, _("News wasn't created. Try again."))
        return redirect(self.get_success_url())

    def get_success_url(self):
        return self.object.course_offering.get_url_for_tab("news")

    def is_form_allowed(self, user, course_offering):
        return user.is_curator or user in course_offering.teachers.all()


class CourseOfferingNewsUpdateView(TeacherOnlyMixin, ProtectedFormMixin,
                                   UpdateView):
    model = CourseOfferingNews
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseNewsForm

    def get_success_url(self):
        return self.object.course_offering.get_url_for_tab("news")

    def is_form_allowed(self, user, obj):
        return user.is_curator or user in obj.course_offering.teachers.all()


class CourseOfferingNewsDeleteView(TeacherOnlyMixin, ProtectedFormMixin,
                                   DeleteView):
    model = CourseOfferingNews
    template_name = "learning/simple_delete_confirmation.html"

    def get_success_url(self):
        """
        Since we don't check was it the last deleted news or not - redirect to
        default active tab.
        """
        return self.object.course_offering.get_absolute_url()

    def is_form_allowed(self, user, obj):
        return user.is_curator or user in obj.course_offering.teachers.all()


class CourseOfferingNewsUnreadNotificationsView(ListAPIView):
    permission_classes = [CuratorAccessPermission]
    serializer_class = CourseOfferingNewsNotificationSerializer

    def get_queryset(self):
        return (CourseOfferingNewsNotification.unread
                .filter(course_offering_news_id=self.kwargs.get('news_pk'))
                .select_related("user")
                .order_by("user__last_name"))
