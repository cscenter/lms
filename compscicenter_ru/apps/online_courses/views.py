from django.views import generic

from online_courses.models import OnlineCourse


class OnlineCoursesView(generic.ListView):
    context_object_name = 'online_courses'
    model = OnlineCourse
    template_name = "compscicenter_ru/online_courses.html"

    def get_queryset(self):
        return OnlineCourse.objects.order_by("-start", "name")
