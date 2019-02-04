from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.db import transaction, IntegrityError
from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import ugettext_lazy as _
from vanilla import CreateView, UpdateView, DeleteView

from core.exceptions import Redirect
from core.views import ProtectedFormMixin
from courses.forms import CourseNewsForm
from courses.models import Course, CourseNews
from courses.views.mixins import CourseURLParamsMixin
from users.mixins import TeacherOnlyMixin

__all__ = ('CourseNewsCreateView', 'CourseNewsUpdateView',
           'CourseNewsDeleteView')


class CourseNewsCreateView(TeacherOnlyMixin, CourseURLParamsMixin, CreateView):
    model = CourseNews
    template_name = "courses/simple_crispy_form.html"
    form_class = CourseNewsForm

    def get_form(self, **kwargs):
        form_class = self.get_form_class()
        course = get_object_or_404(self.get_course_queryset())
        if not self.is_form_allowed(self.request.user, course):
            raise Redirect(to=redirect_to_login(self.request.get_full_path()))
        kwargs["course"] = course
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
    template_name = "courses/simple_crispy_form.html"
    form_class = CourseNewsForm

    def get_success_url(self):
        return self.object.course.get_url_for_tab("news")

    def is_form_allowed(self, user, obj: CourseNews):
        return user.is_curator or user in obj.course.teachers.all()


class CourseNewsDeleteView(TeacherOnlyMixin, ProtectedFormMixin,
                           DeleteView):
    model = CourseNews
    template_name = "forms/simple_delete_confirmation.html"

    def get_success_url(self):
        """
        Since we don't check was it the last deleted news or not - redirect to
        default active tab.
        """
        return self.object.course.get_absolute_url()

    def is_form_allowed(self, user, obj: CourseNews):
        return user.is_curator or user in obj.course.teachers.all()
