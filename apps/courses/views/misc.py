from django.views import generic
from vanilla import DetailView

from core.models import Location, Branch
from courses.models import Course
from learning.roles import Roles
from users.models import User


class TeacherDetailView(DetailView):
    template_name = "courses/teacher_detail.html"
    context_object_name = 'teacher'

    def get_queryset(self, *args, **kwargs):
        return User.objects.has_role(Roles.TEACHER,
                                     site_id=self.request.site.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        branches = Branch.objects.for_site(site_id=self.request.site.pk)
        min_established = min(b.established for b in branches)
        courses = (Course.objects
                   .available_in(branches)
                   .filter(semester__year__gte=min_established,
                           teachers=self.object.pk)
                   .select_related('semester', 'meta_course', 'branch'))
        context['courses'] = courses
        return context


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
