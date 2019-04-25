# -*- coding: utf-8 -*-
from dal_select2.widgets import Select2Multiple
from django.contrib import admin
from django.db import models
from django.urls import reverse
from django.db.models import Q
from django.utils.safestring import mark_safe

from django.utils.translation import ugettext_lazy as _
from import_export.admin import ExportMixin

from core.admin import meta
from core.filters import AdminRelatedDropdownFilter
from learning.projects.import_export import ProjectStudentAdminRecordResource
from learning.projects.models import Project, ProjectStudent, Report, Review, \
    ReportComment, Supervisor
from users.constants import AcademicRoles
from users.models import User


class ReviewersInline(admin.StackedInline):
    model = Project.reviewers.through


class ProjectStudentInline(admin.TabularInline):
    model = ProjectStudent
    extra = 0
    min_num = 0
    show_change_link = True
    readonly_fields = ["get_report_score", "get_total_score"]
    fields = ('student', 'get_report_score', 'supervisor_grade',
              'supervisor_review', 'presentation_grade', 'get_total_score',
              'final_grade')
    
    def get_total_score(self, obj):
        return obj.total_score
    get_total_score.short_description = "Сумма"

    def get_report_score(self, obj):
        return obj.report.final_score
    get_report_score.short_description = "Отчет"

    def formfield_for_foreignkey(self, db_field, *args, **kwargs):
        if db_field.name == "student":
            kwargs["queryset"] = User.objects.filter(groups__in=[
                AcademicRoles.STUDENT_CENTER,
                AcademicRoles.GRADUATE_CENTER]).distinct()
        return super(ProjectStudentInline,
                     self).formfield_for_foreignkey(db_field, *args, **kwargs)


class ProjectsInline(admin.TabularInline):
    model = Project.supervisors.through
    extra = 0


@admin.register(Supervisor)
class SupervisorAdmin(admin.ModelAdmin):
    model = Supervisor
    list_display = ("full_name", "workplace")
    search_fields = ("full_name",)
    inlines = (ProjectsInline,)

    class Media:
        css = {
            'all': ('v2/css/django_admin.css',)
        }


class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'project_type', 'semester']
    list_filter = [
        ('semester', AdminRelatedDropdownFilter),
    ]
    search_fields = ["name"]
    inlines = [ProjectStudentInline]
    readonly_fields = ("supervisor_presentation_slideshare_url",
                       "presentation_slideshare_url")
    formfield_overrides = {
        models.ManyToManyField: {
            'widget': Select2Multiple(attrs={"data-width": 'style'})
        }
    }

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "reviewers":
            kwargs["queryset"] = (
                User.objects
                    .filter(Q(groups=AcademicRoles.PROJECT_REVIEWER) |
                            Q(is_superuser=True, is_staff=True))
                    .distinct())
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class ReportAdmin(admin.ModelAdmin):
    list_select_related = ["project_student", "project_student__project",
                           "project_student__student"]
    list_display = ['get_student_name', 'get_project_name', 'status']
    list_filter = ['status']
    raw_id_fields = ["project_student"]

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
    raw_id_fields = ["report", "reviewer"]

    def get_project_name(self, instance):
        return instance.report.project_student.project.name
    get_project_name.short_description = _("Project")


class ProjectStudentAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = ProjectStudentAdminRecordResource
    list_display = ['student', 'project', 'get_project_semester',
                    'get_total_score', 'final_grade']
    list_filter = ['project__city', 'project__semester']
    search_fields = ["project__name"]
    readonly_fields = ["report_link"]

    def get_queryset(self, request):
        qs = super(ProjectStudentAdmin, self).get_queryset(request)
        return qs.select_related("report", "student", "project",
                                 "project__semester")

    @meta(_("Сумма"))
    def get_total_score(self, obj):
        return obj.total_score

    @meta(_("Semester"), admin_order_field="project__semester")
    def get_project_semester(self, obj):
        return obj.project.semester

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
