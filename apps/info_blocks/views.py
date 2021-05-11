from dal import autocomplete

from users.mixins import CuratorOnlyMixin

from .models import InfoBlockTag


class InfoBlockTagAutocomplete(CuratorOnlyMixin, autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = InfoBlockTag.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs.order_by('name')
