from django.conf.urls import include, url
from django.urls import path

from admission.views import yandex_login_access, yandex_login_access_complete, \
    ApplicationFormView

app_name = 'application'

urlpatterns = [
    url(r'^application/', include([
        path('', ApplicationFormView.as_view(), name='form'),
        url(r'^yandex_access/$', yandex_login_access, name='auth_begin'),
        url(r'^yandex_access/complete/$', yandex_login_access_complete, name='auth_complete'),
    ])),
]
