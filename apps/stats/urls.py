from django.urls import include, path

from stats.views import StatsIndexView, StatsLearningView, StatsAdmissionView

app_name = 'stats'

urlpatterns = [
    path('', StatsIndexView.as_view(), name='index'),
    path('learning/', StatsLearningView.as_view(), name='learning'),
    path('admission/', StatsAdmissionView.as_view(), name='admission'),
]
