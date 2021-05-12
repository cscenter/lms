from django.urls import path, re_path

from .views import (
    ApplicationFormSubmissionByDays, ApplicationSubmission, CampaignResultsByCourses,
    CampaignResultsByUniversities, CampaignsStagesByYears, CampaignStagesByCourses,
    CampaignStagesByUniversities, CampaignStatsApplicantsResults,
    CampaignStatsExamScoreByCourses, CampaignStatsExamScoreByUniversities,
    CampaignStatsStudentsResults, CampaignStatsTestingScoreByCourses,
    CampaignStatsTestingScoreByUniversities
)

urlpatterns = [
    # Stages
    re_path(r'^branches/(?P<branch_id>\w+)/stages/$',
            CampaignsStagesByYears.as_view({'get': 'list'}),
            name='stats_admission_campaigns_stages_by_year'),
    re_path(r'^campaigns/(?P<campaign_id>\d+)/stages/by-university/$',
            CampaignStagesByUniversities.as_view({'get': 'list'}),
            name='stats_admission_campaign_stages_by_university'),
    re_path(r'^campaigns/(?P<campaign_id>\d+)/stages/by-course/$',
            CampaignStagesByCourses.as_view({'get': 'list'}),
            name='stats_admission_campaign_stages_by_course'),
    # Applicants
    re_path(r'^branches/(?P<branch_id>\d+)/applicants/$', CampaignStatsApplicantsResults.as_view(),
            name='stats_admission_campaign_applicants_results'),
    re_path(r'^branches/(?P<branch_id>\d+)/applicants/form-submissions/', ApplicationFormSubmissionByDays.as_view(),
            name='stats_admission_application_form_submission'),
    re_path(r'^campaigns/(?P<campaign_id>\d+)/applicants/by-university/$',
            CampaignResultsByUniversities.as_view(),
            name='stats_admission_campaign_applicants_by_university'),
    re_path(r'^campaigns/(?P<campaign_id>\d+)/applicants/by-course/$',
            CampaignResultsByCourses.as_view(),
            name='stats_admission_campaign_applicants_by_course'),
    path("campaigns/<int:campaign_id>/applicants/by-day/",
         ApplicationSubmission.as_view(),
         name="application_submission"),
    # Students
    re_path(r'^campaigns/(?P<campaign_id>\d+)/students/$',
            CampaignStatsStudentsResults.as_view({'get': 'list'}),
            name='stats_admission_campaign_students_results'),
    # Testing
    re_path(r'^campaigns/(?P<campaign_id>\d+)/testing/by-university/$',
            CampaignStatsTestingScoreByUniversities.as_view(),
            name='stats_admission_campaign_testing_score_by_university'),
    re_path(r'^campaigns/(?P<campaign_id>\d+)/testing/by-course/$',
            CampaignStatsTestingScoreByCourses.as_view(),
            name='stats_admission_campaign_testing_score_by_course'),
    # Examination
    re_path(r'^campaigns/(?P<campaign_id>\d+)/exam/by-university/$',
            CampaignStatsExamScoreByUniversities.as_view(),
            name='stats_admission_campaign_exam_score_by_university'),
    re_path(r'^campaigns/(?P<campaign_id>\d+)/exam/by-course/$',
            CampaignStatsExamScoreByCourses.as_view(),
            name='stats_admission_campaign_exam_score_by_course'),
]
