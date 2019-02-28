from django.utils import timezone
from django.views import generic

from online_courses.models import OnlineCourse


class OnlineCoursesListView(generic.ListView):
    context_object_name = 'courses'
    model = OnlineCourse
    template_name = "online_courses/online_courses_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recent_courses"] = filter(
            lambda c: not c.is_self_paced and (not c.end or c.end > timezone.now()),
            context[self.context_object_name])
        context["self_paced_courses"] = sorted(filter(
            lambda c: c.is_self_paced,
            context[self.context_object_name]), key=lambda c: c.name)
        context["archive_courses"] = filter(
            lambda c: c.end and c.end <= timezone.now() and not c.is_self_paced,
            context[self.context_object_name]
        )
        return context

    def get_queryset(self):
        return OnlineCourse.objects.order_by("is_self_paced", "-start", "name")


class OnlineCoursesView(generic.ListView):
    context_object_name = 'online_courses'
    model = OnlineCourse
    template_name = "compscicenter_ru/online_courses.html"

    def get_queryset(self):
        return OnlineCourse.objects.order_by("-start", "name")
