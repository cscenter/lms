from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.views.generic import TemplateView

from django.contrib import admin

from index.views import IndexView, AlumniView, ProfView

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'cscsite.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^syllabus/$', TemplateView.as_view(template_name="contacts.html"), name='syllabus'),
    url(r'^orgs/$', TemplateView.as_view(template_name="contacts.html"), name='orgs'),
    url(r'^profs/$', ProfView.as_view(), name='profs'),
    url(r'^alumni/$', AlumniView.as_view(), name='alumni'),
    url(r'^news/', include('news.urls')),
    url(r'^contacts/$', TemplateView.as_view(template_name="contacts.html"), name='contacts'),
    url(r'^admin/', include(admin.site.urls)),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
