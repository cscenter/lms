from django import forms
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from core.widgets import CKEditorWidget
from publications.models import ProjectPublication, ProjectPublicationAuthor


class ProjectAdminInline(admin.TabularInline):
    model = ProjectPublication.projects.through
    extra = 1
    raw_id_fields = ('project',)
    verbose_name = _("Related Project")
    verbose_name_plural = _("Projects")


class PublicationAuthorAdminInline(admin.TabularInline):
    raw_id_fields = ('user',)
    verbose_name = _("Author")
    verbose_name_plural = _("Authors")
    model = ProjectPublicationAuthor
    extra = 1


class ProjectPublicationAdminForm(forms.ModelForm):
    class Meta:
        model = ProjectPublication
        widgets = {
            'description': CKEditorWidget(),
        }
        fields = '__all__'


class ProjectPublicationAdmin(admin.ModelAdmin):
    form = ProjectPublicationAdminForm
    list_display = ("pk", "title")
    inlines = (ProjectAdminInline, PublicationAuthorAdminInline)
    exclude = ('projects', 'authors')


admin.site.register(ProjectPublication, ProjectPublicationAdmin)
