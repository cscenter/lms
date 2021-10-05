from django_filters import BaseInFilter, CharFilter, NumberFilter

from django.contrib.admin import RelatedFieldListFilter


class AdminRelatedDropdownFilter(RelatedFieldListFilter):
    template = 'admin/dropdown_listfilter.html'


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class CharInFilter(BaseInFilter, CharFilter):
    pass
