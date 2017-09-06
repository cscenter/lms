from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from loginas import urls as loginas_urls

from ajaxuploader.views import AjaxProfileImageUploader
from core.views import robots, MarkdownRenderView, MarkdownHowToHelpView
from cscenter.views import IndexView, QAListView, TestimonialsListView, \
    TeachersView, AlumniView, AlumniByYearView, TeamView, SyllabusView, \
    OpenNskView, CourseOfferingsView
from htmlpages import views
from learning.views import CoursesListView
from learning.views.students import UsefulListView, InternshipListView

from users.views import LoginView, LogoutView, TeacherDetailView, \
    UserDetailView, UserUpdateView, UserReferenceCreateView, UserReferenceDetailView
from learning.views.icalendar import ICalClassesView, ICalAssignmentsView, \
    ICalEventsView

admin.autodiscover()

urlpatterns = [
    url(r'^open-nsk/$', OpenNskView.as_view(), name='open_nsk'),
    url(r'^api/', include('api.urls')),
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^robots\.txt$', robots, name='robotstxt'),
    # Redirect from old url `/pages/questions/` to more appropriate
    url(r'^pages/questions/$',
        RedirectView.as_view(url='/enrollment/program/',
                             permanent=True)),
    url(r'^orgs/$', TeamView.as_view(), name='orgs'),
    url(r'^syllabus/$', SyllabusView.as_view(), name='syllabus'),
    url(r'^commenting-the-right-way/$', MarkdownHowToHelpView.as_view(),
        name='commenting_the_right_way'),

    url(r'^profile-update-image/$', AjaxProfileImageUploader.as_view(),
        name="profile_update_image"),

    url(r'^learning/useful/$', UsefulListView.as_view(), name='learning_useful'),
    url(r'^learning/internships/$', InternshipListView.as_view(),
        name='learning_internships'),


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
    url(r'^alumni/(?P<area_of_study_code>[-\w]+)/$', AlumniView.as_view(),
        name='alumni_by_area_of_study'),
    url(r'^(?P<year>[0-9]{4})/$', AlumniByYearView.as_view(),
        name='alumni_memory'),

    url(r'^notifications/', include("notifications.urls")),
    url(r'^staff/', include("staff.urls")),

    url(r'^stats/', include("stats.urls")),

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

    url(r"^courses/$", CourseOfferingsView.as_view(), name="course_list"),
    url(r'^', include('learning.urls')),
    url(r'^', include('learning.admission.urls')),
    url(r'^', include('learning.projects.urls')),
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
            kwargs={'exception': Exception("Bad request")}),
        url(r'^403/$', permission_denied,
            kwargs={'exception': Exception("Forbidden"),
                    'template_name': "errors/403.html"}),
        url(r'^404/$', page_not_found,
            kwargs={'exception': Exception("Page not Found"),
                    'template_name': "errors/404.html"}),
        url(r'^500/$', server_error),
    ]

# Required `is_staff` only. Mb restrict to `is_superuser`?
urlpatterns += [
    url(r'^narnia/django-rq/', include('django_rq.urls')),
]

# Note: htmlpages should be the last one
urlpatterns += [url(r'^(?P<url>.*/)$', views.flatpage, name='html_pages')]
