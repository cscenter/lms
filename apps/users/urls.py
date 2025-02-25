from django.conf import settings
from django.urls import include, path, re_path

from learning.views import EventDetailView
from learning.views.icalendar import (
    ICalAssignmentsView, ICalClassesView, ICalEventsView, ICalInterviewsView
)
from users.views import (
    ConnectedAuthServicesView, ProfileImageUpdate, UserDetailView, UserUpdateView
)

user_api_patterns = []
if settings.IS_SOCIAL_ACCOUNTS_ENABLED:
    user_api_patterns += [
        path('users/<int:user>/connected-accounts/', ConnectedAuthServicesView.as_view(), name="connected_accounts"),
    ]


urlpatterns = [
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/edit/', UserUpdateView.as_view(), name='user_update'),
    path('users/<int:pk>/profile-update-image/', ProfileImageUpdate.as_view(), name="profile_update_image"),
    # iCalendar
    path("events/<int:pk>/", EventDetailView.as_view(), name="non_course_event_detail"),
    re_path(r'^events.ics', ICalEventsView.as_view(), name='ical_events'),
    path('users/<encoded_pk>/classes.ics', ICalClassesView.as_view(), name='user_ical_classes'),
    path('users/<encoded_pk>/assignments.ics', ICalAssignmentsView.as_view(), name='user_ical_assignments'),
    path('users/<encoded_pk>/interviews.ics', ICalInterviewsView.as_view(), name='user_ical_interviews'),

    path('api/v1/', include(([
        path('', include((user_api_patterns, 'api'))),
    ])))
]
