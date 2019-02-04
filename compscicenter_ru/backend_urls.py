from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from loginas import urls as loginas_urls

from compscicenter_ru import views
from compscicenter_ru.views import IndexView
from core.views import MarkdownRenderView, MarkdownHowToHelpView
from users.urls import auth_urls

admin.autodiscover()


urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('api/', include('api.backend_urls')),
    path('tools/markdown/preview/', MarkdownRenderView.as_view(), name='render_markdown'),
    path('commenting-the-right-way/', MarkdownHowToHelpView.as_view(), name='commenting_the_right_way'),

    path('', include('learning.urls')),

    path('', include(auth_urls)),
    path('', include('users.urls')),

    path('notifications/', include("notifications.urls")),
    path('staff/', include("staff.urls")),
    path('stats/', include("stats.urls")),
    path('surveys/', include("surveys.urls")),

    # FIXME: тут как быть?
    path('courses/', views.CourseOfferingsView.as_view(), name="course_list"),
    # FIXME: кажется, что это публичные все ссылки? проверить вручную
    path('', include('courses.urls')),

    path('', include('learning.projects.urls')),

    path('narnia/', admin.site.urls),
    path('narnia/', include(loginas_urls)),
    # Required `is_staff` only. Mb restrict to `is_superuser`?
    path('narnia/django-rq/', include('django_rq.urls')),
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
