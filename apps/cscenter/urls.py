from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path
from django.views.generic import RedirectView
from loginas import urls as loginas_urls

from core.views import robots, MarkdownRenderView, MarkdownHowToHelpView
from cscenter import views as cscenter_views
from htmlpages import views
from learning.studying.views import UsefulListView, InternshipListView
from courses.views import CourseVideoListView
from users.urls import auth_urls
from users.views import TeacherDetailView

admin.autodiscover()

urlpatterns = [
    path('', cscenter_views.IndexView.as_view(), name='index'),
    path('robots.txt', robots, name='robots_txt'),
    path('open-nsk/', cscenter_views.OpenNskView.as_view(), name='open_nsk'),
    path('api/', include('api.urls')),
    path('tools/markdown/preview/', MarkdownRenderView.as_view(), name='render_markdown'),
    path('commenting-the-right-way/', MarkdownHowToHelpView.as_view(), name='commenting_the_right_way'),
    # Redirect from an old url `/pages/questions/` to the new one
    # TODO: move to nginx?
    path('pages/questions/', RedirectView.as_view(url='/enrollment/program/', permanent=True)),
    path('orgs/', cscenter_views.TeamView.as_view(), name='orgs'),
    path('syllabus/', cscenter_views.SyllabusView.as_view(), name='syllabus'),


    path('learning/useful/', UsefulListView.as_view(), name='learning_useful'),
    path('learning/internships/', InternshipListView.as_view(), name='learning_internships'),

    path('teachers2/', cscenter_views.TeachersV2View.as_view(), name='teachers_v2'),
    path('teachers/', cscenter_views.TeachersView.as_view(), name='teachers'),
    path('teachers/<int:pk>/', TeacherDetailView.as_view(), name='teacher_detail'),

    path('', include(auth_urls)),
    path('', include('users.urls')),

    path('alumni2/', cscenter_views.AlumniV2View.as_view(), name='alumni_v2'),
    path('alumni/', cscenter_views.AlumniView.as_view(), name='alumni'),
    path('alumni/<str:area_of_study_code>/', cscenter_views.AlumniView.as_view(), name='alumni_by_area_of_study'),
    re_path(r'^(?P<year>201[3-7])/$', cscenter_views.AlumniByYearView.as_view(), name='alumni_memory'),
    re_path(r'^(?P<year>20[0-9]{2})/$', cscenter_views.AlumniHonorBoardView.as_view(), name='alumni_honor'),

    path('notifications/', include("notifications.urls")),
    path('staff/', include("staff.urls")),
    path('stats/', include("stats.urls")),
    path('surveys/', include("surveys.urls")),
    path('library/', include("library.urls")),
    path('faq/', cscenter_views.QAListView.as_view(), name='faq'),
    path('testimonials2/', cscenter_views.TestimonialsListV2View.as_view(), name='testimonials_v2'),
    path('testimonials/', cscenter_views.TestimonialsListView.as_view(), name='testimonials'),

    path('courses/', cscenter_views.CourseOfferingsView.as_view(), name="course_list"),
    path('', include('courses.urls')),
    path('', include('online_courses.urls')),
    path('videos/', CourseVideoListView.as_view(), name='course_video_list'),
    path('', include('learning.urls')),
    path('', include('admission.urls')),
    path('', include('learning.projects.urls')),
    path('narnia/', admin.site.urls),
    path('narnia/', include(loginas_urls)),
    # Required `is_staff` only. Mb restrict to `is_superuser`?
    path('narnia/django-rq/', include('django_rq.urls')),
    # TODO: remove after testing
    path('', include('admission_test.urls')),

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

# Note: htmlpages should be the last one
urlpatterns += [re_path(r'^(?P<url>.*/)$', views.flatpage, name='html_pages')]
