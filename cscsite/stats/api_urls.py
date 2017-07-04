from django.conf.urls import include, url

from stats.views import CourseParticipantsStatsByGroup, AssignmentsStats, \
    EnrollmentsStats

# Run `./manage.py collectstatic_js_reverse` to update js file with urls
urlpatterns = [
    url(r'^stats/', include([
        url(r'^learning/participants/(?P<course_session_id>\d+)/$',
            CourseParticipantsStatsByGroup.as_view({'get': 'list'}),
            name='stats_learning_participants'),
        url(r'^learning/assignments/(?P<course_session_id>\d+)/$',
            AssignmentsStats.as_view(),
            name='stats_assignments'),
        url(r'^learning/enrollments/(?P<course_session_id>\d+)/$',
            EnrollmentsStats.as_view(),
            name='stats_enrollments'),
    ]))
]
