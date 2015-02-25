from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from django.contrib import admin

from index.views import IndexView, AlumniView, TeachersView, RobotsView
from users.views import LoginView, LogoutView, TeacherDetailView, \
    UserDetailView, UserUpdateView, ICalClassesView, ICalAssignmentsView, \
    ICalEventsView, UserSearchJSONView, UserSearchView #, StudentInfoUpdateView
from textpages.views import TextpageOpenView, TextpageStudentView, \
    CustomTextpageOpenView
from learning.views import \
    TimetableTeacherView, TimetableStudentView, \
    CalendarTeacherView, CalendarStudentView, CalendarFullView, \
    CourseVideoListView, \
    CourseTeacherListView, \
    CourseStudentListView, \
    SemesterListView, CourseDetailView, CourseUpdateView, \
    CourseOfferingDetailView, \
    CourseOfferingEditDescrView, \
    CourseOfferingNewsCreateView, \
    CourseOfferingNewsUpdateView, \
    CourseOfferingNewsDeleteView, \
    CourseOfferingEnrollView, CourseOfferingUnenrollView, \
    CourseClassDetailView, \
    CourseClassCreateView, \
    CourseClassUpdateView, \
    CourseClassDeleteView, \
    CourseClassAttachmentDeleteView, \
    VenueListView, VenueDetailView, \
    AssignmentStudentListView, AssignmentTeacherListView, \
    AssignmentTeacherDetailView, ASStudentDetailView, ASTeacherDetailView, \
    AssignmentCreateView, AssignmentUpdateView, AssignmentDeleteView, \
    MarksSheetTeacherView, MarksSheetTeacherCSVView, \
    MarksSheetTeacherDispatchView, \
    NonCourseEventDetailView


admin.autodiscover()

