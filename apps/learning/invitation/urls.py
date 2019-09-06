from django.conf.urls import include
from django.urls import path, re_path

from . import views as v

app_name = "invitation"

urlpatterns = [
    path("invitation/", include([
        path('<str:token>/', v.InvitationView.as_view(), name="course_list"),
        path('<str:token>/login/', v.InvitationLoginView.as_view(), name="login"),
        path('<str:token>/update-profile/', v.InvitationCompleteProfileView.as_view(), name="complete_profile"),
        path('<str:token>/register/', v.InvitationRegisterView.as_view(), name="registration"),
        path('register/complete/', v.InvitationRegisterCompleteView.as_view(), name="registration_complete"),
        # Activation keys get matched by \w+ instead of the more specific
        # [a-fA-F0-9]{40} because a bad activation key should still get
        # to the view; that way it can return a sensible "invalid key"
        # message instead of a confusing 404.
        re_path(r'^(?P<token>[_\w-]+)/activate/(?P<activation_key>\w+)/$', v.InvitationActivationView.as_view(), name='activate'),
        path('activate/complete/', v.InvitationActivationCompleteView.as_view(), name='activation_complete'),
    ])),
]
