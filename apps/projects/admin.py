# -*- coding: utf-8 -*-
from dal_select2.widgets import Select2Multiple
from django.contrib import admin
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from import_export.admin import ExportMixin

from core.admin import meta
from core.filters import AdminRelatedDropdownFilter
from core.utils import queryset_iterator
from projects.import_export import ProjectStudentAdminRecordResource
from projects.models import Project, ProjectStudent, Report, Review, \
    ReportComment, Supervisor, ReportingPeriod, PracticeCriteria
from users.constants import Roles
from users.models import User


class ReviewersInline(admin.StackedInline):
    model = Project.reviewers.through


class ProjectStudentInline(admin.TabularInline):
    model = ProjectStudent
    extra = 0
    min_num = 0
    show_change_link = True
    fields = ('student', 'supervisor_grade', 'supervisor_review',
              'presentation_grade', 'final_grade')
    raw_id_fields = ('student',)

    def formfield_for_foreignkey(self, db_field, *args, **kwargs):
        if db_field.name == "student":
            kwargs["queryset"] = (User.objects
                                  .has_role(Roles.STUDENT, Roles.VOLUNTEER,
                                            Roles.GRADUATE)
                                  .distinct())
        return super().formfield_for_foreignkey(db_field, *args, **kwargs)


class ProjectsInline(admin.TabularInline):
    model = Project.supervisors.through
    raw_id_fields = ('project',)
    extra = 0


@admin.register(Supervisor)
class SupervisorAdmin(admin.ModelAdmin):
    model = Supervisor
    list_display = ("last_name", "first_name", "occupation")
    search_fields = ("last_name",)
    inlines = (ProjectsInline,)

    class Media:
        css = {
            'all': ('v2/css/django_admin.css',)
        }


class ReportingPeriodAdmin(admin.ModelAdmin):
    list_display = ('term', 'start_on', 'end_on', 'project_type')
    list_filter = [
        ('term', AdminRelatedDropdownFilter),
    ]
    exclude = ('branch',)


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
    raw_id_fields = ('parent',)

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "reviewers":
            kwargs["queryset"] = (
                User.objects
                    # FIXME: add curator role instread of checking is_staff
                    .filter(Q(group__role=Roles.PROJECT_REVIEWER) |
                            Q(is_staff=True))
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
    list_display = ('student', 'project', 'get_project_semester', 'final_grade')
    list_filter = ('project__branch', 'project__semester')
    search_fields = ["project__name"]
    raw_id_fields = ('student', 'project')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("student", "project",
                                 "project__semester")

    def get_export_queryset(self, request):
        # django-import-export 1.2.0 uses queryset .iterator() internally and
        # breaks .prefetch_related() optimization
        # https://github.com/django-import-export/django-import-export/issues/774
        return queryset_iterator(super().get_export_queryset(request)
                                 .select_related("project__branch")
                                 .prefetch_related("reports"))

    @meta(_("Semester"), admin_order_field="project__semester")
    def get_project_semester(self, obj):
        return obj.project.semester


class ReportCommentAdmin(admin.ModelAdmin):
    list_display = ["report", "author"]


class PracticeCriteriaAdmin(admin.ModelAdmin):
    list_display = ("review", "get_reviewer")

    @meta(_("Report Reviewer"), admin_order_field="review__reviewer")
    def get_reviewer(self, obj):
        return obj.review.reviewer


admin.site.register(ReportingPeriod, ReportingPeriodAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(ProjectStudent, ProjectStudentAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(PracticeCriteria, PracticeCriteriaAdmin)
admin.site.register(ReportComment, ReportCommentAdmin)
