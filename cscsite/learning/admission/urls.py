from django.conf.urls import include, url

from learning.admission.views import DashboardView

urlpatterns = [
    url(r'^admission', include([
        url(r'^/dashboard/$', DashboardView.as_view(), name='admission_dashboard'),
    ])),
]