urlpatterns = patterns('',
    url(r'^robots\.txt$', RobotsView.as_view(), name='robotstxt'),
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^syllabus/$', TextpageOpenView.as_view(), name='syllabus'),
    url(r'^orgs/$', TextpageOpenView.as_view(), name='orgs'),
    url(r'^teachers/$', TeachersView.as_view(), name='teachers'),
    url(r'^teachers/(?P<pk>\d+)/$', TeacherDetailView.as_view(),
        name='teacher_detail'),
    url(r'^users/(?P<pk>\d+)/$', UserDetailView.as_view(),
        name='user_detail'),
    url(r'^users/(?P<pk>\d+)/csc_classes.ics', ICalClassesView.as_view(),
        name='user_ical_classes'),
    url(r'^users/(?P<pk>\d+)/csc_assignments.ics',
        ICalAssignmentsView.as_view(),
        name='user_ical_assignments'),
    url(r'^csc_events.ics', ICalEventsView.as_view(),
        name='ical_events'),
    url(r'^users/(?P<pk>\d+)/edit$', UserUpdateView.as_view(),
        name='user_update'),
    # url(r'^student-info/(?P<pk>\d+)/edit$', StudentInfoUpdateView.as_view(),
    #     name='student_info_update'),
    url(r'^alumni/$', AlumniView.as_view(), name='alumni'),
    url(r'^news/', include('news.urls')),
    url(r'^enrollment/$', TextpageOpenView.as_view(), name='enrollment'),
    url(r'^contacts/$', TextpageOpenView.as_view(), name='contacts'),
    url(r'^online/$', TextpageOpenView.as_view(), name='online'),
    url(r'^lectures/$', TextpageOpenView.as_view(), name='lectures'),
    url(r'^videos/$', CourseVideoListView.as_view(), name='course_video_list'),

    url(r'^learning/$',
        RedirectView.as_view(pattern_name=settings.LEARNING_BASE),
        name='learning_base'),
    url(r'^learning/courses/$', CourseStudentListView.as_view(),
        name='course_list_student'),
    url(r'^learning/assignments/$', AssignmentStudentListView.as_view(),
        name='assignment_list_student'),
    url(r'^learning/assignments/(?P<pk>\d+)/$', ASStudentDetailView.as_view(),
        name='a_s_detail_student'),
    url(r'^learning/timetable/$', TimetableStudentView.as_view(),
        name='timetable_student'),
    url(r'^learning/calendar/$', CalendarStudentView.as_view(),
        name='calendar_student'),
    url(r'^learning/full-calendar/$', CalendarFullView.as_view(),
        name='calendar_full_student'),
    url(r'^learning/useful/$', TextpageStudentView.as_view(),
        name='useful_stuff'),

    url(r'^teaching/$',
        RedirectView.as_view(pattern_name=settings.TEACHING_BASE),
        name='teaching_base'),
    url(r'^teaching/timetable/$', TimetableTeacherView.as_view(),
        name='timetable_teacher'),
    url(r'^teaching/calendar/$', CalendarTeacherView.as_view(),
        name='calendar_teacher'),
    url(r'^teaching/full-calendar/$', CalendarFullView.as_view(),
        name='calendar_full_teacher'),
    url(r'^teaching/courses/$', CourseTeacherListView.as_view(),
        name='course_list_teacher'),
    url(r'^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/classes/add$',
        CourseClassCreateView.as_view(),
        name='course_class_add'),
    url(r'^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/classes/(?P<pk>\d+)/edit$',
        CourseClassUpdateView.as_view(),
        name='course_class_edit'),
    url(r'^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/classes/(?P<class_pk>\d+)/attachments/(?P<pk>\d+)/delete$',
        CourseClassAttachmentDeleteView.as_view(),
        name='course_class_attachment_delete'),
    url(r'^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/classes/(?P<pk>\d+)/delete$',
        CourseClassDeleteView.as_view(),
        name='course_class_delete'),
    url(r'^teaching/assignments/(?P<pk>\d+)/$',
        AssignmentTeacherDetailView.as_view(),
        name='assignment_detail_teacher'),
    url(r'^teaching/assignments/$',
        AssignmentTeacherListView.as_view(),
        name='assignment_list_teacher'),
    url(r'^teaching/assignments/submissions/(?P<pk>\d+)/$',
        ASTeacherDetailView.as_view(),
        name='a_s_detail_teacher'),
    url(r'^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/assignments/add$',
        AssignmentCreateView.as_view(),
        name='assignment_add'),
    url(r'^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/assignments/(?P<pk>\d+)/edit$',
        AssignmentUpdateView.as_view(),
        name='assignment_edit'),
    url(r'^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/assignments/(?P<pk>\d+)/delete$',
        AssignmentDeleteView.as_view(),
        name='assignment_delete'),
    url(r'^teaching/marks/$',
        MarksSheetTeacherDispatchView.as_view(),
        name='markssheet_teacher_dispatch'),
    url(r'^teaching/marks/(?P<course_slug>[-\w]+)/(?P<semester_year>\d+)-(?P<semester_type>\w+)/$',
        MarksSheetTeacherView.as_view(),
        name='markssheet_teacher'),
    url(r'^teaching/marks/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)\.csv$',
        MarksSheetTeacherCSVView.as_view(),
        name='markssheet_teacher_csv'),

    url(r"^courses/$", SemesterListView.as_view(),
        name="course_list"),
    url(r"^courses/(?P<slug>[-\w]+)/$", CourseDetailView.as_view(),
        name="course_detail"),
    url(r"^courses/(?P<slug>[-\w]+)/edit$", CourseUpdateView.as_view(),
        name="course_edit"),

    url(r"^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/$",
        CourseOfferingDetailView.as_view(),
        name="course_offering_detail"),
    url(r"^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/edit-descr$",
        CourseOfferingEditDescrView.as_view(),
        name="course_offering_edit_descr"),
    url(r"^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/news/add$",
        CourseOfferingNewsCreateView.as_view(),
        name="course_offering_news_create"),
    url(r"^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/news/(?P<pk>\d+)/edit$",
        CourseOfferingNewsUpdateView.as_view(),
        name="course_offering_news_update"),
    url(r"^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/news/(?P<pk>\d+)/delete$",
        CourseOfferingNewsDeleteView.as_view(),
        name="course_offering_news_delete"),
    url(r"^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/enroll$",
        CourseOfferingEnrollView.as_view(),
        name="course_offering_enroll"),
    url(r"^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/unenroll$",
        CourseOfferingUnenrollView.as_view(),
        name="course_offering_unenroll"),
    url(r"^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/classes/(?P<pk>\d+)/$",
        CourseClassDetailView.as_view(),
        name="class_detail"),

    url(r'^staff/course-marks/$',
        MarksSheetTeacherDispatchView.as_view(is_for_staff=True),
        name='course_markssheet_staff_dispatch'),
    url(r'^staff/course-marks/(?P<course_slug>[-\w]+)/(?P<semester_year>\d+)-(?P<semester_type>\w+)/$',
        MarksSheetTeacherView.as_view(is_for_staff=True),
        name='course_markssheet_staff'),
    url(r'^staff/user-search/$',
        UserSearchView.as_view(),
        name='user_search'),
    url(r'^staff/user-search.json$',
        UserSearchJSONView.as_view(),
        name='user_search_json'),

    url(r"^venues/$", VenueListView.as_view(),
        name="venue_list"),
    url(r"^venues/(?P<pk>\d+)/$", VenueDetailView.as_view(),
        name="venue_detail"),

    url(r"^events/(?P<pk>\d+)/$", NonCourseEventDetailView.as_view(),
        name="non_course_event_detail"),

    url(r'^pages/(?P<slug>[-\w]+)$', CustomTextpageOpenView.as_view(),
        name='custom_text_page'),

    url(r'^library/', include("library.urls")),

    url(r'^login/$', LoginView.as_view(), name='login'),
    url(r'^logout/$', LogoutView.as_view(), name='logout'),

    url(r'^users/password_change$',
        'django.contrib.auth.views.password_change',
        {'post_change_redirect': 'password_change_complete'},
        name='password_change'),
    url(r'^users/password_change/done$',
        'django.contrib.auth.views.password_change_done',
        name='password_change_complete'),
    url(r'^users/password_reset$',
       'django.contrib.auth.views.password_reset',
       {'post_reset_redirect' : 'password_reset_done'},
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

    url(r'^narnia/', include(admin.site.urls)),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += patterns('', url(r'^rosetta/', include('rosetta.urls')))
