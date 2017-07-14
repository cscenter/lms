from django.conf.urls import include, url

from stats.admission.views import CampaignsStagesByYears, \
    CampaignStatsApplicantsResults, CampaignStatsStudentsResults, \
    CampaignStatsTestingScoreByUniversities, \
    CampaignStatsExamScoreByUniversities, \
    CampaignStagesByUniversities, CampaignStagesByCourses, \
    CampaignStatsTestingScoreByCourses, CampaignStatsExamScoreByCourses

urlpatterns = [
    url(r'^cities/(?P<city_code>\w+)/stages/$',
        CampaignsStagesByYears.as_view({'get': 'list'}),
        name='stats_admission_campaigns_stages_by_year'),
    url(r'^campaigns/(?P<campaign_id>\d+)/stages/by-university/$',
        CampaignStagesByUniversities.as_view({'get': 'list'}),
        name='stats_admission_campaign_stages_by_university'),
    url(r'^campaigns/(?P<campaign_id>\d+)/stages/by-course/$',
        CampaignStagesByCourses.as_view({'get': 'list'}),
        name='stats_admission_campaign_stages_by_course'),
    url(r'^cities/(?P<city_code>\w+)/applicants/$',
        CampaignStatsApplicantsResults.as_view(),
        name='stats_admission_campaign_applicants_results'),
    url(r'^campaigns/(?P<campaign_id>\d+)/students/$',
        CampaignStatsStudentsResults.as_view({'get': 'list'}),
        name='stats_admission_campaign_students_results'),
    url(r'^campaigns/(?P<campaign_id>\d+)/testing/by-university/$',
        CampaignStatsTestingScoreByUniversities.as_view(),
        name='stats_admission_campaign_testing_score_by_university'),
    url(r'^campaigns/(?P<campaign_id>\d+)/testing/by-course/$',
        CampaignStatsTestingScoreByCourses.as_view(),
        name='stats_admission_campaign_testing_score_by_course'),
    url(r'^campaigns/(?P<campaign_id>\d+)/exam/by-university/$',
        CampaignStatsExamScoreByUniversities.as_view(),
        name='stats_admission_campaign_exam_score_by_university'),
    url(r'^campaigns/(?P<campaign_id>\d+)/exam/by-course/$',
        CampaignStatsExamScoreByCourses.as_view(),
        name='stats_admission_campaign_exam_score_by_course'),
]
