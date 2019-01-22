from django.conf import settings
from django.conf.urls import url
from django.contrib.auth import views
from django.urls import path

from learning.views.icalendar import ICalClassesView, ICalAssignmentsView, \
    ICalEventsView
from users.views import LoginView, LogoutView, UserDetailView, UserUpdateView, \
    EnrollmentCertificateCreateView, EnrollmentCertificateDetailView, \
    pass_reset_view

auth_urls = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(permanent=False), name='logout'),

    path('password_change/', views.PasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', views.PasswordChangeDoneView.as_view(), name='password_change_done'),

    path('password_reset/', pass_reset_view, name='password_reset'),
    path('password_reset/done/', views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]

urlpatterns = [
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/edit/', UserUpdateView.as_view(), name='user_update'),
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
