from django.urls import include, path

from code_reviews.gerrit.views import GerritCommentAddedWebhook

app_name = 'code_reviews'


gerrit_hooks_patterns = [
    path('comment-added/', GerritCommentAddedWebhook.as_view(), name='comment-added')
]

urlpatterns = [
    path('gerrit/hooks/', include((gerrit_hooks_patterns, 'gerrit-hooks'))),
]
