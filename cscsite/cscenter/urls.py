from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views

from ajaxuploader.views import AjaxProfileImageUploader
from core.views import RobotsView, MarkdownRenderView
from cscenter.views import IndexView, QAListView, TestimonialsListView, \
    TeachersView, AlumniView, AlumniByYearView
from htmlpages import views
from learning.views import UsefulListView

from users.views import LoginView, LogoutView, TeacherDetailView, \
    UserDetailView, UserUpdateView, ICalClassesView, ICalAssignmentsView, \
    ICalEventsView, \
    UserReferenceCreateView, UserReferenceDetailView

admin.autodiscover()

urlpatterns = [
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^robots\.txt$', RobotsView.as_view(), name='robotstxt'),

    url(r'^profile-update-image/$', AjaxProfileImageUploader.as_view(),
        name="profile_update_image"),

    url(r'^learning/useful/$', UsefulListView.as_view(), name='learning_useful'),


    url(r'^teachers/$', TeachersView.as_view(), name='teachers'),
    url(r'^teachers/(?P<pk>\d+)/$', TeacherDetailView.as_view(),
        name='teacher_detail'),
    url(r'^users/(?P<pk>\d+)/$', UserDetailView.as_view(),
        name='user_detail'),
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
    # Alumni
    url(r'^alumni/$', AlumniView.as_view(), name='alumni'),
    url(r'^2016/$', AlumniByYearView.as_view(filter_by_year=2016),
        name='alumni_2016'),
    url(r'^alumni/(?P<study_program_code>[-\w]+)/$', AlumniView.as_view(),
        name='alumni_by_study_program'),

    url(r'^staff/', include("staff.urls")),

    url(r'^library/', include("library.urls")),
    url(r'^faq/$', QAListView.as_view(), name='faq'),
    url(r'^testimonials/$', TestimonialsListView.as_view(), name='testimonials'),

    url(r'^login/$', LoginView.as_view(), name='login'),
    url(r'^logout/$', LogoutView.as_view(), name='logout'),

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
        {'post_reset_redirect' : 'password_reset_complete'},
        name='password_reset_confirm'),
    url(r'^users/reset/done$',
        auth_views.password_reset_complete,
        name='password_reset_complete'),
    url(r'^tools/markdown/preview/$', MarkdownRenderView.as_view(),
        name='render_markdown'),

    url(r'^', include('learning.urls')),
    url(r'^', include('learning.admission.urls')),
    url(r'^', include('learning.projects.urls')),
    url(r'^narnia/', include(admin.site.urls)),
    url(r'^narnia/', include('loginas.urls')),
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
urlpatterns += [url(r'^(?P<url>.*/)$', views.flatpage, name='html_pages')]
