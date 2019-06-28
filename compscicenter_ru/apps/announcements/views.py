from dal import autocomplete
from django.contrib.auth.mixins import PermissionRequiredMixin, \
    LoginRequiredMixin
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
