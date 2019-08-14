from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path
from django.views.generic import TemplateView
from loginas import urls as loginas_urls

from announcements.views import AnnouncementTagAutocomplete
from courses.urls import RE_COURSE_URI
from courses.views import CourseDetailView
from my_compscicenter_ru.views import IndexView
from core.views import MarkdownRenderView, MarkdownHowToHelpView

admin.autodiscover()


urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('robots.txt', TemplateView.as_view(template_name="my_compscicenter_ru/robots.txt", content_type="text/plain"), name='robots_txt'),
    path('api/', include('api.backend_urls')),
    path('tools/markdown/preview/', MarkdownRenderView.as_view(), name='render_markdown'),
    path('commenting-the-right-way/', MarkdownHowToHelpView.as_view(), name='commenting_the_right_way'),

    path('', include('learning.urls')),

    path("courses/", include([
        re_path(RE_COURSE_URI, include([
            path("", CourseDetailView.as_view(), name="course_detail"),
            re_path(r"^(?P<tab>news|assignments|classes|about|contacts|reviews)/$", CourseDetailView.as_view(), name="course_detail_with_active_tab"),
        ]), kwargs={"city_aware": True})
    ])),

    path("courses/", include('learning.invitation.urls')),

    path('', include('auth.urls')),
    path('', include('users.urls')),

    path('notifications/', include("notifications.urls")),
    path('staff/', include("staff.urls")),
    path('stats/', include("stats.urls")),
    path('surveys/', include("surveys.urls")),
    path('', include('projects.urls')),

    path('', include('admission.urls')),

    path('narnia/', admin.site.urls),
    path('narnia/', include(loginas_urls)),
    path('narnia/django-rq/', include('django_rq.urls')),
    # Quick fix for admin page. Better to separate projects into private/public parts
    path("", include(([
        path("announcements/tags-autocomplete/", AnnouncementTagAutocomplete.as_view(), name="tags_autocomplete"),
    ], "announcements"))),
    path('ckeditor/', include('ckeditor_uploader.urls')),
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
