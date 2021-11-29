from django.urls import path, re_path

from learning.views import EventDetailView
from learning.views.icalendar import (
    ICalAssignmentsView, ICalClassesView, ICalEventsView
)
from users.views import (
    ProfileImageUpdate, UserConnectedAuthServicesView, UserDetailView, UserUpdateView
)

urlpatterns = [
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/edit/', UserUpdateView.as_view(), name='user_update'),
    path('users/<int:pk>/profile-update-image/', ProfileImageUpdate.as_view(), name="profile_update_image"),
    path('users/<int:pk>/connected-accounts/', UserConnectedAuthServicesView.as_view(), name="user_connected_accounts"),
    # iCalendar
    path("events/<int:pk>/", EventDetailView.as_view(), name="non_course_event_detail"),
    re_path(r'^events.ics', ICalEventsView.as_view(), name='ical_events'),
    path('users/<int:pk>/classes.ics', ICalClassesView.as_view(), name='user_ical_classes'),
    path('users/<int:pk>/assignments.ics', ICalAssignmentsView.as_view(), name='user_ical_assignments'),
]
