from django.conf.urls import include, url

from courses.views import CourseNewsCreateView, CourseNewsUpdateView, \
    CourseNewsDeleteView, \
    MetaCourseDetailView, MetaCourseUpdateView, CourseClassDetailView, \
    CourseClassCreateView, CourseClassUpdateView, \
    CourseClassAttachmentDeleteView, CourseClassDeleteView
from courses.views.course import CourseDetailView, CourseEditView
from learning.enrollment.views import CourseEnrollView, CourseUnenrollView
from learning.views.course_views import CourseNewsUnreadNotificationsView, \
    CourseStudentsView
from .views import \
    CourseVideoListView, \
    VenueListView, VenueDetailView, \
    AssignmentCreateView, AssignmentUpdateView, AssignmentDeleteView, \
    AssignmentAttachmentDeleteView, \
    EventDetailView

meta_course_patterns = url(
    r"^courses/", include([
        url(r"^(?P<slug>[-\w]+)/$", MetaCourseDetailView.as_view(),
            name="meta_course_detail"),
        url(r"^(?P<slug>[-\w]+)/edit$", MetaCourseUpdateView.as_view(),
            name="meta_course_edit"),
    ]))

# TODO: dynamically generate city_code regex part
course_patterns = url(
    r"^courses/(?P<course_slug>[-\w]+)/(?P<city_code>nsk|kzn|spb|)(?P<city_delimiter>/?)(?P<semester_slug>[-\w]+)/", include([
        # TODO: Ещё раз проверить, что во всех вьюхах учитывается city_code
        # Course offering
        url(r"^$", CourseDetailView.as_view(),
            name="course_detail"),
        url(r"^(?P<tab>news|assignments|classes|about|contacts|reviews)/$",
            CourseDetailView.as_view(),
            name="course_detail_with_active_tab"),
        url(r"^students/$",
            CourseStudentsView.as_view(),
            name="course_students"),
        url(r"^edit$", CourseEditView.as_view(),
            name="course_update"),
        # Enroll/Unenroll
        url(r"^enroll$",
            CourseEnrollView.as_view(),
            name="course_enroll"),
        url(r"^unenroll$",
            CourseUnenrollView.as_view(),
            name="course_leave"),
        # News
        url(r"^news/", include([
            url(r"^add$",
                CourseNewsCreateView.as_view(),
                name="course_news_create"),
            url(r"^(?P<pk>\d+)/edit$",
                CourseNewsUpdateView.as_view(),
                name="course_news_update"),
            url(r"^(?P<pk>\d+)/delete$",
                CourseNewsDeleteView.as_view(),
                name="course_news_delete"),
            url(r"^(?P<news_pk>\d+)/stats$",
                CourseNewsUnreadNotificationsView.as_view(),
                name="course_news_unread"),
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

venues_patterns = url(
    r'^venues/', include([
        url(r"^$", VenueListView.as_view(), name="venue_list"),
        url(r"^(?P<pk>\d+)/$", VenueDetailView.as_view(), name="venue_detail"),
    ]))

urlpatterns = [
    url(r'^videos/$', CourseVideoListView.as_view(), name='course_video_list'),

    venues_patterns,

    meta_course_patterns,

    course_patterns,

    url(r'^learning/', include('learning.studying.urls')),

    url(r'^teaching/', include('learning.teaching.urls')),

    url(r"^events/(?P<pk>\d+)/$", EventDetailView.as_view(),
        name="non_course_event_detail"),
]
