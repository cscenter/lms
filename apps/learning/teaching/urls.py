from django.conf.urls import include, url
from django.views.generic.base import RedirectView

from learning.teaching.views import TimetableView as TeacherTimetable
from learning.views import CalendarTeacherFullView, \
    CalendarTeacherPersonalView, CourseTeacherListView, \
    AssignmentTeacherListView, \
    AssignmentTeacherDetailView, StudentAssignmentTeacherDetailView, \
    AssignmentCommentUpdateView

urlpatterns = [
    url(r'^$', RedirectView.as_view(pattern_name='assignment_list_teacher',
                                    permanent=True),
        name='teaching_base'),
    url(r'^timetable/$', TeacherTimetable.as_view(),
        name='timetable_teacher'),
    url(r'^calendar/$', CalendarTeacherPersonalView.as_view(),
        name='calendar_teacher'),
    url(r'^full-calendar/$', CalendarTeacherFullView.as_view(),
        name='calendar_full_teacher'),
    url(r'^courses/$', CourseTeacherListView.as_view(),
        name='course_list_teacher'),
    url(r'^assignments/', include([
        url(r'^$',
            AssignmentTeacherListView.as_view(),
            name='assignment_list_teacher'),
        url(r'^(?P<pk>\d+)/$',
            AssignmentTeacherDetailView.as_view(),
            name='assignment_detail_teacher'),
        url(r'^submissions/(?P<pk>\d+)/$',
            StudentAssignmentTeacherDetailView.as_view(),
            name='a_s_detail_teacher'),
        url(
            r'^submissions/(?P<submission_pk>\d+)/comment/(?P<comment_pk>\d+)/update/$',
            AssignmentCommentUpdateView.as_view(),
            name='assignment_submission_comment_edit'),
    ])),
    url(r'^marks/', include('learning.gradebook.urls')),
]
