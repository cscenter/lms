from django.conf.urls import include, url

from .views import CourseParticipantsStatsByYear, AssignmentsStats, \
    EnrollmentsStats, CourseParticipantsStatsByGroup

urlpatterns = [
        url(r'^participants/(?P<course_id>\d+)/groups/$',
            CourseParticipantsStatsByGroup.as_view(),
            name='stats_learning_participants_group'),
        url(r'^participants/(?P<course_id>\d+)/year/$',
            CourseParticipantsStatsByYear.as_view(),
            name='stats_learning_participants_year'),
        url(r'^assignments/(?P<course_id>\d+)/$',
            AssignmentsStats.as_view({'get': 'list'}),
            name='stats_assignments'),
        url(r'^enrollments/(?P<course_id>\d+)/$',
            EnrollmentsStats.as_view(),
            name='stats_enrollments'),
]
