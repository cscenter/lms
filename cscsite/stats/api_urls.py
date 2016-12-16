from django.conf.urls import include, url

from stats.views import CourseParticipantsStatsByGroup, AssignmentsStats

urlpatterns = [
    # {% url "api:stats_participants" course_slug semester_slug %}
    url(r'^stats/', include([
        url(r'^participants/(?P<course_session_id>\d+)/$',
            CourseParticipantsStatsByGroup.as_view(),
            name='stats_participants'),
        url(r'^assignments/(?P<course_session_id>\d+)/$',
            AssignmentsStats.as_view(),
            name='stats_assignments'),
    ]))
]
