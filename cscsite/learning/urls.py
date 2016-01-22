from django.conf import settings
from django.conf.urls import include, url
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
    StudentAssignmentListView, AssignmentTeacherListView, \
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

    url(r"^venues/$", VenueListView.as_view(),
        name="venue_list"),
    url(r"^venues/(?P<pk>\d+)/$", VenueDetailView.as_view(),
        name="venue_detail"),

    # Course urls
    url(r"^courses/$", CoursesListView.as_view(),
        name="course_list"),
    url(r"^courses/(?P<slug>[-\w]+)/$", CourseDetailView.as_view(),
        name="course_detail"),
    url(r"^courses/(?P<slug>[-\w]+)/edit$", CourseUpdateView.as_view(),
        name="course_edit"),

    # Course offering urls
    url(r"^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)", include([
        # Common pages
        url(r"^/$",
            CourseOfferingDetailViewContext.as_view(),
            name="course_offering_detail"),
        url(r"^/edit-descr$",
            CourseOfferingEditDescrView.as_view(),
            name="course_offering_edit_descr"),
        url(r"^/news/add$",
            CourseOfferingNewsCreateView.as_view(),
            name="course_offering_news_create"),
        url(r"^/news/(?P<pk>\d+)/edit$",
            CourseOfferingNewsUpdateView.as_view(),
            name="course_offering_news_update"),
        url(r"^/news/(?P<pk>\d+)/delete$",
            CourseOfferingNewsDeleteView.as_view(),
            name="course_offering_news_delete"),
        url(r"^/enroll$",
            CourseOfferingEnrollView.as_view(),
            name="course_offering_enroll"),
        url(r"^/unenroll$",
            CourseOfferingUnenrollView.as_view(),
            name="course_offering_unenroll"),
        # Classes
        url(r"^/classes", include([
            url(r"^/(?P<pk>\d+)/$",
                CourseClassDetailView.as_view(),
                name="class_detail"),
            url(r'^/add$',
                CourseClassCreateView.as_view(),
                name='course_class_add'),
            url(r'^/(?P<pk>\d+)/edit$',
                CourseClassUpdateView.as_view(),
                name='course_class_edit'),
            url(r'^/(?P<class_pk>\d+)/attachments/(?P<pk>\d+)/delete$',
                CourseClassAttachmentDeleteView.as_view(),
                name='course_class_attachment_delete'),
            url(r'^/(?P<pk>\d+)/delete$',
                CourseClassDeleteView.as_view(),
                name='course_class_delete'),
        ])),
        # Assignments
        url(r'^/assignments', include([
            url(r'^/add$',
                AssignmentCreateView.as_view(),
                name='assignment_add'),
            url(r'^/(?P<pk>\d+)/edit$',
                AssignmentUpdateView.as_view(),
                name='assignment_edit'),
            url(r'^/(?P<pk>\d+)/delete$',
                AssignmentDeleteView.as_view(),
                name='assignment_delete'),
            url(r'^/(?P<assignment_pk>\d+)/attachments/(?P<pk>\d+)/delete$',
                AssignmentAttachmentDeleteView.as_view(),
                name='assignment_attachment_delete'),

        ])),
    ])),

    # Student section
    url(r'^learning', include([
        url(r'^/$',
            RedirectView.as_view(pattern_name=LEARNING_BASE, permanent=True),
            name='learning_base'),
        url(r'^/courses/$', CourseStudentListView.as_view(),
            name='course_list_student'),
        url(r'^/assignments/$', StudentAssignmentListView.as_view(),
            name='assignment_list_student'),
        url(r'^/assignments/(?P<pk>\d+)/$', ASStudentDetailView.as_view(),
            name='a_s_detail_student'),
        # TODO: learning/assignments/attachments/?
        url(r'^/attachments/(?P<sid>[-\w]+)/$',
            AssignmentAttachmentDownloadView.as_view(),
            name='assignment_attachments_download'),
        url(r'^/timetable/$', TimetableStudentView.as_view(),
            name='timetable_student'),
        url(r'^/calendar/$', CalendarStudentView.as_view(),
            name='calendar_student'),
        url(r'^/full-calendar/$', CalendarFullView.as_view(),
            name='calendar_full_student'),
    ])),

    # Teacher section
    url(r'^teaching', include([
        url(r'^/$',
            RedirectView.as_view(pattern_name=TEACHING_BASE, permanent=True),
            name='teaching_base'),
        url(r'^/timetable/$', TimetableTeacherView.as_view(),
            name='timetable_teacher'),
        url(r'^/calendar/$', CalendarTeacherView.as_view(),
            name='calendar_teacher'),
        url(r'^/full-calendar/$', CalendarFullView.as_view(),
            name='calendar_full_teacher'),
        url(r'^/courses/$', CourseTeacherListView.as_view(),
            name='course_list_teacher'),
        url(r'^/assignments', include([
            url(r'^/$',
                AssignmentTeacherListView.as_view(),
                name='assignment_list_teacher'),
            url(r'^/(?P<pk>\d+)/$',
                AssignmentTeacherDetailView.as_view(),
                name='assignment_detail_teacher'),
            url(r'^/submissions/(?P<pk>\d+)/$',
                ASTeacherDetailView.as_view(),
                name='a_s_detail_teacher'),
        ])),
        url(r'^/marks', include([
            url(r'^/$',
                MarksSheetTeacherDispatchView.as_view(),
                name='markssheet_teacher_dispatch'),
            url(r'^/(?P<course_slug>[-\w]+)/(?P<semester_year>\d+)-(?P<semester_type>\w+)/$',
                MarksSheetTeacherView.as_view(),
                name='markssheet_teacher'),
            url(r'^/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)\.csv$',
                MarksSheetTeacherCSVView.as_view(),
                name='markssheet_teacher_csv'),
            url(r'^/(?P<course_offering_pk>\d+)/import/stepic$',
                MarksSheetTeacherImportCSVFromStepicView.as_view(),
                name='markssheet_teacher_csv_import_stepic'),
            url(r'^/(?P<course_offering_pk>\d+)/import/yandex$',
                MarksSheetTeacherImportCSVFromYandexView.as_view(),
                name='markssheet_teacher_csv_import_yandex'),
        ])),
    ])),

    url(r"^events/(?P<pk>\d+)/$", NonCourseEventDetailView.as_view(),
        name="non_course_event_detail"),


]
