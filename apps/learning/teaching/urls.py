from django.conf.urls import include, url
from django.urls import path, re_path
from django.views.generic.base import RedirectView

from learning.gradebook import views as gv
from learning.teaching.views import TimetableView as TeacherTimetable, \
    AssignmentCommentUpdateView, AssignmentDetailView, AssignmentListView, \
    CalendarFullView, CalendarPersonalView, CourseListView
from learning.views import StudentAssignmentTeacherDetailView
from learning.api.views import CourseNewsUnreadNotificationsView

COURSE_URI = r'^(?P<city>[-\w]+)/(?P<course_slug>[-\w]+)/(?P<semester_year>\d+)-(?P<semester_type>\w+)/'


app_name = 'teaching'
urlpatterns = [
    path('', RedirectView.as_view(pattern_name='assignment_list', permanent=False), name='base'),
    path('timetable/', TeacherTimetable.as_view(), name='timetable'),
    path('calendar/', CalendarPersonalView.as_view(), name='calendar'),
    path('full-calendar/', CalendarFullView.as_view(), name='calendar_full'),
    path('courses/', include([
        path('', CourseListView.as_view(), name='course_list'),
        path("news/<int:news_pk>/stats", CourseNewsUnreadNotificationsView.as_view(), name="course_news_unread"),
    ])),
    path('assignments/', include([
        path('', AssignmentListView.as_view(), name='assignment_list'),
        path('<int:pk>/', AssignmentDetailView.as_view(), name='assignment_detail'),
        path('submissions/<int:pk>/', StudentAssignmentTeacherDetailView.as_view(), name='a_s_detail'),
        # FIXME: move this path to comment model as  `get_comment_update_url`
        path('submissions/<int:submission_pk>/comment/<int:comment_pk>/update/', AssignmentCommentUpdateView.as_view(), name='assignment_submission_comment_edit'),
    ])),
    path('marks/', include([
        path('', gv.GradeBookTeacherDispatchView.as_view(), name='gradebook_dispatch'),
        # FIXME: make compatible with RE_COURSE_URI
        re_path(COURSE_URI, include([
            path('', gv.GradeBookTeacherView.as_view(), name='gradebook'),
            path('csv/', gv.GradeBookTeacherCSVView.as_view(), name='gradebook_csv'),
        ])),
        path('<int:course_id>/import/stepic', gv.AssignmentScoresImportByStepikIDView.as_view(), name='gradebook_csv_import_stepic'),
        path('<int:course_id>/import/yandex', gv.AssignmentScoresImportByYandexLoginView.as_view(), name='gradebook_csv_import_yandex'),
    ])),
]
