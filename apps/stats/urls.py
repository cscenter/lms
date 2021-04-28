from django.urls import path

from stats.views import StatsAdmissionView, StatsIndexView, StatsLearningView

app_name = 'stats'

urlpatterns = [
    path('', StatsIndexView.as_view(), name='index'),
    path('learning/', StatsLearningView.as_view(), name='learning'),
    path('admission/', StatsAdmissionView.as_view(), name='admission'),
]
