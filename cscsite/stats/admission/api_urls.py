from django.conf.urls import include, url

from stats.admission.views import CampaignStatsByStage, \
    CampaignStatsApplicantsResults, CampaignStatsStudentsResults, \
    CampaignStatsOnlineTestScore, CampaignStatsExamScore

urlpatterns = [
        url(r'^campaigns/(?P<city_code>\w+)/stages/$',
            CampaignStatsByStage.as_view({'get': 'list'}),
            name='stats_admission_campaign_stages'),
        url(r'^campaigns/(?P<city_code>\w+)/applicants/$',
            CampaignStatsApplicantsResults.as_view(),
            name='stats_admission_campaign_applicants_results'),
        url(r'^campaigns/(?P<campaign_id>\d+)/students/$',
            CampaignStatsStudentsResults.as_view({'get': 'list'}),
            name='stats_admission_campaign_students_results'),
        url(r'^campaigns/(?P<campaign_id>\d+)/testing/$',
            CampaignStatsOnlineTestScore.as_view({'get': 'list'}),
            name='stats_admission_campaign_testing_score'),
        url(r'^campaigns/(?P<campaign_id>\d+)/exam/$',
            CampaignStatsExamScore.as_view({'get': 'list'}),
            name='stats_admission_campaign_exam_score'),
]



