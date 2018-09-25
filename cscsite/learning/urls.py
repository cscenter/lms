from django.conf.urls import include, url
from django.views.generic.base import RedirectView

from learning.settings import LEARNING_BASE, TEACHING_BASE
from learning.views import CalendarTeacherFullView
from learning.views.views import CalendarStudentFullView
from .views import \
    TimetableTeacherView, TimetableStudentView, \
    CalendarTeacherView, CalendarStudentView, \
    CourseVideoListView, \
    CourseTeacherListView, \
    CourseStudentListView, \
    CoursesListView, CourseDetailView, CourseUpdateView, \
    CourseOfferingDetailView, \
    CourseClassDetailView, \
    CourseClassCreateView, \
    CourseClassUpdateView, \
    CourseClassDeleteView, \
    CourseClassAttachmentDeleteView, \
    VenueListView, VenueDetailView, \
    AssignmentTeacherListView, \
    AssignmentTeacherDetailView, StudentAssignmentTeacherDetailView, \
    AssignmentCreateView, AssignmentUpdateView, AssignmentDeleteView, \
    AssignmentAttachmentDeleteView, \
    NonCourseEventDetailView, OnlineCoursesListView, \
    AssignmentAttachmentDownloadView, AssignmentCommentUpdateView
from learning.views.gradebook import GradeBookTeacherView, \
    GradeBookTeacherDispatchView, GradeBookTeacherCSVView, \
    AssignmentGradesImportByStepikIDView, \
    AssignmentGradesImportByYandexLoginView
from learning.views.course_offering import CourseOfferingEditView, \
    CourseOfferingNewsCreateView, CourseOfferingNewsUpdateView, \
    CourseOfferingNewsDeleteView, CourseOfferingNewsUnreadNotificationsView, \
    CourseOfferingStudentsView
from learning.views.students import StudentAssignmentStudentDetailView, \
    StudentAssignmentListView, CourseOfferingEnrollView, \
    CourseOfferingUnenrollView

course_patterns = url(
    r"^courses/", include([
        url(r"^(?P<slug>[-\w]+)/$", CourseDetailView.as_view(),
            name="course_detail"),
        url(r"^(?P<slug>[-\w]+)/edit$", CourseUpdateView.as_view(),
            name="course_edit"),
    ]))

# TODO: dynamically generate city_code regex part
course_offering_patterns = url(
    r"^courses/(?P<course_slug>[-\w]+)/(?P<city_code>nsk|kzn|spb|)(?P<city_delimiter>/?)(?P<semester_slug>[-\w]+)/", include([
        # TODO: Ещё раз проверить, что во всех вьюхах учитывается city_code
        # Course offering
        url(r"^$", CourseOfferingDetailView.as_view(),
            name="course_offering_detail"),
        url(r"^(?P<tab>news|assignments|classes|about|contacts|reviews)/$",
            CourseOfferingDetailView.as_view(),
            name="course_offering_detail_with_active_tab"),
        url(r"^students/$",
            CourseOfferingStudentsView.as_view(),
            name="course_offering_students"),
        url(r"^edit$", CourseOfferingEditView.as_view(),
            name="course_offering_update"),
        # Enroll/Unenroll
        url(r"^enroll$",
            CourseOfferingEnrollView.as_view(),
            name="course_offering_enroll"),
        url(r"^unenroll$",
            CourseOfferingUnenrollView.as_view(),
            name="course_offering_unenroll"),
        # News
        url(r"^news/", include([
            url(r"^add$",
                CourseOfferingNewsCreateView.as_view(),
                name="course_offering_news_create"),
            url(r"^(?P<pk>\d+)/edit$",
                CourseOfferingNewsUpdateView.as_view(),
                name="course_offering_news_update"),
            url(r"^(?P<pk>\d+)/delete$",
                CourseOfferingNewsDeleteView.as_view(),
                name="course_offering_news_delete"),
            url(r"^(?P<news_pk>\d+)/stats$",
                CourseOfferingNewsUnreadNotificationsView.as_view(),
                name="course_offering_news_unread"),
        ])),
        # Classes
        url(r"^classes/", include([
            url(r"^(?P<pk>\d+)/$",
                CourseClassDetailView.as_view(),
                name="class_detail"),
            url(r'^add$',
                CourseClassCreateView.as_view(),
                name='course_class_add'),
            url(r'^(?P<pk>\d+)/edit$',
                CourseClassUpdateView.as_view(),
                name='course_class_update'),
            url(r'^(?P<pk>\d+)/delete$',
                CourseClassDeleteView.as_view(),
                name='course_class_delete'),
            url(r'^(?P<class_pk>\d+)/attachments/(?P<pk>\d+)/delete$',
                CourseClassAttachmentDeleteView.as_view(),
                name='course_class_attachment_delete'),
        ])),
        # Assignments
        url(r'^assignments/', include([
            url(r'^add$',
                AssignmentCreateView.as_view(),
                name='assignment_add'),
            url(r'^(?P<pk>\d+)/edit$',
                AssignmentUpdateView.as_view(),
                name='assignment_update'),
            url(r'^(?P<pk>\d+)/delete$',
                AssignmentDeleteView.as_view(),
                name='assignment_delete'),
            url(r'^(?P<assignment_pk>\d+)/attachments/(?P<pk>\d+)/delete$',
                AssignmentAttachmentDeleteView.as_view(),
                name='assignment_attachment_delete'),

        ])),
    ]), kwargs={"city_aware": True})

