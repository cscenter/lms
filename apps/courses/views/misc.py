from django.db.models import Q
from django.views import generic

from core.models import Venue


class VenueListView(generic.ListView):
    model = Venue
    template_name = "courses/venue_list.html"

    def get_queryset(self):
        return (Venue.objects
                .filter(Q(city_id=self.request.city_code) |
                        Q(city__isnull=True)))


class VenueDetailView(generic.DetailView):
    model = Venue
    template_name = "courses/venue_detail.html"
