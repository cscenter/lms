from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views import generic

from learning.icalendar import UserClassesICalendar, UserAssignmentsICalendar, \
    EventsICalendar
from users.models import User


# TODO: add secret link for each student?
class UserICalendarView(generic.base.View):
    calendar_class = None

    def get(self, request, *args, **kwargs):
        cal = self.calendar_class(*self.get_init_args())
        response = HttpResponse(cal.to_ical(),
                                content_type="text/calendar; charset=UTF-8")
        response['Content-Disposition'] = "attachment; filename=\"{}\"".format(
            cal.file_name)
        return response

    def get_init_args(self):
        user_id = self.kwargs['pk']
        qs = (User.objects
              .filter(pk=user_id)
              .only("first_name", "last_name", "patronymic", "pk"))
        user = get_object_or_404(qs)
        return [self.request.site, user, self.request.build_absolute_uri]


class ICalClassesView(UserICalendarView):
    calendar_class = UserClassesICalendar


class ICalAssignmentsView(UserICalendarView):
    calendar_class = UserAssignmentsICalendar


class ICalEventsView(UserICalendarView):
    calendar_class = EventsICalendar

    def get_init_args(self):
        request = self.request
        return [request.site, request.user, request.build_absolute_uri]
