from django.urls import path, include

from . import views as v

app_name = 'code-reviews-api'

urlpatterns = [
    path('v1/', include(([
        path('gerrit/', include([
            path('comment-added/', v.GerritUpdateReviewGrade.as_view(), name='gerrit_comment_added'),
        ]))
    ], 'v1')))
]