from django.urls import path

from . import views as v

app_name = 'announcements'

urlpatterns = [
    path("announcements/tags-autocomplete/", v.AnnouncementTagAutocomplete.as_view(), name="tags_autocomplete"),
    path("announcements/<slug:slug>/", v.AnnouncementDetailView.as_view(), name="announcement_detail"),
]
