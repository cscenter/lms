from django.apps import apps
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path
from django.views.generic import TemplateView

from compsciclub_ru.views import (
    RegistrationClosedView, CalendarClubScheduleView, ClubClassesFeed,
    CourseClassDetailView, CourseDetailView, CoursesListView, IndexView,
    MetaCourseDetailView, TeacherDetailView, TeachersView
)
from core.views import MarkdownHowToHelpView, MarkdownRenderView
from courses.urls import RE_COURSE_PUBLIC_URI, RE_COURSE_URI
from htmlpages import views
from international_schools.views import InternationalSchoolsListView
from learning.views import (
    CourseEnrollView, CourseNewsNotificationUpdate, CourseUnenrollView, EventDetailView
)

admin.autodiscover()

urlpatterns = i18n_patterns(
    path('', IndexView.as_view(), name='index'),

    path('register/', RegistrationClosedView.as_view(), name='registration_register'),
    path('', include('registration.backends.default.urls')),
    path('', include('auth.urls')),

    path("schedule/", CalendarClubScheduleView.as_view(), name="public_schedule"),
    path("schedule/classes.ics", ClubClassesFeed(), name="public_schedule_classes_ics"),

    path("courses/", include([
        path("", CoursesListView.as_view(), name="course_list"),
        path("<slug:course_slug>/", MetaCourseDetailView.as_view(), name="meta_course_detail"),
        re_path(RE_COURSE_PUBLIC_URI, include([
            path("", CourseDetailView.as_view(), name="course_detail"),
            re_path(r"^(?P<tab>classes|about|news)/$", CourseDetailView.as_view(), name="course_detail_with_active_tab"),
            path("classes/<int:pk>/", CourseClassDetailView.as_view(), name="class_detail"),
        ])),
    ])),
    path('', include('courses.urls')),

    path('teachers/', TeachersView.as_view(), name='teachers'),
    re_path(r'^teachers/(?P<pk>\d+)/$', TeacherDetailView.as_view(), name='teacher_detail'),
    path("schools/", InternationalSchoolsListView.as_view(), name="international_schools_list"),

    prefix_default_language=False
)

# Placing this urls under `admin` namespace needs a lot of customization
if apps.is_installed('django_rq'):
    urlpatterns += [path('narnia/django-rq/', include('django_rq.urls'))]

urlpatterns += [
    path('robots.txt', TemplateView.as_view(template_name="compsciclub_ru/robots.txt", content_type="text/plain"), name='robots_txt'),
    path('tools/markdown/preview/', MarkdownRenderView.as_view(), name='render_markdown'),
    path('commenting-the-right-way/', MarkdownHowToHelpView.as_view(), name='commenting_the_right_way'),

    path('notifications/', include("notifications.urls")),

    path('', include('users.urls')),

    path('teaching/', include('learning.teaching.urls')),
    path('learning/', include('learning.study.urls')),
    path('api/', include('learning.api.urls')),
    path("events/<int:pk>/", EventDetailView.as_view(), name="non_course_event_detail"),

    path("courses/", include([
        re_path(RE_COURSE_URI, include([
            path("enroll/", CourseEnrollView.as_view(), name="course_enroll"),
            path("unenroll/", CourseUnenrollView.as_view(), name="course_leave"),
            path("news/notifications/", CourseNewsNotificationUpdate.as_view(), name="course_news_notifications_read"),
        ])),
    ])),

    path('narnia/', admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    from django.conf.urls import handler400, handler403, handler404, handler500
    urlpatterns += [
        path('400/', handler400, kwargs={'exception': Exception("400")}),
        path('403/', handler403, kwargs={'exception': Exception("403")}),
        path('404/', handler404, kwargs={'exception': Exception("404")}),
        path('500/', handler500),
    ]
    if apps.is_installed('debug_toolbar'):
        import debug_toolbar
        urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
    if apps.is_installed('rosetta'):
        urlpatterns += [path('rosetta/', include('rosetta.urls'))]

urlpatterns += i18n_patterns(
    re_path(r'^(?P<url>.*/)$', views.flatpage, name='html_pages'),
    prefix_default_language=False
)
