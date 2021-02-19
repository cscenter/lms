from django.urls import path

from .views import OnlineCoursesView

app_name = 'online_courses'

urlpatterns = [
    path('online/', OnlineCoursesView.as_view(), name='list'),
]
