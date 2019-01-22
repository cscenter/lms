from django.conf import settings
from django.db.models import Q
from django.views import generic
from vanilla import ListView

from courses.models import Course, Venue
from courses.utils import grouper


class CourseVideoListView(ListView):
    model = Course
    template_name = "courses/courses_video_list.html"
    context_object_name = 'course_list'

    def get_queryset(self):
        return (Course.objects
                .filter(is_published_in_video=True)
                .order_by('-semester__year', 'semester__type')
                .select_related('meta_course', 'semester'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        full = context[self.context_object_name]
        context['course_list_chunks'] = grouper(full, 3)
        return context


class VenueListView(generic.ListView):
    model = Venue
    template_name = "courses/venue_list.html"

    def get_queryset(self):
        return (Venue.objects
                .filter(sites__pk=settings.SITE_ID)
                .filter(Q(city_id=self.request.city_code) |
                        Q(city__isnull=True)))


class VenueDetailView(generic.DetailView):
    model = Venue
    template_name = "courses/venue_detail.html"
