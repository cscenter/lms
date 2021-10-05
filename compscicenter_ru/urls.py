from django.apps import apps
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path
from django.views.generic import RedirectView, TemplateView

from announcements.views import AnnouncementDetailView
from compscicenter_ru import views
from core.views import MarkdownHowToHelpView, MarkdownRenderView
from courses.urls import RE_COURSE_PUBLIC_URI
from htmlpages.views import flatpage

admin.autodiscover()

urlpatterns = i18n_patterns(
    path('alumni/', views.AlumniView.as_view(), name='alumni'),
    path('alumni/<str:area>/', views.AlumniView.as_view(), name='alumni_by_area'),
    prefix_default_language=False
)

urlpatterns += [
    path('', views.IndexView.as_view(), name='index'),
    path('robots.txt', TemplateView.as_view(template_name="compscicenter_ru/robots.txt", content_type="text/plain"), name='robots_txt'),
    path('stayhome/', TemplateView.as_view(template_name='compscicenter_ru/stayhome.html'), name='stay_home'),
    path('fund/', TemplateView.as_view(template_name='compscicenter_ru/fund.html'), name='fund'),
    # About section
    path('history/', TemplateView.as_view(template_name='compscicenter_ru/history.html'), name='history'),
    path('team/', views.TeamView.as_view(), name='team'),
    path('teachers/', views.TeachersView.as_view(), name='teachers'),
    path('teachers/<int:pk>/', views.TeacherDetailView.as_view(), name='teacher_detail'),
    path('testimonials/', views.TestimonialsListView.as_view(), name='testimonials'),
    path('students/<int:student_id>/', views.GraduateProfileView.as_view(), name='student_profile'),
    # TODO: move redirect to nginx?
    path('pages/questions/', RedirectView.as_view(url='/enrollment/program/', permanent=True)),
    re_path(r'^(?P<year>20[0-9]{2})/$', views.AlumniHonorBoardView.as_view(), name='alumni_honor'),
    path('partners/', include([
        path('itmo/', TemplateView.as_view(template_name='compscicenter_ru/partners/itmo.html'), name='partners_itmo'),
        path('mkn-spbgu/', TemplateView.as_view(template_name='compscicenter_ru/partners/mkn-spbgu.html'), name='partners_mkn_spbgu'),
    ])),
    # Programs
    path('syllabus/', include([
        path('', views.OnCampusProgramsView.as_view(), name='syllabus_list'),
        path('on-campus/', RedirectView.as_view(url='/syllabus/', permanent=False)),  # old urls
        path('<slug:discipline_code>/', views.OnCampusProgramDetailView.as_view(), name='syllabus_program_detail'),
        path('distance/', views.DistanceProgramView.as_view(), name='distance_program'),
    ])),
    # Admission
    path('enrollment/', RedirectView.as_view(url='/application/')),
    path('enrollment/checklist/', views.EnrollmentChecklistView.as_view(), name='enrollment_checklist'),
    path('enrollment/program/', views.EnrollmentPreparationProgramView.as_view(), name='enrollment_preparation_program'),
    path('faq/', views.QAListView.as_view(), name='faq'),
    path('', include('application.urls')),
    path('', include('admission.urls_appointment')),
    # Online education
    path('', include('online_courses.urls')),
    path('videos/', views.CourseVideoListView.as_view(), name='video_list'),

    path('api/', include('compscicenter_ru.api.urls')),

    path('', include('publications.urls')),

    path("courses/", include([
        path("", views.CourseOfferingsView.as_view(), name="course_list"),
        path("<slug:course_slug>/", views.MetaCourseDetailView.as_view(), name="meta_course_detail"),
        re_path(RE_COURSE_PUBLIC_URI, include([
            path("", views.CourseDetailView.as_view(), name="course_detail"),
            re_path(r"^(?P<tab>classes|about)/$", views.CourseDetailView.as_view(), name="course_detail_with_active_tab"),
            path("classes/<int:pk>/", views.CourseClassDetailView.as_view(), name="class_detail"),
        ]))
    ])),

    # Used in admin interface
    path('tools/markdown/preview/', MarkdownRenderView.as_view(), name='render_markdown'),
    path('commenting-the-right-way/', MarkdownHowToHelpView.as_view(), name='commenting_the_right_way'),
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
    re_path(r'^pages/(?P<url>.*/)$', flatpage, name='html_pages'),
    prefix_default_language=False)
urlpatterns += [
    path('policy/', flatpage, {'url': '/policy/'}, name="policy_html_page"),
    path('<slug:slug>/', AnnouncementDetailView.as_view(), name="announcement_detail"),
]
