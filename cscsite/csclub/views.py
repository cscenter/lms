from django.conf import settings
from django.db.models import Q, Prefetch, Count
from django.http import JsonResponse
from django.views import generic
from django.utils.timezone import now

from .utils import check_for_city
from learning.views import CalendarMixin
from learning.models import NonCourseEvent, CourseOffering, Semester, \
    CourseClass
from learning.utils import grouper


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


class IndexView(generic.TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        current_semester = Semester.get_current()
        context['current_semester'] = current_semester
        today = now().date()
        # TODO: add cache
        courseclass_queryset = (CourseClass.objects
                                           .filter(date__gte=today)
                                           .order_by('date', 'starts_at'))
        context['courses'] = (CourseOffering.custom.site_related(self.request)
            .filter(semester=current_semester.pk)
            .select_related('course', 'semester')
            .prefetch_related(
                'teachers',
                Prefetch(
                    'courseclass_set',
                    queryset=courseclass_queryset,
                    to_attr='classes'
                ),
            )
            .order_by('course__name'))

        return context
