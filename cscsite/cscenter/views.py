from django.conf import settings
from django.views import generic

from core.models import Faq
from users.models import CSCUser


class QAListView(generic.ListView):
    context_object_name = "faq"
    template_name = "faq.html"

    def get_queryset(self):
        return Faq.objects.filter(site=settings.CENTER_SITE_ID).order_by("sort")


class TestimonialsListView(generic.ListView):
    context_object_name = "testimonials"
    template_name = "testimonials.html"

    def get_queryset(self):
        return (CSCUser.objects
                .filter(groups=CSCUser.group_pks.GRADUATE_CENTER)
                .exclude(csc_review='').exclude(photo='')
                .prefetch_related("study_programs")
                .order_by("-graduation_year"))
