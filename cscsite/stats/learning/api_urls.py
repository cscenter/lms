from django.conf.urls import include, url

from .views import CourseParticipantsStatsByYear, AssignmentsStats, \
    EnrollmentsStats, CourseParticipantsStatsByGroup

urlpatterns = [
        url(r'^participants/(?P<course_session_id>\d+)/groups/$',
            CourseParticipantsStatsByGroup.as_view(),
            name='stats_learning_participants_group'),
        url(r'^participants/(?P<course_session_id>\d+)/year/$',
            CourseParticipantsStatsByYear.as_view(),
            name='stats_learning_participants_year'),
        url(r'^assignments/(?P<course_session_id>\d+)/$',
            AssignmentsStats.as_view(),
            name='stats_assignments'),
        url(r'^enrollments/(?P<course_session_id>\d+)/$',
            EnrollmentsStats.as_view(),
            name='stats_enrollments'),
]
