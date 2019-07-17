from django.conf import settings
from django.conf.urls import include
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path
from django.views.generic import RedirectView, TemplateView
from loginas import urls as loginas_urls
from registration.backends.default.views import ActivationView, \
    ResendActivationView

from announcements.views import AnnouncementTagAutocomplete, \
    AnnouncementDetailView
from compscicenter_ru import views
from core.views import MarkdownRenderView, MarkdownHowToHelpView
from htmlpages.views import flatpage
from users.views import TeacherDetailView

admin.autodiscover()

urlpatterns = i18n_patterns(
    path('alumni/', views.AlumniView.as_view(), name='alumni'),
    path('alumni/<str:area>/', views.AlumniView.as_view(), name='alumni_by_area'),
    prefix_default_language=False
)


urlpatterns += [
    path('', views.IndexView.as_view(), name='index'),
    path('robots.txt', TemplateView.as_view(template_name="compscicenter_ru/robots.txt", content_type="text/plain"), name='robots_txt'),
    path('open-nsk/', TemplateView.as_view(template_name='open_nsk.html'), name='open_nsk'),
    # About section
    path('history/', TemplateView.as_view(template_name='compscicenter_ru/history.html'), name='history'),
    path('team/', views.TeamView.as_view(), name='team'),
    path('teachers/', views.TeachersView.as_view(), name='teachers'),
    path('teachers/<int:pk>/', TeacherDetailView.as_view(), name='teacher_detail'),
    path('testimonials/', views.TestimonialsListView.as_view(), name='testimonials'),
    # Editing courses/
    path('tools/markdown/preview/', MarkdownRenderView.as_view(), name='render_markdown'),
    path('commenting-the-right-way/', MarkdownHowToHelpView.as_view(), name='commenting_the_right_way'),
    # TODO: move redirect to nginx?
    path('pages/questions/', RedirectView.as_view(url='/enrollment/program/', permanent=True)),
    re_path(r'^(?P<year>20[0-9]{2})/$', views.AlumniHonorBoardView.as_view(), name='alumni_honor'),
    # Programs
    path('syllabus/', RedirectView.as_view(url='/syllabus/on-campus/', permanent=False)),
    path('syllabus/on-campus/', views.OnCampusProgramsView.as_view(), name='on_campus_programs'),
    path('syllabus/on-campus/<slug:discipline_code>/', views.OnCampusProgramDetailView.as_view(), name='on_campus_program_detail'),
    path('syllabus/distance/', views.DistanceProgramView.as_view(), name='distance_program'),

    path('enrollment/', RedirectView.as_view(url='/application/')),
    path('enrollment/checklist/', views.EnrollmentChecklistView.as_view(), name='enrollment_checklist'),
    path('enrollment/program/', views.EnrollmentPreparationProgramView.as_view(), name='enrollment_preparation_program'),
    path('faq/', views.QAListView.as_view(), name='faq'),
    # Online education
    path('', include('online_courses.urls')),
    path('videos/', views.CourseVideoListView.as_view(), name='video_list'),

    path('students/<int:student_id>/', views.StudentProfileView.as_view(), name='student_profile'),
    path('', include('auth.urls')),
    path('', include('users.urls')),

    path('api/', include('api.frontend_urls')),

    path('courses/', views.CourseOfferingsView.as_view(), name="course_list"),
    # Place tags-autocomplete under `announcements` namespace
    path("", include(([
        path("announcements/tags-autocomplete/", AnnouncementTagAutocomplete.as_view(), name="tags_autocomplete"),
    ], "announcements"))),
    path('projects/', views.ProjectsListView.as_view(), name="public_projects"),
    path('', include('publications.urls')),

    path('', include('courses.urls')),

    path('', include('admission.urls_application')),

    path('narnia/', admin.site.urls),
    path('narnia/', include(loginas_urls)),
    path('narnia/django-rq/', include('django_rq.urls')),
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

urlpatterns += i18n_patterns(re_path(r'^pages/(?P<url>.*/)$', flatpage, name='html_pages'), prefix_default_language=False)
urlpatterns += [
    path('policy/', flatpage, {'url': '/policy/'}, name="policy_html_page"),
    path('<slug:slug>/', AnnouncementDetailView.as_view(), name="announcement_detail"),
]
