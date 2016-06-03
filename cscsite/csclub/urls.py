from django.conf import settings
from django.conf.urls import patterns, include, url
from solid_i18n.urls import solid_i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from htmlpages import views

from index.views import RobotsView, \
    UnsubscribeYaProxyView, EnrollmentApplicationCallback
from users.views import LoginView, LogoutView, \
    UserDetailView, UserUpdateView, ICalClassesView, ICalAssignmentsView, \
    ICalEventsView, UserReferenceCreateView, UserReferenceDetailView
from learning.views import InternationalSchoolsListView
from learning.urls import course_patterns, course_offering_patterns, \
    student_section_patterns, teaching_section_patterns, venues_patterns
from core.views import MarkdownRenderView
from csclub.views import CalendarClubScheduleView, IndexView, TeachersView, \
    TeacherDetailView


admin.autodiscover()

urlpatterns = solid_i18n_patterns(
    url(r'^$', IndexView.as_view(), name='index'),
    course_patterns,
    course_offering_patterns,
    # Schedule
    url(r"^schedule/$", CalendarClubScheduleView.as_view(),
        name="public_schedule"),
    # Registration
    url(r'^', include('registration.backends.default.urls')),
    # Teachers/Lecturers
    url(r'^teachers/$', TeachersView.as_view(), name='teachers'),
    url(r'^teachers/(?P<pk>\d+)/$', TeacherDetailView.as_view(),
        name='teacher_detail'),
    # International schools
    url(r"^schools/$", InternationalSchoolsListView.as_view(),
        name="international_schools_list"),
    # Auth
    url(r'^login/$', LoginView.as_view(), name='login'),
    url(r'^users/password_change$',
        'django.contrib.auth.views.password_change',
        {'post_change_redirect': 'password_change_complete'},
        name='password_change'),
    url(r'^users/password_change/done$',
        'django.contrib.auth.views.password_change_done',
        name='password_change_complete'),
    url(r'^users/password_reset$',
       'django.contrib.auth.views.password_reset',
       {'post_reset_redirect' : 'password_reset_done',
        'email_template_name': 'emails/password_reset.html'},
       name='password_reset'),
    url(r'^users/password_reset/done$',
        'django.contrib.auth.views.password_reset_done',
        name='password_reset_done'),
    url(r'^users/reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        'django.contrib.auth.views.password_reset_confirm',
        {'post_reset_redirect' : 'password_reset_complete'},
       name='password_reset_confirm'),
    url(r'^users/reset/done$',
        'django.contrib.auth.views.password_reset_complete',
        name='password_reset_complete'),
)

urlpatterns += patterns('',
    url(r'^robots\.txt$', RobotsView.as_view(), name='robotstxt'),
    url(r'^logout/$', LogoutView.as_view(permanent=True), name='logout'),
    url(r'^tools/markdown/preview/$',
        MarkdownRenderView.as_view(),
        name='render_markdown'),
    url(r'^unsubscribe/(?P<sub_hash>[a-f0-9]{32})/',
        UnsubscribeYaProxyView.as_view(), name='unsubscribe_ya'),
    url(r'^private/enrollment_gform_callback/',
        EnrollmentApplicationCallback.as_view(), name='enrollment_gform_cb'),
    url(r'^users/(?P<pk>\d+)/$', UserDetailView.as_view(),
        name='user_detail'),

    # Common for club and center, but not related to learning app
    url(r'^users/(?P<pk>\d+)/reference/add$',
        UserReferenceCreateView.as_view(),
        name='user_reference_add'),
    url(r'^users/(?P<user_id>\d+)/reference/(?P<pk>\d+)$',
        UserReferenceDetailView.as_view(),
        name='user_reference_detail'),
    url(r'^users/(?P<pk>\d+)/csc_classes.ics', ICalClassesView.as_view(),
        name='user_ical_classes'),
    url(r'^users/(?P<pk>\d+)/csc_assignments.ics',
        ICalAssignmentsView.as_view(),
        name='user_ical_assignments'),
    url(r'^csc_events.ics', ICalEventsView.as_view(),
        name='ical_events'),
    url(r'^users/(?P<pk>\d+)/edit$', UserUpdateView.as_view(),
        name='user_update'),

    student_section_patterns,
    teaching_section_patterns,
    venues_patterns,

    url(r'^narnia/', include(admin.site.urls)),
    url(r'^narnia/', include('loginas.urls')),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += [url(r'^rosetta/', include('rosetta.urls'))]

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        url(r'^400/$', 'django.views.defaults.bad_request'),
        url(r'^403/$', 'django.views.defaults.permission_denied'),
        url(r'^404/$', 'django.views.defaults.page_not_found'),
        url(r'^500/$', 'django.views.defaults.server_error'),
    ]

# Note: htmlpages should be the last one
urlpatterns += solid_i18n_patterns('', url(r'^(?P<url>.*/)$', views.flatpage,
                                           name='html_pages'))

# XXX: Remove after old.compsciclub.ru termination
from django.conf.urls import handler404
handler404 = 'csclub.views.custom_page_not_found'
