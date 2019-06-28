from dal import autocomplete
from django import forms
from django.contrib import admin
from taggit.managers import TaggableManager

from announcements.models import Announcement, AnnouncementTag


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


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    form = AnnouncementForm
    list_display = ("name", "publish_start_at", "publish_end_at")
