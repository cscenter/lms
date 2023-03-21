from django.urls import include, path

from . import views as v

app_name = "admission-api"

urlpatterns = [
    path(
        "v2/admission/",
        include(
            (
                [
                    path(
                        "interviews/slots/",
                        v.InterviewSlots.as_view(),
                        name="interview_slots",
                    ),
                    path(
                        "residence-cities/",
                        v.ResidenceCityList.as_view(),
                        name="residence_cities",
                    ),
                    path(
                        "residence-city-campaigns/",
                        v.CampaignCityList.as_view(),
                        name="residence_cities",
                    ),
                ],
                "v2",
            )
        ),
    )
]
