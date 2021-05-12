from django.urls import include, path

from .views import TokenObtainView, TokenRevokeView

app_name = 'auth-api'


urlpatterns = [
    path('v1/', include(([
        path('token/', TokenObtainView.as_view(), name='token_obtain'),
        path('revoke/', TokenRevokeView.as_view(), name='token_revoke'),
    ], 'v1')))
]
