from django.urls import include, path, re_path
from django.views.generic.base import RedirectView

from courses.urls import RE_COURSE_URI
from learning.api.views import CourseNewsUnreadNotificationsView
from learning.gradebook import views as gv
from learning.teaching.views import (
    AssignmentCommentUpdateView, AssignmentDetailView, AssignmentListView,
    CalendarFullView, CalendarPersonalView, CourseListView, GradeBookListView,
    StudentAssignmentCommentCreateView, StudentAssignmentDetailView,
    StudentGroupCreateView, StudentGroupDeleteView, StudentGroupDetailView,
    StudentGroupListView, StudentGroupStudentUpdateView, StudentGroupUpdateView
)
from learning.teaching.views import TimetableView as TeacherTimetable

app_name = 'teaching'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='teaching:assignment_list', permanent=False), name='base'),
    path('timetable/', TeacherTimetable.as_view(), name='timetable'),
    path('calendar/', CalendarPersonalView.as_view(), name='calendar'),
    path('full-calendar/', CalendarFullView.as_view(), name='calendar_full'),
    path('courses/', include([
        path('', CourseListView.as_view(), name='course_list'),
        path('<int:course_pk>/groups/', include([
            path('', StudentGroupListView.as_view(), name='student_group_list'),
            path('create/', StudentGroupCreateView.as_view(), name='student_group_create'),
            path('<int:pk>/update/', StudentGroupUpdateView.as_view(), name='student_group_update'),
            path('<int:pk>/delete/', StudentGroupDeleteView.as_view(), name='student_group_delete'),
            path('<int:group_pk>/', StudentGroupDetailView.as_view(), name='student_group_detail'),
            path('<int:group_pk>/student/<int:pk>/update/', StudentGroupStudentUpdateView.as_view(), name='student_group_student_update'),

        ])),

        # TODO: separate api views?
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
        path('<int:course_id>/import/', include([
            path('stepic', gv.ImportAssignmentScoresByStepikIDView.as_view(), name='gradebook_import_scores_by_stepik_id'),
            path('yandex', gv.ImportAssignmentScoresByYandexLoginView.as_view(), name='gradebook_import_scores_by_yandex_login'),
            path('enrollments', gv.ImportAssignmentScoresByEnrollmentIDView.as_view(), name='gradebook_import_scores_by_enrollment_id'),
        ])),
    ])),
]
