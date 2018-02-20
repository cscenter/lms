from django.conf.urls import include, url

from admission_test import views


app_name = 'admission_test'

urlpatterns = [
    url(r'^enrollment/', include([
        url(r'^subscribe/$', views.AdmissionTestApplicantCreateView.as_view(), name='admission_2018_testing'),
        url(r'^subscribe/complete/$', views.registration_complete, name='registration_complete'),
        url(r'^subscribe/auth/$', views.auth, name='auth_begin'),
        url(r'^subscribe/auth/complete/$', views.auth_complete, name='auth_complete'),
    ])),
]
