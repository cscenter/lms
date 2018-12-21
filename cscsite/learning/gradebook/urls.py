from django.conf.urls import url

from .views import (GradeBookTeacherDispatchView, GradeBookTeacherView,
                    GradeBookTeacherCSVView,
                    AssignmentScoresImportByStepikIDView,
                    AssignmentScoresImportByYandexLoginView)

app_name = 'gradebook'


urlpatterns = [
    url(r'^$',
        GradeBookTeacherDispatchView.as_view(),
        name='markssheet_teacher_dispatch'),
    url(
        r'^(?P<city>[-\w]+)/(?P<course_slug>[-\w]+)/(?P<semester_year>\d+)-(?P<semester_type>\w+)/$',
        GradeBookTeacherView.as_view(),
        name='markssheet_teacher'),
    url(
        r'^(?P<city>[-\w]+)/(?P<course_slug>[-\w]+)/(?P<semester_year>\d+)-(?P<semester_type>\w+)/csv/$',
        GradeBookTeacherCSVView.as_view(),
        name='markssheet_teacher_csv'),
    url(r'^(?P<course_id>\d+)/import/stepic$',
        AssignmentScoresImportByStepikIDView.as_view(),
        name='markssheet_teacher_csv_import_stepic'),
    url(r'^(?P<course_id>\d+)/import/yandex$',
        AssignmentScoresImportByYandexLoginView.as_view(),
        name='markssheet_teacher_csv_import_yandex'),
]
