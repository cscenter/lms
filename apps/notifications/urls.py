from django.conf.urls import url

from .views import CourseNewsNotificationUpdate

app_name = 'notifications'

urlpatterns = [
    url(r'^course-offerings/news/$',
        CourseNewsNotificationUpdate.as_view(),
        name='course__news'),
]