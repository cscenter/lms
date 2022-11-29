from django.conf import settings
from django.contrib.auth import views
from django.urls import include, path


from auth.views import (
    LoginView, LogoutView, connect_service_begin, connect_service_complete,
    disconnect_service, pass_reset_confirm_view, pass_reset_view, yandex_login_access_admission,
    yandex_login_access_admission_complete, yandex_profile_oauth_data_access, yandex_profile_oauth_data_complete
)

app_name = 'auth'

social_patterns = [
    path('connect/<str:backend>/', connect_service_begin, name='begin'),
    path('complete/<str:backend>/', connect_service_complete, name='complete'),
    path('disconnect/<str:backend>/', disconnect_service, name='disconnect'),
]

yandex_application_access_patterns = [
    path('yandex_access/', yandex_login_access_admission, name='begin'),
    path('yandex_access/complete/', yandex_login_access_admission_complete, name='complete')
]

yandex_profile_data_access_patterns = [
    path('yandex_profile_oauth_access/', yandex_profile_oauth_data_access, name='yandex_begin'),
    path('yandex_profile_oauth_access/complete/', yandex_profile_oauth_data_complete, name='yandex_complete')
]

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(permanent=False), name='logout'),

    # path('password_change/', views.PasswordChangeView.as_view(), name='password_change'),
    # path('password_change/done/', views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    # FIXME: rename like in `registration` app
    path('password_reset/', pass_reset_view, name='password_reset'),
    path('password_reset/done/', views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', pass_reset_confirm_view, name='password_reset_confirm'),
    path('reset/done/', views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('', include((yandex_application_access_patterns, 'application'))),
    path('', include((yandex_profile_data_access_patterns, 'users')))
]



if settings.IS_SOCIAL_ACCOUNTS_ENABLED:
    urlpatterns += [
        path('social/', include((social_patterns, 'social')))
    ]
