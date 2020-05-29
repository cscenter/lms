from django.urls import path

from .views import UsefulListView, InternshipListView, HonorCodeView

urlpatterns = [
    path('useful/', UsefulListView.as_view(), name='learning_useful'),
    path('internships/', InternshipListView.as_view(), name='learning_internships'),
    path('hc/', HonorCodeView.as_view(), name='honor_code'),
]
