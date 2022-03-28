from django.urls import include, path

from .views import (
    ApplicationFormView
)

app_name = 'application'

urlpatterns = [
    path('application/', include([
        path('', ApplicationFormView.as_view(), name='form'),
    ])),
]
