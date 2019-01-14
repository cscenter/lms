from django.views import generic

from international_schools.models import InternationalSchool


class InternationalSchoolsListView(generic.ListView):
    model = InternationalSchool
    context_object_name = 'schools'
    template_name = "international_schools/international_schools.html"

    def get_queryset(self):
        return InternationalSchool.objects.order_by("-deadline")
