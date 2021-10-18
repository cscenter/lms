from django.urls import include, path, re_path
from django.views.generic.base import RedirectView

from courses.urls import RE_COURSE_URI
from learning.api.views import CourseNewsUnreadNotificationsView
from learning.gradebook import views as gv
from learning.teaching.api.student_groups import StudentGroupTransferStudentsView
from learning.teaching.views import (
    CalendarFullView, CalendarPersonalView, CourseListView, GradeBookListView
)
from learning.teaching.views import TimetableView as TeacherTimetable
from learning.teaching.views.assignments import (
    AssignmentCheckQueueView, AssignmentCommentUpdateView, AssignmentDetailView,
    AssignmentDownloadSolutionAttachmentsView, StudentAssignmentCommentCreateView,
    StudentAssignmentDetailView
)
from learning.teaching.views.student_groups import (
    StudentGroupCreateView, StudentGroupDeleteView, StudentGroupDetailView,
    StudentGroupListView, StudentGroupUpdateView
)

app_name = 'teaching'

student_group_patterns = [
    re_path(RE_COURSE_URI, include([
        path('student-groups/', include([
            path('', StudentGroupListView.as_view(), name='list'),
            path('create/', StudentGroupCreateView.as_view(), name='create'),
            path('<int:pk>/update/', StudentGroupUpdateView.as_view(), name='update'),
            path('<int:pk>/delete/', StudentGroupDeleteView.as_view(), name='delete'),
            path('<int:pk>/', StudentGroupDetailView.as_view(), name='detail'),
        ])),
    ])),
]

student_group_api_patterns = [
    path('student-groups/<int:source_student_group>/transfer/', StudentGroupTransferStudentsView.as_view(), name='transfer'),
]

import_scores_api_patterns = [
    path('<int:course_id>/import/yandex-contest/', gv.GradebookImportScoresFromYandexContest.as_view(), name='yandex_contest')
]

urlpatterns = [
    # TODO: add login_required before redirect
    path('', RedirectView.as_view(pattern_name='teaching:assignments_check_queue', permanent=False), name='base'),
    path('timetable/', TeacherTimetable.as_view(), name='timetable'),
    path('calendar/', CalendarPersonalView.as_view(), name='calendar'),
    path('full-calendar/', CalendarFullView.as_view(), name='calendar_full'),
    path('courses/', include([
        path('', CourseListView.as_view(), name='course_list'),
        path('', include((student_group_patterns, 'student_groups'))),
        # TODO: separate api views?
        path("news/<int:news_pk>/stats", CourseNewsUnreadNotificationsView.as_view(), name="course_news_unread"),
    ])),
    path('assignments/', include([
        path('', AssignmentCheckQueueView.as_view(), name='assignments_check_queue'),
        path('<int:pk>/', AssignmentDetailView.as_view(), name='assignment_detail'),
        path('<int:pk>/export/solution-attachments/', AssignmentDownloadSolutionAttachmentsView.as_view(), name='assignment_download_solution_attachments'),
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
        path('<int:course_id>/import/csv/', include([
            path('stepik', gv.ImportAssignmentScoresByStepikIDView.as_view(), name='gradebook_import_scores_by_stepik_id'),
            path('yandex-login', gv.ImportAssignmentScoresByYandexLoginView.as_view(), name='gradebook_import_scores_by_yandex_login'),
            path('enrollments', gv.ImportAssignmentScoresByEnrollmentIDView.as_view(), name='gradebook_import_scores_by_enrollment_id'),
        ])),
    ])),
    path('api/', include(([
        path('', include((student_group_api_patterns, 'student-groups'))),
        path('scores/', include((import_scores_api_patterns, 'import-scores'))),
    ], 'api'))),
]
