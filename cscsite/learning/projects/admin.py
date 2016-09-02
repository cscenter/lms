# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

from django.utils.translation import ugettext_lazy as _

from learning.projects.models import Project, ProjectStudent, Report, Review, \
    ReportComment
from learning.settings import PARTICIPANT_GROUPS
from users.models import CSCUser


class ReviewersInline(admin.StackedInline):
    model = Project.reviewers.through


class ProjectStudentInline(admin.TabularInline):
    model = ProjectStudent
    extra = 0
    min_num = 1
    show_change_link = True

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


class ReportAdmin(admin.ModelAdmin):
    list_select_related = ["project_student", "project_student__project"]
    list_display = ['get_student_name', 'get_project_name', 'status']
    list_filter = ['status']

    def get_student_name(self, instance):
        return instance.project_student.student
    get_student_name.short_description = _("Student")

    def get_project_name(self, instance):
        return instance.project_student.project
    get_project_name.short_description = _("Project")

    def formfield_for_foreignkey(self, db_field, *args, **kwargs):
        if db_field.name == "project_student":
            kwargs["queryset"] = (ProjectStudent.objects
                                  .select_related("project", "student")
                                  .order_by("project__name"))
        return super(ReportAdmin,
                     self).formfield_for_foreignkey(db_field, *args, **kwargs)


class ReviewAdmin(admin.ModelAdmin):
    list_filter = ['is_completed']
    list_display = ['reviewer', 'report', 'get_project_name', 'is_completed']

    def get_project_name(self, instance):
        return instance.report.project_student.project.name
    get_project_name.short_description = _("Project")


class ProjectStudentAdmin(admin.ModelAdmin):
    list_display = ['student', 'project', 'get_project_semester', 'final_grade']
    search_fields = ["project__name"]
    readonly_fields = ["report_link"]

    def get_project_semester(self, obj):
        return obj.project.semester
    get_project_semester.short_description = _("Semester")
    get_project_semester.admin_order_field = 'project__semester'

    def report_link(self, instance):
        url = reverse('admin:%s_%s_change' % (instance.report._meta.app_label,
                                              instance.report._meta.model_name),
                      args=(instance.report.id,))
        return mark_safe('<a href="{}">{}</a>'.format(url, _("Edit")))


class ReportCommentAdmin(admin.ModelAdmin):
    list_display = ["report", "author"]

admin.site.register(Project, ProjectAdmin)
admin.site.register(ProjectStudent, ProjectStudentAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(ReportComment, ReportCommentAdmin)
