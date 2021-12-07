from vanilla import CreateView, DeleteView, UpdateView

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.db import IntegrityError, transaction
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _

from auth.mixins import PermissionRequiredMixin
from core.exceptions import Redirect
from core.views import ProtectedFormMixin
from courses.forms import CourseNewsForm
from courses.models import Course, CourseNews
from courses.views.mixins import CourseURLParamsMixin
from learning.permissions import CreateCourseNews, EditCourseNews, DeleteCourseNews
from users.mixins import TeacherOnlyMixin

__all__ = ('CourseNewsCreateView', 'CourseNewsUpdateView',
           'CourseNewsDeleteView')


class CourseNewsCreateView(PermissionRequiredMixin, CourseURLParamsMixin, CreateView):
    model = CourseNews
    template_name = "courses/simple_crispy_form.html"
    form_class = CourseNewsForm
    permission_required = CreateCourseNews.name

    def get_form(self, **kwargs):
        form_class = self.get_form_class()
        kwargs["course"] = self.course
        return form_class(**kwargs)

    def get_permission_object(self):
        return self.course

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


class CourseNewsUpdateView(PermissionRequiredMixin, CourseURLParamsMixin,
                           UpdateView):
    model = CourseNews
    template_name = "courses/simple_crispy_form.html"
    permission_required = EditCourseNews.name
    form_class = CourseNewsForm

    def get_permission_object(self):
        return self.course

    def get_success_url(self):
        return self.object.course.get_url_for_tab("news")


class CourseNewsDeleteView(PermissionRequiredMixin, CourseURLParamsMixin,
                           DeleteView):
    model = CourseNews
    permission_required = DeleteCourseNews.name
    template_name = "forms/simple_delete_confirmation.html"

    def get_permission_object(self):
        return self.course

    def get_success_url(self):
        """
        Since we don't check was it the last deleted news or not - redirect to
        default active tab.
        """
        return self.object.course.get_absolute_url()

