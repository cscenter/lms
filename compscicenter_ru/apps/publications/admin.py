from django import forms
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from core.widgets import CKEditorWidget
from publications.models import ProjectPublication, ProjectPublicationAuthor


class ProjectAdminInline(admin.TabularInline):
    model = ProjectPublication.projects.through
    extra = 0
    raw_id_fields = ('project',)
    verbose_name = _("Related Project")
    verbose_name_plural = _("Projects")


class PublicationAuthorAdminInline(admin.TabularInline):
    raw_id_fields = ('user',)
    verbose_name = _("Author")
    verbose_name_plural = _("Authors")
    model = ProjectPublicationAuthor
    extra = 0

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("user", "project_publication")


class ProjectPublicationAdminForm(forms.ModelForm):
    class Meta:
        model = ProjectPublication
        widgets = {
            'description': CKEditorWidget(),
        }
        fields = '__all__'


class ProjectPublicationAdmin(admin.ModelAdmin):
    form = ProjectPublicationAdminForm
    list_display = ("title", "slug")
    inlines = (ProjectAdminInline, PublicationAuthorAdminInline)
    # FIXME: select2 instead?
    exclude = ('projects', 'authors')

    class Media:
        css = {
            'all': ('v2/css/django_admin.css',)
        }

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        p = form.instance.projects.first()
        publication_type = p.project_type if p else ''
        if form.instance.type != publication_type:
            (ProjectPublication.objects
             .filter(pk=form.instance.pk)
             .update(type=publication_type))


admin.site.register(ProjectPublication, ProjectPublicationAdmin)
