from loginas import urls as loginas_urls

from django.apps import apps
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView

from core.views import MarkdownHowToHelpView, MarkdownRenderView
from courses.views import TeacherDetailView
from info_blocks.views import InfoBlockTagAutocomplete
from library.views import BookTagAutocomplete
from lms.views import CourseOfferingsView, IndexView
from users.views import (
    CertificateOfParticipationCreateView, CertificateOfParticipationDetailView
)

admin.site.enable_nav_sidebar = False
admin.autodiscover()


urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('robots.txt', TemplateView.as_view(template_name="lms/robots.txt", content_type="text/plain"), name='robots_txt'),

    path('', include('auth.urls')),

    path('api/', include('api.urls')),
    path('api/', include('learning.api.urls')),
    path('api/', include('code_reviews.api.urls')),
    path('api/', include('stats.api_urls')),
    path('api/', include('admission.api.urls')),

    path('tools/markdown/preview/', MarkdownRenderView.as_view(), name='render_markdown'),
    path('commenting-the-right-way/', MarkdownHowToHelpView.as_view(), name='commenting_the_right_way'),

    path('', include('learning.urls')),

    path('courses/', CourseOfferingsView.as_view(), name="course_list"),
    path('', include('courses.urls')),
    path("courses/", include('learning.invitation.urls')),
    path('teachers/<int:pk>/', TeacherDetailView.as_view(), name='teacher_detail'),

    path('users/<int:student_profile_id>/reference/add/', CertificateOfParticipationCreateView.as_view(), name='student_reference_add'),
    path('users/<int:student_profile_id>/reference/<int:reference_pk>/', CertificateOfParticipationDetailView.as_view(), name='student_reference_detail'),
    path('', include('users.urls')),

    path('notifications/', include("notifications.urls")),
    path('staff/', include("staff.urls")),
    path('stats/', include("stats.urls")),
    path('surveys/', include("surveys.urls")),
    path('', include('projects.urls')),

    path('', include('admission.urls')),

    # URLs for tags autocomplete, available only for curators
    path("narnia/library/tags-autocomplete/", BookTagAutocomplete.as_view(), name="library_tags_autocomplete"),
    path("narnia/info_blocks/tags-autocomplete/", InfoBlockTagAutocomplete.as_view(), name="info_blocks_tags_autocomplete"),

    path('narnia/', admin.site.urls),
    path('narnia/', include(loginas_urls)),
    path('narnia/django-rq/', include('django_rq.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
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


if apps.is_installed('announcements'):
    from announcements.views import AnnouncementTagAutocomplete

    # URLs for tags autocomplete for announcements, specific for CS Center site
    urlpatterns += [
        path("narnia/announcements/tags-autocomplete/", AnnouncementTagAutocomplete.as_view(),
             name="announcements_tags_autocomplete"),
    ]
