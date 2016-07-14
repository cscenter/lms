from django.contrib import admin

from learning.projects.models import StudentProject


class StudentProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'project_type', 'semester', 'grade']
    list_filter = ['semester']

admin.site.register(StudentProject, StudentProjectAdmin)