teaching_section_patterns = url(
    r'^teaching/', include([
        url(r'^$',
            RedirectView.as_view(pattern_name=TEACHING_BASE, permanent=True),
            name='teaching_base'),
        url(r'^timetable/$', TimetableTeacherView.as_view(),
            name='timetable_teacher'),
        url(r'^calendar/$', CalendarTeacherView.as_view(),
            name='calendar_teacher'),
        url(r'^full-calendar/$', CalendarTeacherFullView.as_view(),
            name='calendar_full_teacher'),
        url(r'^courses/$', CourseTeacherListView.as_view(),
            name='course_list_teacher'),
        url(r'^assignments/', include([
            url(r'^$',
                AssignmentTeacherListView.as_view(),
                name='assignment_list_teacher'),
            url(r'^(?P<pk>\d+)/$',
                AssignmentTeacherDetailView.as_view(),
                name='assignment_detail_teacher'),
            url(r'^submissions/(?P<pk>\d+)/$',
                StudentAssignmentTeacherDetailView.as_view(),
                name='a_s_detail_teacher'),
            url(r'^submissions/(?P<submission_pk>\d+)/comment/(?P<comment_pk>\d+)/update/$',
                AssignmentCommentUpdateView.as_view(),
                name='assignment_submission_comment_edit'),
        ])),
        url(r'^marks/', include([
            url(r'^$',
                GradeBookTeacherDispatchView.as_view(),
                name='markssheet_teacher_dispatch'),
            url(r'^(?P<city>[-\w]+)/(?P<course_slug>[-\w]+)/(?P<semester_year>\d+)-(?P<semester_type>\w+)/$',
                GradeBookTeacherView.as_view(),
                name='markssheet_teacher'),
            url(r'^(?P<city>[-\w]+)/(?P<course_slug>[-\w]+)/(?P<semester_year>\d+)-(?P<semester_type>\w+)/csv/$',
                GradeBookTeacherCSVView.as_view(),
                name='markssheet_teacher_csv'),
            url(r'^(?P<course_offering_pk>\d+)/import/stepic$',
                AssignmentGradesImportByStepikIDView.as_view(),
                name='markssheet_teacher_csv_import_stepic'),
            url(r'^(?P<course_offering_pk>\d+)/import/yandex$',
                AssignmentGradesImportByYandexLoginView.as_view(),
                name='markssheet_teacher_csv_import_yandex'),
        ])),
    ]))

student_section_patterns = url(
    r'^learning/', include([
        url(r'^$',
            RedirectView.as_view(pattern_name=LEARNING_BASE, permanent=True),
            name='learning_base'),
        url(r'^courses/$', CourseStudentListView.as_view(),
            name='course_list_student'),
        url(r'^assignments/$', StudentAssignmentListView.as_view(),
            name='assignment_list_student'),
        url(r'^assignments/(?P<pk>\d+)/$', StudentAssignmentStudentDetailView.as_view(),
            name='a_s_detail_student'),
        # TODO: learning/assignments/attachments/?
        url(r'^attachments/(?P<sid>[-\w]+)/(?P<file_name>.+)$',
            AssignmentAttachmentDownloadView.as_view(),
            name='assignment_attachments_download'),
        url(r'^timetable/$', TimetableStudentView.as_view(),
            name='timetable_student'),
        url(r'^calendar/$', CalendarStudentView.as_view(),
            name='calendar_student'),
        url(r'^full-calendar/$', CalendarStudentFullView.as_view(),
            name='calendar_full_student'),
    ]))

venues_patterns = url(
    r'^venues/', include([
        url(r"^$", VenueListView.as_view(), name="venue_list"),
        url(r"^(?P<pk>\d+)/$", VenueDetailView.as_view(), name="venue_detail"),
    ]))

urlpatterns = [
    url(r'^online/$', OnlineCoursesListView.as_view(),
        name='onlinecourses_list'),
    url(r'^videos/$', CourseVideoListView.as_view(), name='course_video_list'),

    venues_patterns,

    course_patterns,

    course_offering_patterns,

    student_section_patterns,

    teaching_section_patterns,

    url(r"^events/(?P<pk>\d+)/$", NonCourseEventDetailView.as_view(),
        name="non_course_event_detail"),
]
