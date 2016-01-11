from django.conf import settings
from django.conf.urls import url
from django.views.generic.base import RedirectView

from learning.settings import LEARNING_BASE, TEACHING_BASE
from .views import \
    TimetableTeacherView, TimetableStudentView, \
    CalendarTeacherView, CalendarStudentView, CalendarFullView, \
    CourseVideoListView, \
    CourseTeacherListView, \
    CourseStudentListView, \
    CoursesListView, CourseDetailView, CourseUpdateView, \
    CourseOfferingDetailViewContext, \
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
    AssignmentAttachmentDeleteView, \
    MarksSheetTeacherView, MarksSheetTeacherCSVView, \
    MarksSheetTeacherImportCSVFromStepicView, \
    MarksSheetTeacherImportCSVFromYandexView, \
    MarksSheetTeacherDispatchView, \
    NonCourseEventDetailView, OnlineCoursesListView, \
    AssignmentAttachmentDownloadView

urlpatterns = [
    url(r'^online/$', OnlineCoursesListView.as_view(), name='onlinecourses_list'),
    url(r'^videos/$', CourseVideoListView.as_view(), name='course_video_list'),

    url(r'^learning/$',
        RedirectView.as_view(pattern_name=LEARNING_BASE, permanent=True),
        name='learning_base'),
    url(r'^learning/courses/$', CourseStudentListView.as_view(),
        name='course_list_student'),
    url(r'^learning/assignments/$', AssignmentStudentListView.as_view(),
        name='assignment_list_student'),
    url(r'^learning/assignments/(?P<pk>\d+)/$', ASStudentDetailView.as_view(),
        name='a_s_detail_student'),
    url(r'^assignments/attachments/(?P<sid>[-\w]+)/$',
        AssignmentAttachmentDownloadView.as_view(),
        name='assignment_attachments_download'),
    url(r'^learning/timetable/$', TimetableStudentView.as_view(),
        name='timetable_student'),
    url(r'^learning/calendar/$', CalendarStudentView.as_view(),
        name='calendar_student'),
    url(r'^learning/full-calendar/$', CalendarFullView.as_view(),
        name='calendar_full_student'),

    url(r'^teaching/$',
        RedirectView.as_view(pattern_name=TEACHING_BASE, permanent=True),
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
    url(r'^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/assignments/(?P<assignment_pk>\d+)/attachments/(?P<pk>\d+)/delete$',
        AssignmentAttachmentDeleteView.as_view(),
        name='assignment_attachment_delete'),
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
    url(r'^teaching/marks/(?P<course_offering_pk>\d+)/import/stepic$',
        MarksSheetTeacherImportCSVFromStepicView.as_view(),
        name='markssheet_teacher_csv_import_stepic'),
    url(r'^teaching/marks/(?P<course_offering_pk>\d+)/import/yandex$',
        MarksSheetTeacherImportCSVFromYandexView.as_view(),
        name='markssheet_teacher_csv_import_yandex'),

    url(r"^courses/$", CoursesListView.as_view(),
        name="course_list"),
    url(r"^courses/(?P<slug>[-\w]+)/$", CourseDetailView.as_view(),
        name="course_detail"),
    url(r"^courses/(?P<slug>[-\w]+)/edit$", CourseUpdateView.as_view(),
        name="course_edit"),

    url(r"^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/$",
        CourseOfferingDetailViewContext.as_view(),
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

    url(r"^venues/$", VenueListView.as_view(),
        name="venue_list"),
    url(r"^venues/(?P<pk>\d+)/$", VenueDetailView.as_view(),
        name="venue_detail"),

    url(r"^events/(?P<pk>\d+)/$", NonCourseEventDetailView.as_view(),
        name="non_course_event_detail"),
]
