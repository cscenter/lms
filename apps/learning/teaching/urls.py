from django.conf.urls import include, url
from django.urls import path, re_path
from django.views.generic.base import RedirectView

from courses.urls import RE_COURSE_URI
from learning.gradebook import views as gv
from learning.teaching.views import TimetableView as TeacherTimetable, \
    AssignmentCommentUpdateView, AssignmentDetailView, AssignmentListView, \
    CalendarFullView, CalendarPersonalView, CourseListView, \
    StudentAssignmentDetailView, GradeBookListView, \
    StudentAssignmentCommentCreateView
from learning.api.views import CourseNewsUnreadNotificationsView


app_name = 'teaching'

urlpatterns = [
    # Redirects with relative url since RedirectView uses django's `
    # reverse` implementation
    path('', RedirectView.as_view(pattern_name='teaching:assignment_list', permanent=False), name='base'),
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
        path('submissions/<int:pk>/', StudentAssignmentDetailView.as_view(), name='student_assignment_detail'),
        path('submissions/<int:pk>/comments/', StudentAssignmentCommentCreateView.as_view(), name='assignment_comment_create'),
        path('submissions/<int:pk>/comments/<int:comment_pk>/update/', AssignmentCommentUpdateView.as_view(), name='student_assignment_comment_edit'),
    ])),
    path('marks/', include([
        path('', GradeBookListView.as_view(), name='gradebook_list'),
        re_path(RE_COURSE_URI, include([
            path('', gv.GradeBookView.as_view(), name='gradebook'),
            path('csv/', gv.GradeBookCSVView.as_view(), name='gradebook_csv'),
        ])),
        path('<int:course_id>/import/stepic', gv.AssignmentScoresImportByStepikIDView.as_view(), name='gradebook_csv_import_stepic'),
        path('<int:course_id>/import/yandex', gv.AssignmentScoresImportByYandexLoginView.as_view(), name='gradebook_csv_import_yandex'),
    ])),
]
