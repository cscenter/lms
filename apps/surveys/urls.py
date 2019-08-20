from django.conf.urls import include, url

from courses.urls import RE_COURSE_URI
from surveys import views

app_name = 'surveys'

urlpatterns = [
    url(RE_COURSE_URI + r"(?P<survey_form_slug>[-\w]+)/", include([
        url(r"^$", views.CourseSurveyDetailView.as_view(), name='form_detail'),
        url(r"^success/$", views.CourseSurveyFormSuccessView.as_view(), name='form_success'),
    ]))
]
