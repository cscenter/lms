from django.urls import include, path, re_path
from django.views.generic.base import RedirectView

from courses.urls import RE_COURSE_URI
from learning.api.views import CourseNewsUnreadNotificationsView
from learning.gradebook import views as gv
from learning.teaching.api.views import (
    PersonalAssignmentScoreAuditLogView, StudentGroupTransferStudentsView
)
from learning.teaching.views import (
    CalendarFullView, CalendarPersonalView, CourseListView, CourseStudentProgressView,
    GradeBookListView, TeachingUsefulListView
)
from learning.teaching.views import TimetableView as TeacherTimetable
from learning.teaching.views.assignments import (
    AssignmentCheckQueueView, AssignmentCommentUpdateView, AssignmentDetailView,
    AssignmentDownloadSolutionAttachmentsView, StudentAssignmentCommentCreateView,
    StudentAssignmentDetailView, AssignmentStatusLogCSVView, AssignmentStudentAnswersCSVView
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

scores_api_patterns = [
    path('personal-assignments/<int:student_assignment_id>/score-audit-log/', PersonalAssignmentScoreAuditLogView.as_view(), name='audit_log')
]

urlpatterns = [
    # TODO: add login_required before redirect
    path('', RedirectView.as_view(pattern_name='teaching:assignments_check_queue', permanent=False), name='base'),
    path('timetable/', TeacherTimetable.as_view(), name='timetable'),
    path('calendar/', CalendarPersonalView.as_view(), name='calendar'),
    path('useful/', TeachingUsefulListView.as_view(), name='teaching_useful'),
    path('full-calendar/', CalendarFullView.as_view(), name='calendar_full'),
    path('courses/', include([
        path('', CourseListView.as_view(), name='course_list'),
        path('', include((student_group_patterns, 'student_groups'))),
        re_path(RE_COURSE_URI, include([
            path('students/', include([
                path('<int:enrollment_id>/', CourseStudentProgressView.as_view(), name='student-progress'),
            ]))
        ])),
        # TODO: separate api views?
        path("news/<int:news_pk>/stats", CourseNewsUnreadNotificationsView.as_view(), name="course_news_unread"),
    ])),
    path('assignments/', include([
        path('', AssignmentCheckQueueView.as_view(), name='assignments_check_queue'),
        path('<int:pk>/', AssignmentDetailView.as_view(), name='assignment_detail'),
        path('<int:pk>/export/status-changes', AssignmentStatusLogCSVView.as_view(), name='assignment_status_log_csv'),
        path('<int:pk>/export/text-solutions', AssignmentStudentAnswersCSVView.as_view(), name='assignment_student_answers_csv'),
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
            path('assignments-stepik', gv.ImportAssignmentScoresByStepikIDView.as_view(), name='gradebook_import_scores_by_stepik_id'),
            path('assignments-yandex-login', gv.ImportAssignmentScoresByYandexLoginView.as_view(), name='gradebook_import_scores_by_yandex_login'),
            path('assignments-enrollments', gv.ImportAssignmentScoresByEnrollmentIDView.as_view(), name='gradebook_import_scores_by_enrollment_id'),
            path('course-grades-stepik', gv.ImportCourseGradesByStepikIDView.as_view(), name='gradebook_import_course_grades_by_stepik_id'),
            path('course-grades-yandex', gv.ImportCourseGradesByYandexLoginView.as_view(), name='gradebook_import_course_grades_by_yandex_login'),
            path('course-grades-enrollments', gv.ImportCourseGradesByEnrollmentIDView.as_view(), name='gradebook_import_course_grades_by_enrollment_id')
        ])),
    ])),
    path('api/', include(([
        path('', include((student_group_api_patterns, 'student-groups'))),
        path('scores/', include((import_scores_api_patterns, 'import-scores'))),
        path('v1/', include((scores_api_patterns, 'scores'))),
    ], 'api'))),
]
