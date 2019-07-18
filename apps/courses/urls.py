from django.conf.urls import include
from django.urls import path, re_path

from courses import views

from courses.settings import SemesterTypes

_terms = r"|".join(slug for slug, _ in SemesterTypes.choices)
semester_slug = r"(?P<semester_year>\d{4})-(?P<semester_type>" + _terms + r")"


# FIXME: move to settings, replace with branch code (for cs center) But how? :<
RE_COURSE_URI = r"^(?P<course_slug>[-\w]+)/(?P<city_code>nsk|kzn|spb|)(?P<city_delimiter>/?)" + semester_slug + r"/"


urlpatterns = [
    path("courses/", include([
        path("<slug:course_slug>/", views.MetaCourseDetailView.as_view(), name="meta_course_detail"),
        path("<slug:course_slug>/edit", views.MetaCourseUpdateView.as_view(), name="meta_course_edit"),
        re_path(RE_COURSE_URI, include([
            path("", views.CourseDetailView.as_view(), name="course_detail"),
            re_path(r"^(?P<tab>news|assignments|classes|about|contacts|reviews)/$", views.CourseDetailView.as_view(), name="course_detail_with_active_tab"),
            path("edit", views.CourseEditView.as_view(), name="course_update"),
            path("news/", include([
                path("add", views.CourseNewsCreateView.as_view(), name="course_news_create"),
                path("<int:pk>/edit", views.CourseNewsUpdateView.as_view(), name="course_news_update"),
                path("<int:pk>/delete", views.CourseNewsDeleteView.as_view(), name="course_news_delete"),
            ])),
            path("classes/", include([
                path("<int:pk>/", views.CourseClassDetailView.as_view(), name="class_detail"),
                path("add", views.CourseClassCreateView.as_view(), name="course_class_add"),
                path("<int:pk>/edit", views.CourseClassUpdateView.as_view(), name="course_class_update"),
                path("<int:pk>/delete", views.CourseClassDeleteView.as_view(), name="course_class_delete"),
                path("<int:class_pk>/attachments/<int:pk>/delete", views.CourseClassAttachmentDeleteView.as_view(), name='course_class_attachment_delete'),
            ])),
            path('assignments/', include([
                path('add', views.AssignmentCreateView.as_view(), name='assignment_add'),
                path('<int:pk>/edit', views.AssignmentUpdateView.as_view(), name='assignment_update'),
                path('<int:pk>/delete', views.AssignmentDeleteView.as_view(), name='assignment_delete'),
                path('<int:assignment_pk>/attachments/<int:pk>/delete', views.AssignmentAttachmentDeleteView.as_view(), name='assignment_attachment_delete'),
            ])),
        ]), kwargs={"city_aware": True}),
    ])),
    path("venues/", include([
        path("", views.VenueListView.as_view(), name="venue_list"),
        path("<int:pk>/", views.VenueDetailView.as_view(), name="venue_detail"),
    ]))
]
