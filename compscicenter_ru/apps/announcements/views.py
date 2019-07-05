from dal import autocomplete
from django.contrib.auth.mixins import PermissionRequiredMixin, \
    LoginRequiredMixin
from django.utils import timezone
from django_jinja.views.generic import DetailView

from announcements.models import Announcement, AnnouncementTag


class AnnouncementTagAutocomplete(LoginRequiredMixin, PermissionRequiredMixin,
                                  autocomplete.Select2QuerySetView):
    permission_required = 'announcements.add_announcement'

    def get_queryset(self):
        qs = AnnouncementTag.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class AnnouncementDetailView(DetailView):
    model = Announcement
    template_name = "compscicenter_ru/announcements/announcement_detail.html"

    def get_queryset(self):
        # Note: Announcement always accessible by direct link
        return (Announcement.objects
                .select_related("event_details",
                                "event_details__venue"))
