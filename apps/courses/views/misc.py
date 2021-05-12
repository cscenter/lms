from vanilla import DetailView

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import generic

from core.models import Branch, Location
from courses.models import Course, CourseTeacher
from learning.roles import Roles
from users.models import User


class TeacherDetailView(LoginRequiredMixin, DetailView):
    template_name = "lms/courses/teacher_detail.html"
    context_object_name = 'teacher'

    def get_queryset(self, *args, **kwargs):
        # FIXME: Будет показываться любой преподаватель с любого сайта с группой преподавателя
        return User.objects.filter(group__role=Roles.TEACHER).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        branches = Branch.objects.for_site(site_id=self.request.site.pk)
        min_established = min(b.established for b in branches)
        courses = (Course.objects
                   .in_branches(branches)
                   .filter(semester__year__gte=min_established,
                           course_teachers__roles=~CourseTeacher.roles.spectator,
                           teachers=self.object.pk)
                   .select_related('semester', 'meta_course', 'main_branch')
                   .order_by('-semester__index'))
        context['courses'] = courses
        return context


class VenueListView(generic.ListView):
    model = Location
    template_name = "courses/venue_list.html"

    def get_queryset(self):
        qs = Location.objects.get_queryset()
        # Limit results on compsciclub.ru
        if hasattr(self.request, "branch") and self.request.branch.city_id:
            qs = qs.filter(city_id=self.request.branch.city_id)
        return qs


class VenueDetailView(generic.DetailView):
    model = Location
    template_name = "courses/venue_detail.html"
