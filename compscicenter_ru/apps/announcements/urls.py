from django.urls import path

from . import views as v

app_name = 'announcements'

urlpatterns = [
    path("<slug:slug>/", v.AnnouncementDetailView.as_view(), name="announcement_detail"),
]
