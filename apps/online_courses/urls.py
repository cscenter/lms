from django.conf.urls import url

from .views import OnlineCoursesListView, OnlineCoursesView

app_name = 'online_courses'

urlpatterns = [
    url(r'^online/$', OnlineCoursesListView.as_view(), name='list'),
    url(r'^online2/$', OnlineCoursesView.as_view(), name='list2'),
]
