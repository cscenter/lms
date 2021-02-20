from django.urls import path

from lk_yandexdataschool_ru.apps.application.api.views import ApplicationFormCreateTaskView
from lms.urls import urlpatterns


urlpatterns += [
    path('admission/applications/', ApplicationFormCreateTaskView.as_view(), name='admission_application_form_new_task'),
]
