from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.views.generic import TemplateView

from django.contrib import admin

from index.views import IndexView, AlumniView, ProfView
from users.views import LoginView, LogoutView
from textpages.views import TextpageOpenView, TextpageStudentView
from learning.views import CourseTeacherListView, CourseUpdateView, \
    CourseDetailView

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^syllabus/$', TextpageOpenView.as_view(), name='syllabus'),
    url(r'^orgs/$', TextpageOpenView.as_view(), name='orgs'),
    url(r'^profs/$', ProfView.as_view(), name='profs'),
    url(r'^alumni/$', AlumniView.as_view(), name='alumni'),
    url(r'^news/', include('news.urls')),
    url(r'^enrollment/$', TextpageOpenView.as_view(), name='enrollment'),
    url(r'^contacts/$', TextpageOpenView.as_view(), name='contacts'),

    url(r'^teaching/courses/$', CourseTeacherListView.as_view(),
        name='courses_teacher'),
    url(r'^teaching/courses/(?P<pk>\d+)$', CourseUpdateView.as_view(),
        name='course_edit'),

    url(regex=r"^courses/(?P<slug>[-\w]+)/$",
        view=CourseDetailView.as_view(),
        name="course_detail"),

    url(r'^licenses/$', TextpageStudentView.as_view(), name='licenses'),

    url(r'^login/$', LoginView.as_view(), name='login'),
    url(r'^logout/$', LogoutView.as_view(), name='logout'),

    url(r'^admin/', include(admin.site.urls)),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
