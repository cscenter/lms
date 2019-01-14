from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.views import generic

from learning.models import CourseNewsNotification


class CourseNewsNotificationUpdate(generic.View):
    http_method_names = ["post", "put"]

    def post(self, request, *args, **kwargs):
        course = request.POST.get("co")
        if not request.user.is_authenticated or not course:
            raise PermissionDenied
        updated = (CourseNewsNotification.unread
                   .filter(course_offering_news__course=course,
                           user_id=self.request.user.pk)
                   .update(is_unread=False))
        return JsonResponse({"updated": bool(updated)})

    def put(self, *args, **kwargs):
        return self.post(*args, **kwargs)
