from django.conf.urls import include
from django.urls import path, re_path

from admission.api.views import (
    CampaignCreateContestScoresImportTask,
    ConfirmationSendEmailVerificationCodeApi,
)
from admission.views import (
    ApplicantCreateStudentView,
    ApplicantDetailView,
    ApplicantListView,
    ApplicantStatusUpdateView,
    ConfirmationOfAcceptanceForStudiesDoneView,
    ConfirmationOfAcceptanceForStudiesView,
    InterviewAssignmentDetailView,
    InterviewCommentUpsertView,
    InterviewDetailView,
    InterviewInvitationCreateView,
    InterviewInvitationListView,
    InterviewListCSVView,
    InterviewListView,
    InterviewResultsDispatchView,
    InterviewResultsView,
    RegisterApplicantsForOlympiadView,
)

app_name = "admission"

applicant_patterns = [
    path("", ApplicantListView.as_view(), name="list"),
    path("<int:pk>/", ApplicantDetailView.as_view(), name="detail"),
    path(
        "<int:pk>/create_student",
        ApplicantCreateStudentView.as_view(),
        name="create_student",
    ),
    path("status/<int:pk>/", ApplicantStatusUpdateView.as_view(), name="update_status"),
    path(
        "campaigns/<int:campaign_id>/register-for-olympiad/",
        RegisterApplicantsForOlympiadView.as_view(),
        name="register_for_olympiad",
    ),
]

interview_invitation_patterns = [
    path("", InterviewInvitationListView.as_view(), name="list"),
    path("send", InterviewInvitationCreateView.as_view(), name="send"),
]

interview_patterns = [
    path("", InterviewListView.as_view(), name="list"),
    path("download_csv", InterviewListCSVView.as_view(), name="csv_list"),
    path("<int:pk>/", InterviewDetailView.as_view(), name="detail"),
    path(
        "interviews/<int:pk>/comment",
        InterviewCommentUpsertView.as_view(),
        name="comment",
    ),
    path(
        "assignments/<int:pk>/",
        InterviewAssignmentDetailView.as_view(),
        name="assignment",
    ),
]

results_patterns = [
    path("", InterviewResultsDispatchView.as_view(), name="dispatch"),
    path("<str:branch_code>/", InterviewResultsView.as_view(), name="list"),
]

acceptance_patterns = [
    re_path(
        r"^(?P<year>\d{4})/(?P<access_key>\w+)/$",
        ConfirmationOfAcceptanceForStudiesView.as_view(),
        name="confirmation_form",
    ),
    path(
        "done/",
        ConfirmationOfAcceptanceForStudiesDoneView.as_view(),
        name="confirmation_done",
    ),
]
acceptance_api_patterns = [
    # FIXME: consider to use year/access_key in this URL to make action on the resource
    path(
        "verify-email",
        ConfirmationSendEmailVerificationCodeApi.as_view(),
        name="email_verification_code",
    ),
]

urlpatterns = [
    path(
        "admission/",
        include(
            [
                path("applicants/", include((applicant_patterns, "applicants"))),
                path(
                    "interviews/",
                    include(
                        (
                            [
                                path("", include(interview_patterns)),
                                path(
                                    "invitations/",
                                    include(
                                        (interview_invitation_patterns, "invitations")
                                    ),
                                ),
                            ],
                            "interviews",
                        )
                    ),
                ),
                path("results/", include((results_patterns, "results"))),
                path("confirmation/", include((acceptance_patterns, "acceptance"))),
            ]
        ),
    ),
    path(
        "api/admission/",
        include(
            (
                [
                    path(
                        "confirmation/",
                        include((acceptance_api_patterns, "acceptance")),
                    ),
                    path(
                        "<int:campaign_id>/contest/<int:contest_type>/import/",
                        CampaignCreateContestScoresImportTask.as_view(),
                        name="import_contest_scores",
                    ),
                ],
                "api",
            )
        ),
    ),
]
