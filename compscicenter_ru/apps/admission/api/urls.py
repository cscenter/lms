from django.urls import path

from . import views as v

urlpatterns = [
    path('applicants/', v.ApplicantCreateAPIView.as_view(), name='applicant_create'),
]
