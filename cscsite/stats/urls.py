from django.conf.urls import url

from stats.views import StatsIndexView, StatsLearningView

urlpatterns = [
    url(r'^$', StatsIndexView.as_view(), name='stats_index'),
    url(r'^learning/$', StatsLearningView.as_view(), name='stats_learning'),
]
