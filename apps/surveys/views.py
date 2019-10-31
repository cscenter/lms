from django.contrib import messages
from django.http import Http404
from django.shortcuts import render, get_object_or_404
from django.views.generic import FormView
from vanilla import TemplateView

from core.exceptions import Redirect
from core.urls import reverse
from courses.models import Course
from courses.views.mixins import CourseURLParamsMixin
from learning.settings import Branches
from surveys.forms import FormBuilder
from surveys.models import CourseSurvey


class CourseSurveyDetailView(CourseURLParamsMixin, FormView):
    template_name = "surveys/survey_detail.html"

    def get_success_url(self):
        return reverse("surveys:form_success", kwargs=self.kwargs)

    def get_course_queryset(self):
        return (super().get_course_queryset()
                .select_related("meta_course", "semester"))

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        survey = get_object_or_404(
            (CourseSurvey.objects
             .select_related("form")),
            course=self.course,
            form__slug=self.kwargs["survey_form_slug"])
        survey.course = self.course
        if not survey.is_published and not self.request.user.is_curator:
            raise Http404
        if not survey.is_active and not self.request.user.is_curator:
            msg = "Опрос окончен. Перенаправляем на страницу курса."
            messages.info(self.request, msg,
                          extra_tags='timeout')
            raise Redirect(to=self.course.get_absolute_url())
        return FormBuilder(survey, **self.get_form_kwargs())

    def form_valid(self, form):
        """If the form is valid, save the associated model."""
        form.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        survey = context['form'].survey
        # Course survey is anonymous so we can't show deadline in the
        # timezone of the student. Let's use msk timezone for everyone
        if survey.expire_at:
            context['survey_deadline'] = survey.expire_at_local(
                tz=Branches.get_choice(Branches.SPB).timezone,
                format="j E H:i")
        return context


class CourseSurveyFormSuccessView(CourseURLParamsMixin, TemplateView):
    template_name = "surveys/survey_success.html"

    def get_context_data(self, **kwargs):
        return {"course": self.course}
