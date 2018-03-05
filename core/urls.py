"""apps URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views import generic


class HtmlView(generic.TemplateView):
    def get_template_names(self):
        path_to_template = self.kwargs.get('path_to_template', '')[:-1]
        if not path_to_template:
            path_to_template = "v1/pages/index"
        return [f"{path_to_template}.jinja2",
                f"{path_to_template}/index.jinja2"]


urlpatterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + [
    url(r'^$', HtmlView.as_view(), name='index'),
    url(r'^login/$', auth_views.LoginView.as_view(), name='login'),
    url(r'^(?P<path_to_template>.*)$', HtmlView.as_view(), name='html_pages'),
]
