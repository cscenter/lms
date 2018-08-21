from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from loginas import urls as loginas_urls

from ajaxuploader.views import AjaxProfileImageUploader
from core.views import robots, MarkdownRenderView, MarkdownHowToHelpView
from cscenter import views as cscenter_views
from htmlpages import views
from learning.views.students import UsefulListView, InternshipListView
from users.forms import UserPasswordResetForm
from users.tasks import html_email_template_name, email_template_name, \
    subject_template_name

from users.views import LoginView, LogoutView, TeacherDetailView, \
    UserDetailView, UserUpdateView, UserReferenceCreateView, UserReferenceDetailView
from learning.views.icalendar import ICalClassesView, ICalAssignmentsView, \
    ICalEventsView

admin.autodiscover()

urlpatterns = [
    url(r'^$', cscenter_views.IndexView.as_view(), name='index'),
    url(r'^open-nsk/$', cscenter_views.OpenNskView.as_view(), name='open_nsk'),
    url(r'^api/', include('api.urls')),
    url(r'^robots\.txt$', robots, name='robotstxt'),
    # Redirect from old url `/pages/questions/` to more appropriate
    url(r'^pages/questions/$',
        RedirectView.as_view(url='/enrollment/program/',
                             permanent=True)),
    url(r'^orgs/$', cscenter_views.TeamView.as_view(), name='orgs'),
    url(r'^syllabus/$', cscenter_views.SyllabusView.as_view(), name='syllabus'),
    url(r'^commenting-the-right-way/$', MarkdownHowToHelpView.as_view(),
        name='commenting_the_right_way'),

    url(r'^profile-update-image/$', AjaxProfileImageUploader.as_view(),
        name="profile_update_image"),

    url(r'^learning/useful/$', UsefulListView.as_view(), name='learning_useful'),
    url(r'^learning/internships/$', InternshipListView.as_view(),
        name='learning_internships'),


    url(r'^teachers/$', cscenter_views.TeachersView.as_view(), name='teachers'),
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
    url(r'^alumni2/$', cscenter_views.AlumniV2View.as_view(), name='alumni_v2'),
    url(r'^alumni/$', cscenter_views.AlumniView.as_view(), name='alumni'),
    url(r'^alumni/(?P<area_of_study_code>[-\w]+)/$', cscenter_views.AlumniView.as_view(),
        name='alumni_by_area_of_study'),
    url(r'^(?P<year>201[3-7])/$', cscenter_views.AlumniByYearView.as_view(),
        name='alumni_memory'),
    url(r'^(?P<year>20[0-9]{2})/$', cscenter_views.AlumniHonorBoardView.as_view(),
        name='alumni_honor'),

    url(r'^notifications/', include("notifications.urls")),
    url(r'^staff/', include("staff.urls")),

    url(r'^stats/', include("stats.urls")),

    url(r'^library/', include("library.urls")),
    url(r'^faq/$', cscenter_views.QAListView.as_view(), name='faq'),
    url(r'^testimonials/$', cscenter_views.TestimonialsListView.as_view(),
        name='testimonials'),
    url(r'^testimonials2/$',
        cscenter_views.TestimonialsListV2View.as_view(),
        name='testimonials_v2'),

    url(r'^login/$', LoginView.as_view(), name='login'),
    url(r'^logout/$', LogoutView.as_view(), name='logout'),
    url(r'^users/password_change$',
        auth_views.PasswordChangeView.as_view(),
        name='password_change'),
    url(r'^users/password_change/done$',
        auth_views.PasswordChangeDoneView.as_view(),
        name='password_change_done'),
    url(r'^users/password_reset$',
        auth_views.PasswordResetView.as_view(
            form_class=UserPasswordResetForm,
            email_template_name=email_template_name,
            html_email_template_name=html_email_template_name,
            subject_template_name=subject_template_name),
        name='password_reset'),
    url(r'^users/password_reset/done$',
        auth_views.PasswordResetDoneView.as_view(),
        name='password_reset_done'),
    url(r'^users/reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        auth_views.PasswordResetConfirmView.as_view(),
        name='password_reset_confirm'),
    url(r'^users/reset/done$',
        auth_views.PasswordResetCompleteView.as_view(),
        name='password_reset_complete'),

    url(r'^tools/markdown/preview/$', MarkdownRenderView.as_view(),
        name='render_markdown'),
    url(r"^courses/$", cscenter_views.CourseOfferingsView.as_view(), name="course_list"),
    url(r'^', include('learning.urls')),
    url(r'^', include('learning.admission.urls')),
    url(r'^', include('learning.projects.urls')),
    url(r'^narnia/', admin.site.urls),
    url(r'^narnia/', include(loginas_urls)),
    # TODO: remove after testing
    url(r'^', include('admission_test.urls')),

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
