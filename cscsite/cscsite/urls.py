from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.views.generic import TemplateView

from django.contrib import admin

from index.views import IndexView, AlumniView, ProfView
from users.views import LoginView, LogoutView
from textpages.views import TextpageOpenView, TextpageStudentView
from learning.views import \
    TimetableTeacherView, \
    CourseTeacherListView, CourseUpdateView, \
    CourseListView, CourseDetailView, \
    CourseOfferingDetailView, \
    CourseOfferingEnrollView, CourseOfferingUnenrollView, \
    CourseClassDetailView, \
    VenueListView, VenueDetailView

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

    url(r'^teaching/timetable/$', TimetableTeacherView.as_view(),
        name='timetable_teacher'),
    url(r'^teaching/courses/$', CourseTeacherListView.as_view(),
        name='course_list_teacher'),
    url(r'^teaching/courses/(?P<pk>\d+)$', CourseUpdateView.as_view(),
        name='course_edit'),

    url(r"^courses/$", CourseListView.as_view(),
        name="course_list"),
    url(r"^courses/(?P<slug>[-\w]+)/$", CourseDetailView.as_view(),
        name="course_detail"),
    url(r"^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)$",
        CourseOfferingDetailView.as_view(),
        name="course_offering_detail"),
    url(r"^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/enroll$",
        CourseOfferingEnrollView.as_view(),
        name="course_offering_enroll"),
    url(r"^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/unenroll$",
        CourseOfferingUnenrollView.as_view(),
        name="course_offering_unenroll"),
    url(r"^courses/(?P<course_slug>[-\w]+)/(?P<semester_slug>[-\w]+)/(?P<pk>[-\w]+)$",
        CourseClassDetailView.as_view(),
        name="class_detail"),

    url(r"^venues/$", VenueListView.as_view(),
        name="venue_list"),
    url(r"^venues/(?P<pk>[-\w]+)/$", VenueDetailView.as_view(),
        name="venue_detail"),

    url(r'^licenses/$', TextpageStudentView.as_view(), name='licenses'),

    url(r'^login/$', LoginView.as_view(), name='login'),
    url(r'^logout/$', LogoutView.as_view(), name='logout'),

    url(r'^admin/', include(admin.site.urls)),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
