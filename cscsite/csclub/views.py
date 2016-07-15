from collections import Counter

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Prefetch, Q
from django.http import JsonResponse, Http404
from django.utils.timezone import now
from django.views import generic
# TODO: (XXX) Dont' forget to remove it after old.* termination.
from django.views.decorators.csrf import requires_csrf_token
from django.shortcuts import redirect

from learning.gallery.models import Image
from learning.models import CourseOffering, Semester, \
    CourseClass
from learning.views import CalendarMixin
from .utils import check_for_city


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
        if current_semester.type in [Semester.TYPES.spring,
                                     Semester.TYPES.autumn]:
            context['courses'] = (
                CourseOffering
                .custom
                .site_related(self.request)
                .filter(semester=current_semester.pk)
                .select_related('course', 'semester')
                .prefetch_related(
                    'teachers',
                    Prefetch(
                        'courseclass_set',
                        queryset=courseclass_queryset,
                        to_attr='classes'
                    ))
                .order_by('is_completed', 'course__name'))
        else:
            context['courses'] = []

        return context


class TeachersView(generic.ListView):
    template_name = "users/teacher_list.html"

    @property
    def get_queryset(self):
        user_model = get_user_model()
        lecturers = list(CourseOffering
            .objects
            .filter(is_open=True,
                    city__pk=self.request.city_code)
            .distinct()
            .values_list("teachers__pk", flat=True))
        return (user_model.objects
                .filter(groups=user_model.group_pks.TEACHER_CLUB,
                        courseofferingteacher__teacher_id__in=lecturers)
                .distinct)


class TeacherDetailView(generic.DetailView):
    template_name = "users/teacher_club_detail.html"
    context_object_name = 'teacher'

    def get_queryset(self, *args, **kwargs):
        co_queryset = (CourseOffering.custom.site_related(self.request)
                       .select_related('semester', 'course'))
        return (get_user_model()._default_manager
                .all()
                .prefetch_related(
                    Prefetch('teaching_set',
                             queryset=co_queryset.all(),
                             to_attr='course_offerings'),
                    Prefetch('images',
                             queryset=Image.objects.select_related(
                                 "course_offering",
                                 "course_offering__semester"))
                    ))

    def get_context_data(self, **kwargs):
        context = super(TeacherDetailView, self).get_context_data(**kwargs)
        teacher = context[self.context_object_name]
        if not teacher.is_teacher:
            raise Http404
        return context


@requires_csrf_token
def custom_page_not_found(request, exception, template_name='404.html'):
    return redirect('http://old.compsciclub.ru' + request.path)
