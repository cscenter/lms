from django.urls import include, path, re_path

from courses.urls import RE_COURSE_URI
from surveys import views

app_name = 'surveys'

urlpatterns = [
    re_path(RE_COURSE_URI + r"(?P<survey_form_slug>[-\w]+)/", include([
        path(r"", views.CourseSurveyDetailView.as_view(), name='form_detail'),
        path(r"success/", views.CourseSurveyFormSuccessView.as_view(), name='form_success'),
    ])),
    path("report_bug", views.ReportBugView.as_view(), name='report_bug'),
    path("report_idea", views.ReportIdeaView.as_view(), name='report_idea')
]
