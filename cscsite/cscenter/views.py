from collections import Counter

from django.conf import settings
from django.contrib.auth import get_user_model
from django.views import generic

from core.models import Faq
from learning.models import Semester, CourseOffering, CourseOfferingTeacher
from users.models import CSCUser


class QAListView(generic.ListView):
    context_object_name = "faq"
    template_name = "faq.html"

    def get_queryset(self):
        return Faq.objects.filter(site=settings.CENTER_SITE_ID).order_by("sort")


class TestimonialsListView(generic.ListView):
    context_object_name = "testimonials"
    template_name = "testimonials.html"
    paginate_by = 10

    def get_queryset(self):
        return (CSCUser.objects
                .filter(groups=CSCUser.group_pks.GRADUATE_CENTER)
                .exclude(csc_review='').exclude(photo='')
                .prefetch_related("study_programs")
                .order_by("-graduation_year"))


class TeachersView(generic.ListView):
    template_name = "center_teacher_list.html"
    context_object_name = "teachers"

    def get_queryset(self):
        user_model = get_user_model()
        qs = (user_model.objects
              .filter(groups=user_model.group_pks.TEACHER_CENTER,
                      courseofferingteacher__roles=CourseOfferingTeacher.roles.lecturer)
              .distinct())
        return qs

    def get_context_data(self, **kwargs):
        context = super(TeachersView, self).get_context_data(**kwargs)
        semesters = list(Semester
                         .latest_academic_years(year_count=3)
                         .values_list("id", flat=True))
        active_lecturers = Counter(
            CourseOffering.objects.filter(semester__in=semesters)
            .values_list("teachers__pk", flat=True)
        )
        context["active"] = filter(lambda t: t.pk in active_lecturers,
                                   context[self.context_object_name])
        context["other"] = filter(lambda t: t.pk not in active_lecturers,
                                  context[self.context_object_name])
        return context
