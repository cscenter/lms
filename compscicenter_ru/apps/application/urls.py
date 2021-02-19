from django.urls import path, include

from .views import yandex_login_access, yandex_login_access_complete, \
    ApplicationFormView

app_name = 'application'

urlpatterns = [
    path('application/', include([
        path('', ApplicationFormView.as_view(), name='form'),
        path('yandex_access/', yandex_login_access, name='auth_begin'),
        path('yandex_access/complete/', yandex_login_access_complete, name='auth_complete'),
    ])),
]
