from django.urls import path, include
from django.views.generic.base import RedirectView

from learning.study.views import TimetableView, \
    StudentAssignmentDetailView, StudentAssignmentListView, \
    CalendarFullView, CalendarPersonalView, CourseListView, \
    StudentAssignmentCommentCreateView, AssignmentExecutionTimeUpdateView
from learning.views import AssignmentAttachmentDownloadView, \
    AssignmentCommentAttachmentDownloadView

app_name = 'study'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='study:assignment_list', permanent=False), name='learning_base'),
    path('assignments/', include([
        path('', StudentAssignmentListView.as_view(), name='assignment_list'),
        path('<int:pk>/', StudentAssignmentDetailView.as_view(), name='student_assignment_detail'),
        path('<int:pk>/execution-time/', AssignmentExecutionTimeUpdateView.as_view(), name='student_assignment_execution_time_update'),
        path('<int:pk>/comments/', StudentAssignmentCommentCreateView.as_view(), name='assignment_comment_create'),
        path('attachments/', include([
            path('<slug:sid>/<str:file_name>', AssignmentAttachmentDownloadView.as_view(), name='download_assignment_attachment'),
            path('comments/<slug:sid>/<str:file_name>', AssignmentCommentAttachmentDownloadView.as_view(), name='download_assignment_comment_attachment'),
        ])),
    ])),
    path('timetable/', TimetableView.as_view(), name='timetable'),
    path('calendar/', CalendarPersonalView.as_view(), name='calendar'),
    path('full-calendar/', CalendarFullView.as_view(), name='calendar_full'),
    path('courses/', CourseListView.as_view(), name='course_list'),
]
