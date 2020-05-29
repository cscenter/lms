from dal import autocomplete
from django.conf import settings
from django.views import generic

from auth.mixins import PermissionRequiredMixin
from info_blocks.models import InfoBlock, CurrentInfoBlockTags
from users.mixins import CuratorOnlyMixin
from .models import InfoBlockTag


class InfoBlockTagAutocomplete(CuratorOnlyMixin, autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = InfoBlockTag.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs


class UsefulListView(PermissionRequiredMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "info_blocks/useful.html"
    permission_required = "study.view_faq"

    def get_queryset(self):
        return (InfoBlock.objects
                .for_site(settings.SITE_ID)
                .with_tag(CurrentInfoBlockTags.USEFUL)
                .order_by("sort"))


class InternshipListView(PermissionRequiredMixin, generic.ListView):
    context_object_name = "faq"
    template_name = "info_blocks/internships.html"
    permission_required = "study.view_internships"

    def get_queryset(self):
        return (InfoBlock.objects
                .for_site(settings.SITE_ID)
                .with_tag(CurrentInfoBlockTags.INTERNSHIP)
                .order_by("sort"))


class HonorCodeView(generic.ListView):
    context_object_name = "faq"
    template_name = "info_blocks/honor_code.html"

    def get_queryset(self):
        return (InfoBlock.objects
                .for_site(settings.SITE_ID)
                .with_tag(CurrentInfoBlockTags.HONOR_CODE)
                .order_by("sort"))
