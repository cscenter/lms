from django.db.models import Q
from django.views import generic

from core.models import Location


class VenueListView(generic.ListView):
    model = Location
    template_name = "courses/venue_list.html"

    def get_queryset(self):
        qs = Location.objects.get_queryset()
        if hasattr(self.request, "branch") and self.request.branch.city_id:
            qs = qs.filter(city_id=self.request.branch.city_id)
        return qs


class VenueDetailView(generic.DetailView):
    model = Location
    template_name = "courses/venue_detail.html"
