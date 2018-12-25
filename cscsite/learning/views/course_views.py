import logging

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.db import transaction, IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from rest_framework.generics import ListAPIView
from vanilla import DeleteView, UpdateView, CreateView, TemplateView

from api.permissions import CuratorAccessPermission
from core.exceptions import Redirect
from core.views import ProtectedFormMixin
from courses.forms import CourseEditDescrForm, CourseNewsForm
from learning.models import CourseNewsNotification
from courses.models import Course, CourseNews
from learning.api.serializers import CourseNewsNotificationSerializer
from learning.viewmixins import TeacherOnlyMixin
from learning.views.utils import get_co_from_query_params

__all__ = ['CourseEditView',
           'CourseNewsCreateView', 'CourseNewsUpdateView',
           'CourseNewsDeleteView', 'CourseNewsUnreadNotificationsView',
           'CourseStudentsView']


logger = logging.getLogger(__name__)


class CourseStudentsView(TeacherOnlyMixin, TemplateView):
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
class CourseEditView(TeacherOnlyMixin, ProtectedFormMixin,
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


class CourseNewsCreateView(TeacherOnlyMixin, CreateView):
    model = CourseNews
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseNewsForm

    def get_form(self, **kwargs):
        form_class = self.get_form_class()
        co = get_co_from_query_params(self.kwargs, self.request.city_code)
        if not co:
            raise Http404('Course not found')
        if not self.is_form_allowed(self.request.user, co):
            raise Redirect(to=redirect_to_login(self.request.get_full_path()))
        kwargs["course"] = co
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
        return self.object.course.get_url_for_tab("news")

    def is_form_allowed(self, user, course: Course):
        return user.is_curator or user in course.teachers.all()


class CourseNewsUpdateView(TeacherOnlyMixin, ProtectedFormMixin,
                           UpdateView):
    model = CourseNews
    template_name = "learning/simple_crispy_form.html"
    form_class = CourseNewsForm

    def get_success_url(self):
        return self.object.course.get_url_for_tab("news")

    def is_form_allowed(self, user, obj: CourseNews):
        return user.is_curator or user in obj.course.teachers.all()


class CourseNewsDeleteView(TeacherOnlyMixin, ProtectedFormMixin,
                           DeleteView):
    model = CourseNews
    template_name = "learning/simple_delete_confirmation.html"

    def get_success_url(self):
        """
        Since we don't check was it the last deleted news or not - redirect to
        default active tab.
        """
        return self.object.course.get_absolute_url()

    def is_form_allowed(self, user, obj: CourseNews):
        return user.is_curator or user in obj.course.teachers.all()


class CourseNewsUnreadNotificationsView(ListAPIView):
    permission_classes = [CuratorAccessPermission]
    serializer_class = CourseNewsNotificationSerializer

    def get_queryset(self):
        return (CourseNewsNotification.unread
                .filter(course_offering_news_id=self.kwargs.get('news_pk'))
                .select_related("user")
                .order_by("user__last_name"))
