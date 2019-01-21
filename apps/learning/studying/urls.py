from django.conf.urls import url
from django.views.generic.base import RedirectView

from learning.studying.views import TimetableView, \
    StudentAssignmentStudentDetailView, StudentAssignmentListView, \
    CalendarStudentFullView, CalendarStudentPersonalView
from learning.views import CourseStudentListView, \
    AssignmentAttachmentDownloadView

urlpatterns = [
    url(r'^$',
        RedirectView.as_view(pattern_name='assignment_list_student',
                             permanent=True),
        name='learning_base'),
    url(r'^courses/$', CourseStudentListView.as_view(),
        name='course_list_student'),
    url(r'^assignments/$', StudentAssignmentListView.as_view(),
        name='assignment_list_student'),
    url(r'^assignments/(?P<pk>\d+)/$',
        StudentAssignmentStudentDetailView.as_view(),
        name='a_s_detail_student'),
    # TODO: learning/assignments/attachments/?
    url(r'^attachments/(?P<sid>[-\w]+)/(?P<file_name>.+)$',
        AssignmentAttachmentDownloadView.as_view(),
        name='assignment_attachments_download'),
    url(r'^timetable/$', TimetableView.as_view(),
        name='timetable_student'),
    url(r'^calendar/$', CalendarStudentPersonalView.as_view(),
        name='calendar_student'),
    url(r'^full-calendar/$', CalendarStudentFullView.as_view(),
        name='calendar_full_student'),
]
