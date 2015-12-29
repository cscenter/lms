from collections import Counter

from django.conf import settings
from django.contrib.auth import get_user_model
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
            .order_by('is_completed', 'course__name'))

        return context


class TeachersView(generic.ListView):
    template_name = "users/teacher_list.html"

    def get_queryset(self):
        user_model = get_user_model()
        semesters = list(Semester.latest_academic_years(year_count=2).values_list(
            "id", flat=True))
        active_teachers_pks = Counter(CourseOffering.objects.filter(
            semester__in=semesters).values_list("teachers__pk", flat=True))

        teacher_groups = [user_model.group_pks.TEACHER_CLUB]
        return user_model.objects.filter(groups__in=teacher_groups).distinct()


# TODO: (XXX) Dont' forget to remove it after old.* termination.
from django.views.defaults import page_not_found
from django.views.decorators.csrf import requires_csrf_token
from django.shortcuts import get_object_or_404, redirect
@requires_csrf_token
def custom_page_not_found(request, template_name='404.html'):
    return redirect('http://old.compsciclub.ru' + request.path)
