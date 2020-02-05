from django.urls import path

from learning.views.icalendar import ICalClassesView, ICalAssignmentsView
from users.views import UserDetailView, UserUpdateView, \
    ProfileImageUpdate

urlpatterns = [
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/edit/', UserUpdateView.as_view(), name='user_update'),
    path('users/<int:pk>/profile-update-image/', ProfileImageUpdate.as_view(), name="profile_update_image"),
    path('users/<int:pk>/csc_classes.ics', ICalClassesView.as_view(), name='user_ical_classes'),
    path('users/<int:pk>/csc_assignments.ics', ICalAssignmentsView.as_view(), name='user_ical_assignments'),
]
