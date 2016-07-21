from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views

from ajaxuploader.views import AjaxProfileImageUploader
from core.views import MarkdownRenderView
from cscenter.views import QAListView, TestimonialsListView, TeachersView
from htmlpages import views
from index.views import IndexView, AlumniView, RobotsView, \
    UnsubscribeYaProxyView, EnrollmentApplicationCallback, AlumniByYearView
from learning.views import \
    MarksSheetTeacherView, MarksSheetTeacherDispatchView, UsefulListView
from staff.views import ExportsView, StudentsDiplomasView, \
    StudentsDiplomasCSVView, \
    StudentSearchJSONView, StudentSearchView, \
    TotalStatisticsView, \
    ProgressReportForSemesterView, \
    ProgressReportFullView, StudentsDiplomasStatsView, HintListView
from users.views import LoginView, LogoutView, TeacherDetailView, \
    UserDetailView, UserUpdateView, ICalClassesView, ICalAssignmentsView, \
    ICalEventsView, \
    UserReferenceCreateView, UserReferenceDetailView

admin.autodiscover()

urlpatterns = [
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^robots\.txt$', RobotsView.as_view(), name='robotstxt'),
    url(r'^unsubscribe/(?P<sub_hash>[a-f0-9]{32})/',
        UnsubscribeYaProxyView.as_view(), name='unsubscribe_ya'),
    url(r'^private/enrollment_gform_callback/',
        EnrollmentApplicationCallback.as_view(), name='enrollment_gform_cb'),

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

    # TODO: refactor
    url(r'^staff/warehouse/$', HintListView.as_view(), name='staff_warehouse'),
    url(r'^staff/course-marks/$',
        MarksSheetTeacherDispatchView.as_view(is_for_staff=True),
        name='course_markssheet_staff_dispatch'),
    url(r'^staff/course-marks/(?P<city>[-\w]+)/(?P<course_slug>[-\w]+)/(?P<semester_year>\d+)-(?P<semester_type>\w+)/$',
        MarksSheetTeacherView.as_view(is_for_staff=True),
        name='course_markssheet_staff'),
    url(r'^staff/student-search/$',
        StudentSearchView.as_view(),
        name='student_search'),
    url(r'^staff/student-search.json$',
        StudentSearchJSONView.as_view(),
        name='student_search_json'),
    url(r'^staff/exports/$',
        ExportsView.as_view(),
        name='staff_exports'),
    url(r'^staff/exports/diplomas_stats/$',
        StudentsDiplomasStatsView.as_view(),
        name='staff_exports_students_diplomas_stats'),
    url(r'^staff/exports/diplomas/$',
        StudentsDiplomasView.as_view(),
        name='staff_exports_students_diplomas'),
    url(r'^staff/exports/diplomas/csv/$',
        StudentsDiplomasCSVView.as_view(),
        name='staff_exports_students_diplomas_csv'),
    url(r'^staff/exports/sheet/csv/$',
        ProgressReportFullView.as_view(output_format="csv"),
        name='staff_exports_sheet_all_students_csv'),
    url(r'^staff/exports/sheet/xlsx/$',
        ProgressReportFullView.as_view(output_format="xlsx"),
        name='staff_exports_sheet_all_students_xlsx'),

    url(r'^staff/exports/sheet/(?P<term_year>\d+)/(?P<term_type>\w+)/csv/$',
        ProgressReportForSemesterView.as_view(output_format="csv"),
        name='staff_exports_students_sheet_filter_by_semester_csv'),
    url(r'^staff/exports/sheet/(?P<term_year>\d+)/(?P<term_type>\w+)/xlsx/$',
        ProgressReportForSemesterView.as_view(output_format="xlsx"),
        name='staff_exports_students_sheet_filter_by_semester_xlsx'),

    url(r'^staff/statistics/csv/$',
        TotalStatisticsView.as_view(),
        name='staff_total_statistics_csv'),

    url(r'^library/', include("library.urls")),
    url(r'^faq/$', QAListView.as_view(), name='faq'),
    url(r'^testimonials/$', TestimonialsListView.as_view(), name='testimonials'),

    url(r'^login/$', LoginView.as_view(), name='login'),
    url(r'^logout/$', LogoutView.as_view(permanent=True), name='logout'),

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
    from django.views.defaults import page_not_found, bad_request, \
        permission_denied, server_error

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
