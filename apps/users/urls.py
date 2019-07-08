from django.conf import settings
from django.conf.urls import url
from django.urls import path

from learning.views.icalendar import ICalClassesView, ICalAssignmentsView, \
    ICalEventsView
from users.views import UserDetailView, UserUpdateView, \
    EnrollmentCertificateCreateView, EnrollmentCertificateDetailView, \
    ProfileImageUpdate

urlpatterns = [
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/edit/', UserUpdateView.as_view(), name='user_update'),
    path('users/<int:pk>/profile-update-image/', ProfileImageUpdate.as_view(), name="profile_update_image"),
    # FIXME: disable enrollment certificates on compsciclub.ru
    path('users/<int:pk>/reference/add/', EnrollmentCertificateCreateView.as_view(), name='user_reference_add'),
    path('users/<int:pk>/reference/<int:reference_pk>/', EnrollmentCertificateDetailView.as_view(), name='user_reference_detail'),
    path('users/<int:pk>/csc_classes.ics', ICalClassesView.as_view(), name='user_ical_classes'),
    path('users/<int:pk>/csc_assignments.ics', ICalAssignmentsView.as_view(), name='user_ical_assignments'),
]

extra_patterns = [
    url(r'^csc_events.ics', ICalEventsView.as_view(), name='ical_events'),
]

if settings.SITE_ID == settings.CENTER_SITE_ID:
    urlpatterns.extend(extra_patterns)
