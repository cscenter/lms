from django.urls import include, path

from lk_yandexdataschool_ru.apps.application.api.views import (
    ApplicationFormCreateTaskView
)
from lms.urls import urlpatterns

urlpatterns += [
    path('admission/applications/', ApplicationFormCreateTaskView.as_view(), name='admission_application_form_new_task'),
    path('', include('admission.urls_appointment')),
]
