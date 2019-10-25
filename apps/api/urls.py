from django.urls import path

from .views import TokenObtainView, TokenRevokeView

app_name = 'api-auth'

urlpatterns = [
    path('token/', TokenObtainView.as_view(), name='token_obtain'),
    path('revoke/', TokenRevokeView.as_view(), name='token_revoke'),
]
