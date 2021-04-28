from django.urls import include, path
from django.views.generic.base import RedirectView

from learning.study.views import (
    CalendarFullView, CalendarPersonalView, CourseListView,
    StudentAssignmentCommentCreateView, StudentAssignmentDetailView,
    StudentAssignmentListView, StudentAssignmentSolutionCreateView, TimetableView
)
from learning.views import (
    AssignmentAttachmentDownloadView, AssignmentCommentAttachmentDownloadView
)
from learning.views.views import AssignmentSubmissionAttachmentDownloadView

app_name = 'study'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='study:assignment_list', permanent=False), name='learning_base'),
    path('assignments/', include([
        path('', StudentAssignmentListView.as_view(), name='assignment_list'),
        path('<int:pk>/', StudentAssignmentDetailView.as_view(), name='student_assignment_detail'),
        path('<int:pk>/comments/', StudentAssignmentCommentCreateView.as_view(), name='assignment_comment_create'),
        path('<int:pk>/solutions/', StudentAssignmentSolutionCreateView.as_view(), name='assignment_solution_create'),
    ])),
    path('attachments/assignments/', include([
        path('comments/<slug:sid>/<str:file_name>', AssignmentCommentAttachmentDownloadView.as_view(), name='download_assignment_comment_attachment'),
        path('submissions/<slug:sid>/<str:file_name>', AssignmentSubmissionAttachmentDownloadView.as_view(), name='download_submission_attachment'),
        path('<slug:sid>/<str:file_name>', AssignmentAttachmentDownloadView.as_view(), name='download_assignment_attachment'),
    ])),
    path('timetable/', TimetableView.as_view(), name='timetable'),
    path('calendar/', CalendarPersonalView.as_view(), name='calendar'),
    path('full-calendar/', CalendarFullView.as_view(), name='calendar_full'),
    path('courses/', CourseListView.as_view(), name='course_list'),
]
