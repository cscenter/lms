from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'cscsite.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^news/', include('news.urls')),
    url(r'^contacts/', TemplateView.as_view(template_name="contacts.html")),
    url(r'^admin/', include(admin.site.urls)),
)
