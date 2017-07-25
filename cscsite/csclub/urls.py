from django.conf import settings
from django.conf.urls import include, url
from solid_i18n.urls import solid_i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from loginas import urls as loginas_urls

from ajaxuploader.views import AjaxProfileImageUploader
from htmlpages import views

from core.views import MarkdownHowToHelpView, robots
from users.views import LoginView, LogoutView, \
    UserDetailView, UserUpdateView, ICalClassesView, ICalAssignmentsView, \
    ICalEventsView, UserReferenceCreateView, UserReferenceDetailView
from learning.views import InternationalSchoolsListView
from learning.urls import course_patterns, course_offering_patterns, \
    student_section_patterns, teaching_section_patterns, venues_patterns
from core.views import MarkdownRenderView
from csclub.views import CalendarClubScheduleView, IndexView, TeachersView, \
    TeacherDetailView, AsyncEmailRegistrationView, ClubClassesFeed

admin.autodiscover()

urlpatterns = solid_i18n_patterns(
    url(r'^$', IndexView.as_view(), name='index'),
    # TODO: Remove this link as a stale in a while
    url(r'^comment-the-right-way/$', MarkdownHowToHelpView.as_view(),
        name='comment_the_right_way'),
    url(r'^commenting-the-right-way/$', MarkdownHowToHelpView.as_view(),
        name='commenting_the_right_way'),
    course_patterns,
    course_offering_patterns,

    url(r'^profile-update-image/$', AjaxProfileImageUploader.as_view(),
        name="profile_update_image"),
    # Schedule
    url(r"^schedule/$", CalendarClubScheduleView.as_view(),
        name="public_schedule"),
    url(r"^schedule/classes.ics$", ClubClassesFeed(),
        name="public_schedule_classes_ics"),
    # Registration
    url(r'^register/$', AsyncEmailRegistrationView.as_view(),
        name='registration_register'),
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
        auth_views.password_change,
        {'post_change_redirect': 'password_change_complete'},
        name='password_change'),
    url(r'^users/password_change/done$',
        auth_views.password_change_done,
        name='password_change_complete'),
    url(r'^users/password_reset$',
        auth_views.password_reset,
        {'post_reset_redirect': 'password_reset_done',
         'email_template_name': 'emails/password_reset.html'},
        name='password_reset'),
    url(r'^users/password_reset/done$',
        auth_views.password_reset_done,
        name='password_reset_done'),
    url(r'^users/reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        auth_views.password_reset_confirm,
        {'post_reset_redirect': 'password_reset_complete'},
        name='password_reset_confirm'),
    url(r'^users/reset/done$',
        auth_views.password_reset_complete,
        name='password_reset_complete'),
)

urlpatterns += [
    url(r'^robots\.txt$', robots, name='robotstxt'),
    url(r'^logout/$', LogoutView.as_view(permanent=False), name='logout'),
    url(r'^tools/markdown/preview/$',
        MarkdownRenderView.as_view(),
        name='render_markdown'),

    url(r'^notifications/', include("notifications.urls")),

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
    url(r'^users/(?P<pk>\d+)/edit$', UserUpdateView.as_view(),
        name='user_update'),

    student_section_patterns,
    teaching_section_patterns,
    venues_patterns,

    url(r'^narnia/', include(admin.site.urls)),
    url(r'^narnia/', include(loginas_urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += [url(r'^rosetta/', include('rosetta.urls'))]

if settings.DEBUG:
    import debug_toolbar
    from django.views.defaults import page_not_found, bad_request, \
        permission_denied, server_error
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]

    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        url(r'^400/$', bad_request,
            kwargs={'exception': Exception("Page not Found")}),
        url(r'^403/$', permission_denied,
            kwargs={'exception': Exception("Page not Found")}),
        url(r'^404/$', page_not_found,
            kwargs={'exception': Exception("Page not Found")}),
        url(r'^500/$', server_error,
            kwargs={'exception': Exception("Page not Found")}),
    ]

# Note: htmlpages should be the last one
urlpatterns += solid_i18n_patterns(url(r'^(?P<url>.*/)$', views.flatpage,
                                       name='html_pages'))

# XXX: Remove after old.compsciclub.ru termination
from django.conf.urls import handler404
handler404 = 'csclub.views.custom_page_not_found'
