from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import FormView

from surveys.forms import FormBuilder
from surveys.models import Form, CourseOfferingSurvey


class CourseSurveyDetailView(FormView):
    template_name = "surveys/survey_detail.html"

    def get_success_url(self):
        return reverse("surveys:form_success", kwargs=self.kwargs)

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        survey = get_object_or_404(
            CourseOfferingSurvey.objects.select_related("form"),
            course_offering__course__slug=self.kwargs['course_slug'],
            course_offering__city_id=self.request.city_code,
            course_offering__semester__year=self.kwargs['semester_year'],
            course_offering__semester__type=self.kwargs['semester_type'],
            form__slug=self.kwargs["slug"])
        return FormBuilder(survey.form, **self.get_form_kwargs())

    def form_valid(self, form):
        """If the form is valid, save the associated model."""
        form.save()
        return super().form_valid(form)


form_detail = CourseSurveyDetailView.as_view()


def form_success(request, slug, **kwargs):
    return render(request, 'surveys/survey_success.html')
