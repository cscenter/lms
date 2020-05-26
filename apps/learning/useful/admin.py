from dal import autocomplete
from django import forms
from django.contrib import admin
from django.contrib.postgres.aggregates import ArrayAgg
from django.utils.translation import ugettext_lazy as _

from learning.useful.models import Useful, UsefulTag

admin.site.register(UsefulTag)


class UsefulAdminForm(forms.ModelForm):
    class Meta:
        model = Useful
        fields = '__all__'
        widgets = {
            'tags': autocomplete.TaggitSelect2(
                url='learning.useful:tags_autocomplete',
                attrs={"data-width": 'style'})
        }


@admin.register(Useful)
class UsefulAdmin(admin.ModelAdmin):
    form = UsefulAdminForm
    model = Useful
    list_filter = ('site', 'tags')
    list_display = ('__str__', 'site', 'tag_list', 'sort')
    ordering = ('site',)
    sortable_by = ('site', 'tag_list', 'sort')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(tag_list=ArrayAgg('tags__name'))

    def tag_list(self, obj):
        return ', '.join(obj.tag_list)

    tag_list.short_description = _("Useful Tags")
