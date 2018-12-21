from django.conf.urls import url

from .views import OnlineCoursesListView

app_name = 'online_courses'

urlpatterns = [
    url(r'^online/$', OnlineCoursesListView.as_view(), name='list'),
]
