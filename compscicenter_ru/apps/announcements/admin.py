from dal import autocomplete
from dal_select2.widgets import Select2Multiple
from django import forms
from django.contrib import admin
from django.db import models
from django.utils.translation import ugettext_lazy as _

from announcements.models import Announcement, AnnouncementTag, \
    AnnouncementEventDetails


@admin.register(AnnouncementTag)
class AnnouncementTagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = '__all__'
        widgets = {
            'tags': autocomplete.TaggitSelect2(
                url='announcements:tags_autocomplete',
                attrs={"data-width": 'style'})
        }


class AnnouncementEventDetailsInline(admin.StackedInline):
    model = AnnouncementEventDetails
    extra = 0
    verbose_name = _("Announcement Details")
    verbose_name_plural = _("Announcement Details")
    formfield_overrides = {
        models.ManyToManyField: {
            'widget': Select2Multiple(attrs={"data-width": 'style'})
        }
    }


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    form = AnnouncementForm
    list_display = ("name", "publish_start_at", "publish_end_at")
    inlines = (AnnouncementEventDetailsInline,)

    class Media:
        css = {
            "all": ("v2/css/hide_timezone_warnings.css",)
        }
