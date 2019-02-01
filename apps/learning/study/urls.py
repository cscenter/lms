from django.conf.urls import url
from django.urls import path, include
from django.views.generic.base import RedirectView

from learning.study.views import TimetableView, \
    StudentAssignmentStudentDetailView, StudentAssignmentListView, \
    CalendarStudentFullView, CalendarStudentPersonalView
from learning.views import CourseStudentListView, \
    AssignmentAttachmentDownloadView

app_name = 'study'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='study:assignment_list', permanent=False), name='learning_base'),
    path('courses/', CourseStudentListView.as_view(), name='course_list'),
    path('assignments/', include([
        path('', StudentAssignmentListView.as_view(), name='assignment_list'),
        path('<int:pk>/', StudentAssignmentStudentDetailView.as_view(), name='a_s_detail'),
        url(r'^submissions/(?P<student_assignment_id>\d+)/attachments/(?P<sid>[-\w]+)/(?P<file_name>.+)$', AssignmentAttachmentDownloadView.as_view(), name='assignment_comment_attachments_download'),
    ])),
    url(r'^attachments/(?P<sid>[-\w]+)/(?P<file_name>.+)$',
        AssignmentAttachmentDownloadView.as_view(),
        name='assignment_attachments_download'),
    path('timetable/', TimetableView.as_view(), name='timetable'),
    path('calendar/', CalendarStudentPersonalView.as_view(), name='calendar'),
    path('full-calendar/', CalendarStudentFullView.as_view(), name='calendar_full'),
]
