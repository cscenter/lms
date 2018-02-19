from django.conf.urls import include, url

from admission_test import views


app_name = 'admission_test'

urlpatterns = [
    url(r'^admission-2018/', include([
        url(r'^testing/$', views.AdmissionTestApplicantCreateView.as_view(), name='admission_2018_testing'),
        url(r'^testing/auth/$', views.auth, name='auth_begin'),
        url(r'^testing/auth/complete/$', views.auth_complete, name='auth_complete'),
    ])),
]
