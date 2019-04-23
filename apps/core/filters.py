from django.contrib.admin import RelatedFieldListFilter


class AdminRelatedDropdownFilter(RelatedFieldListFilter):
    template = 'admin/dropdown_listfilter.html'
