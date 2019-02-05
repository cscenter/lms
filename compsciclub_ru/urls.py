from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from loginas import urls as loginas_urls

from compsciclub_ru.views import CalendarClubScheduleView, IndexView, \
    TeachersView, \
    TeacherDetailView, AsyncEmailRegistrationView, ClubClassesFeed, \
    CoursesListView
from core.views import MarkdownHowToHelpView, robots
from core.views import MarkdownRenderView
from htmlpages import views
from international_schools.views import InternationalSchoolsListView
from users.urls import auth_urls

admin.autodiscover()

urlpatterns = i18n_patterns(
    url(r'^$', IndexView.as_view(), name='index'),

    path('register/', AsyncEmailRegistrationView.as_view(), name='registration_register'),
    path('', include('registration.backends.default.urls')),
    path('', include(auth_urls)),

    path("schedule/", CalendarClubScheduleView.as_view(), name="public_schedule"),
    path("schedule/classes.ics", ClubClassesFeed(), name="public_schedule_classes_ics"),

    url(r"^courses/$", CoursesListView.as_view(), name="course_list"),

    path('', include('learning.enrollment.urls')),
    path('', include('courses.urls')),

    url(r'^teachers/$', TeachersView.as_view(), name='teachers'),
    url(r'^teachers/(?P<pk>\d+)/$', TeacherDetailView.as_view(), name='teacher_detail'),
    url(r"^schools/$", InternationalSchoolsListView.as_view(), name="international_schools_list"),

    prefix_default_language=False
)

urlpatterns += [
    path('robots.txt', robots, name='robots_txt'),
    path('tools/markdown/preview/', MarkdownRenderView.as_view(), name='render_markdown'),
    path('commenting-the-right-way/', MarkdownHowToHelpView.as_view(), name='commenting_the_right_way'),

    url(r'^notifications/', include("notifications.urls")),

    path('', include('users.urls')),

    path('teaching/', include('learning.teaching.urls')),
    path('learning/', include('learning.study.urls')),

    path('narnia/', admin.site.urls),
    path('narnia/', include(loginas_urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar
    from django.conf.urls import handler400, handler403, handler404, handler500
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
        path('400/', handler400, kwargs={'exception': Exception("400")}),
        path('403/', handler403, kwargs={'exception': Exception("403")}),
        path('404/', handler404, kwargs={'exception': Exception("404")}),
        path('500/', handler500),
    ]
    if 'rosetta' in settings.INSTALLED_APPS:
        urlpatterns += [path('rosetta/', include('rosetta.urls'))]

urlpatterns += i18n_patterns(
    url(r'^(?P<url>.*/)$', views.flatpage, name='html_pages'),
    prefix_default_language=False
)

handler404 = 'compsciclub_ru.views.custom_page_not_found'
