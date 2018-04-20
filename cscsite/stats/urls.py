from django.conf.urls import url

from stats.views import StatsIndexView, StatsLearningView, StatsAdmissionView

app_name = 'stats'

urlpatterns = [
    url(r'^$', StatsIndexView.as_view(), name='index'),
    url(r'^learning/$', StatsLearningView.as_view(), name='learning'),
    url(r'^admission/$', StatsAdmissionView.as_view(), name='admission'),
]
