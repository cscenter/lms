from django.contrib import admin

from learning.projects.models import Project, ProjectStudent
from learning.settings import PARTICIPANT_GROUPS
from users.models import CSCUser


class ProjectStudentInline(admin.TabularInline):
    model = ProjectStudent
    extra = 0
    min_num = 1

    def formfield_for_foreignkey(self, db_field, *args, **kwargs):
        if db_field.name == "student":
            kwargs["queryset"] = CSCUser.objects.filter(groups__in=[
                PARTICIPANT_GROUPS.STUDENT_CENTER,
                PARTICIPANT_GROUPS.GRADUATE_CENTER]).distinct()
        return super(ProjectStudentInline,
                     self).formfield_for_foreignkey(db_field, *args, **kwargs)


class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'project_type', 'semester']
    list_filter = ['semester']
    inlines = [ProjectStudentInline]

admin.site.register(Project, ProjectAdmin)
