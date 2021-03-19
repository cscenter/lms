from django.urls import re_path

from .views import CourseParticipantsStatsByYear, AssignmentsStats, \
    EnrollmentsStats, CourseParticipantsStatsByType

urlpatterns = [
    re_path(r'^participants/(?P<course_id>\d+)/groups/$', CourseParticipantsStatsByType.as_view(), name='stats_learning_participants_group'),
    re_path(r'^participants/(?P<course_id>\d+)/year/$', CourseParticipantsStatsByYear.as_view(), name='stats_learning_participants_year'),
    re_path(r'^assignments/(?P<course_id>\d+)/$', AssignmentsStats.as_view({'get': 'list'}), name='stats_assignments'),
    re_path(r'^enrollments/(?P<course_id>\d+)/$', EnrollmentsStats.as_view(), name='stats_enrollments'),
]
