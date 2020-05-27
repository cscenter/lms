from dal import autocomplete
from django.conf import settings
from django.views import generic

from auth.mixins import PermissionRequiredMixin
from useful.models import Useful, CurrentUsefulTags
from .models import UsefulTag


class UsefulTagAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = UsefulTag.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class UsefulListView(PermissionRequiredMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "learning/study/useful.html"
    permission_required = "study.view_faq"

    def get_queryset(self):
        return (Useful.objects
                .for_site(settings.SITE_ID)
                .with_tag(CurrentUsefulTags.USEFUL)
                .order_by("sort"))


class InternshipListView(PermissionRequiredMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "learning/study/internships.html"
    permission_required = "study.view_internships"

    def get_queryset(self):
        return (Useful.objects
                .for_site(settings.SITE_ID)
                .with_tag(CurrentUsefulTags.INTERNSHIP)
                .order_by("sort"))


class HonorCodeView(generic.ListView):
    context_object_name = "faq"
    template_name = "learning/study/honor_code.html"

    def get_queryset(self):
        return (Useful.objects
                .for_site(settings.SITE_ID)
                .with_tag(CurrentUsefulTags.HONOR_CODE)
                .order_by("sort"))
