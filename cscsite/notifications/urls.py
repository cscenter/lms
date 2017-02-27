from django.conf.urls import url

from .views import CourseOfferingNewsNotificationUpdate

app_name = 'notifications'

urlpatterns = [
    url(r'^course-offerings/news/$',
        CourseOfferingNewsNotificationUpdate.as_view(),
        name='course_offerings__news'),
]