from typing import TYPE_CHECKING, Any

from vanilla import CreateView, DeleteView, UpdateView

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _

from auth.mixins import PermissionRequiredMixin
from core.http import HttpRequest
from courses.forms import CourseNewsForm
from courses.models import Course, CourseNews
from courses.views.mixins import CourseURLParamsMixin
from learning.permissions import CreateCourseNews, DeleteCourseNews, EditCourseNews

__all__ = ('CourseNewsCreateView', 'CourseNewsUpdateView',
           'CourseNewsDeleteView')

if TYPE_CHECKING:
    from django.views import View
    CourseNewsURLParamsMixinBase = View
else:
    CourseNewsURLParamsMixinBase = object


class CourseNewsCreateView(PermissionRequiredMixin, CourseURLParamsMixin, CreateView):
    model = CourseNews
    template_name = "courses/simple_crispy_form.html"
    form_class = CourseNewsForm
    permission_required = CreateCourseNews.name

    def get_permission_object(self):
        return self.course

    def get_form(self, **kwargs):
        form_class = self.get_form_class()
        kwargs["course"] = self.course
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


class CourseNewsURLParamsMixin(CourseNewsURLParamsMixinBase):
    course_news: CourseNews

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any):
        super().setup(request, *args, **kwargs)
        self.course_news = get_object_or_404(
            CourseNews.objects.filter(pk=kwargs['pk'])
        )


class CourseNewsUpdateView(PermissionRequiredMixin, CourseNewsURLParamsMixin,
                           UpdateView):
    model = CourseNews
    template_name = "courses/simple_crispy_form.html"
    permission_required = EditCourseNews.name
    form_class = CourseNewsForm

    def get_permission_object(self):
        return self.course_news

    def get_object(self):
        return self.course_news

    def get_success_url(self):
        return self.object.course.get_url_for_tab("news")


class CourseNewsDeleteView(PermissionRequiredMixin, CourseNewsURLParamsMixin,
                           DeleteView):
    model = CourseNews
    permission_required = DeleteCourseNews.name
    template_name = "forms/simple_delete_confirmation.html"

    def get_permission_object(self):
        return self.course_news

    def get_object(self):
        return self.course_news

    def get_success_url(self):
        """
        Since we don't check was it the last deleted news or not - redirect to
        default active tab.
        """
        return self.object.course.get_absolute_url()

