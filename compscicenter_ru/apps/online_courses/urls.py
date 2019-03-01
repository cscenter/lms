from django.conf.urls import url

from .views import OnlineCoursesView

app_name = 'online_courses'

urlpatterns = [
    url(r'^online/$', OnlineCoursesView.as_view(), name='list'),
]
