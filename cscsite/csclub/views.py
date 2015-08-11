from django.conf import settings
from django.http import JsonResponse
from django.views import generic

from .utils import check_for_city
from learning.views import CalendarMixin
from learning.models import NonCourseEvent


def set_city(request, city_code):
    success = False
    city_code = city_code.replace('-', ' ').upper()
    if request.method == 'POST':
        if check_for_city(city_code):
            if hasattr(request, 'session'):
                request.session[settings.CITY_SESSION_KEY] = city_code
            else:
                response = JsonResponse({'success': True})
                response.set_cookie(settings.CITY_COOKIE_NAME, city_code,
                                    max_age=settings.LANGUAGE_COOKIE_AGE,
                                    path=settings.LANGUAGE_COOKIE_PATH,
                                    domain=settings.LANGUAGE_COOKIE_DOMAIN)
                return response
            success = True

    return JsonResponse({'success': success})


class CalendarClubScheduleView(CalendarMixin, generic.ListView):
    user_type = 'public_full'

    def noncourse_events(self, month, year, prev_month_date, next_month_date):
        return NonCourseEvent.objects.none()
