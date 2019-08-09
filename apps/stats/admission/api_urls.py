from django.conf.urls import include, url
from django.urls import path

from stats.admission.views import CampaignsStagesByYears, \
    CampaignStatsApplicantsResults, CampaignStatsStudentsResults, \
    CampaignStatsTestingScoreByUniversities, \
    CampaignStatsExamScoreByUniversities, \
    CampaignStagesByUniversities, CampaignStagesByCourses, \
    CampaignStatsTestingScoreByCourses, CampaignStatsExamScoreByCourses, \
    CampaignResultsByUniversities, CampaignResultsByCourses, \
    ApplicationSubmission, ApplicationFormSubmissionByDays

urlpatterns = [
    # Stages
    url(r'^cities/(?P<branch_code>\w+)/stages/$',
        CampaignsStagesByYears.as_view({'get': 'list'}),
        name='stats_admission_campaigns_stages_by_year'),
    url(r'^campaigns/(?P<campaign_id>\d+)/stages/by-university/$',
        CampaignStagesByUniversities.as_view({'get': 'list'}),
        name='stats_admission_campaign_stages_by_university'),
    url(r'^campaigns/(?P<campaign_id>\d+)/stages/by-course/$',
        CampaignStagesByCourses.as_view({'get': 'list'}),
        name='stats_admission_campaign_stages_by_course'),
    # Applicants
    url(r'^cities/(?P<branch_code>\w+)/applicants/$', CampaignStatsApplicantsResults.as_view(), name='stats_admission_campaign_applicants_results'),
    url(r'^cities/(?P<branch_code>\w+)/applicants/form-submissions/', ApplicationFormSubmissionByDays.as_view(), name='stats_admission_application_form_submission'),
    url(r'^campaigns/(?P<campaign_id>\d+)/applicants/by-university/$',
        CampaignResultsByUniversities.as_view(),
        name='stats_admission_campaign_applicants_by_university'),
    url(r'^campaigns/(?P<campaign_id>\d+)/applicants/by-course/$',
        CampaignResultsByCourses.as_view(),
        name='stats_admission_campaign_applicants_by_course'),
    path("campaigns/<int:campaign_id>/applicants/by-day/",
         ApplicationSubmission.as_view(),
         name="application_submission"),
    # Students
    url(r'^campaigns/(?P<campaign_id>\d+)/students/$',
        CampaignStatsStudentsResults.as_view({'get': 'list'}),
        name='stats_admission_campaign_students_results'),
    # Testing
    url(r'^campaigns/(?P<campaign_id>\d+)/testing/by-university/$',
        CampaignStatsTestingScoreByUniversities.as_view(),
        name='stats_admission_campaign_testing_score_by_university'),
    url(r'^campaigns/(?P<campaign_id>\d+)/testing/by-course/$',
        CampaignStatsTestingScoreByCourses.as_view(),
        name='stats_admission_campaign_testing_score_by_course'),
    # Examination
    url(r'^campaigns/(?P<campaign_id>\d+)/exam/by-university/$',
        CampaignStatsExamScoreByUniversities.as_view(),
        name='stats_admission_campaign_exam_score_by_university'),
    url(r'^campaigns/(?P<campaign_id>\d+)/exam/by-course/$',
        CampaignStatsExamScoreByCourses.as_view(),
        name='stats_admission_campaign_exam_score_by_course'),
]
