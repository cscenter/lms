from django.db.models import Q
from django.views import generic

from core.models import Venue


class VenueListView(generic.ListView):
    model = Venue
    template_name = "courses/venue_list.html"

    def get_queryset(self):
        qs = Venue.objects.get_queryset()
        if hasattr(self.request, "branch") and self.request.branch.city_id:
            qs = qs.filter(city_id=self.request.branch.city_id)
        return qs


class VenueDetailView(generic.DetailView):
    model = Venue
    template_name = "courses/venue_detail.html"
