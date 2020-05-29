from dal import autocomplete
from django import forms
from django.contrib import admin
from django.contrib.postgres.aggregates import ArrayAgg
from django.utils.translation import ugettext_lazy as _

from core.admin import meta
from info_blocks.models import InfoBlock, InfoBlockTag


class InfoBlockAdminForm(forms.ModelForm):
    class Meta:
        model = InfoBlock
        fields = '__all__'
        widgets = {
            'tags': autocomplete.TaggitSelect2(
                url='info_blocks_tags_autocomplete',
                attrs={"data-width": 'style'})
        }


@admin.register(InfoBlockTag)
class InfoBlockTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')


@admin.register(InfoBlock)
class InfoBlockAdmin(admin.ModelAdmin):
    form = InfoBlockAdminForm
    model = InfoBlock
    list_filter = ('site', 'tags')
    list_display = ('__str__', 'site', 'tag_list', 'sort')
    ordering = ('site',)
    sortable_by = ('site', 'tag_list', 'sort')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(tag_list=ArrayAgg('tags__name'))

    @meta(text=_("Infoblock Tags"))
    def tag_list(self, obj):
        return ', '.join(obj.tag_list)
