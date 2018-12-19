from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as _UserAdmin
from django.db import models as db_models
from django.utils.translation import ugettext_lazy as _
from import_export.admin import ImportMixin

from core.admin import RelatedSpecMixin
from core.widgets import AdminRichTextAreaWidget, AdminRelatedDropdownFilter
from learning.settings import AcademicRoles
from users.forms import UserCreationForm, UserChangeForm
from .import_export import UserRecordResource
from .models import User, EnrollmentCertificate, \
    OnlineCourseRecord, SHADCourseRecord, UserStatusLog


class UserStatusLogAdmin(RelatedSpecMixin, admin.TabularInline):
    model = UserStatusLog
    extra = 0
    readonly_fields = ('created', 'status')
    related_spec = {'select': ['semester', 'student']}

    def has_add_permission(self, request, **kwargs):
        return False


class OnlineCourseRecordAdmin(admin.StackedInline):
    model = OnlineCourseRecord
    extra = 0


class SHADCourseRecordInlineAdmin(admin.StackedInline):
    model = SHADCourseRecord
    extra = 0


class UserAdmin(_UserAdmin):
    add_form = UserCreationForm
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    form = UserChangeForm
    change_form_template = 'admin/user_change_form.html'
    ordering = ['last_name', 'first_name']
    inlines = [OnlineCourseRecordAdmin, SHADCourseRecordInlineAdmin,
               UserStatusLogAdmin]
    readonly_fields = ['comment_changed_at', 'comment_last_author',
                       'last_login', 'date_joined']
    list_display = ['id', 'username', 'email', 'first_name', 'last_name',
                    'is_staff']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'city', 'groups']

    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }

    fieldsets = [
        (None, {'fields': ('username', 'email', 'password')}),
        (_('Personal info'), {
            'fields': ['last_name', 'first_name', 'patronymic', 'workplace',
                       'gender', 'city', 'photo', 'note', 'private_contacts',
                       'csc_review']}),
        (_('Permissions'), {'fields': ['is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions']}),
        (_('External services'), {'fields': ['yandex_id', 'stepic_id',
                                             'github_id']}),
        (_('Student info record'),
         {'fields': ['status', 'enrollment_year',
                     'graduation_year', 'curriculum_year', 'areas_of_study',
                     'university', 'uni_year_at_enrollment', 'phone']}),
        (_("Curator's note"),
         {'fields': ['comment', 'comment_changed_at', 'comment_last_author']}),
        (_('Important dates'), {'fields': ['last_login', 'date_joined']})]

    def get_formsets_with_inlines(self, request, obj=None):
        """
        Yield formsets and the corresponding inlines.
        """
        if obj is None:
            return None
        for inline in self.get_inline_instances(request, obj):
            yield inline.get_formset(request, obj), inline

    def save_model(self, request, obj, form, change):
        if "comment" in form.changed_data:
            obj.comment_last_author = request.user
        super().save_model(request, obj, form, change)


class SHADCourseRecordAdmin(admin.ModelAdmin):
    list_display = ["name", "student", "grade"]
    list_filter = [
        "student__city",
        ("semester", AdminRelatedDropdownFilter)
    ]

    def formfield_for_foreignkey(self, db_field, *args, **kwargs):
        if db_field.name == "student":
            kwargs["queryset"] = User.objects.filter(groups__in=[
                AcademicRoles.STUDENT_CENTER,
                AcademicRoles.VOLUNTEER]).distinct()
        return super().formfield_for_foreignkey(db_field, *args, **kwargs)


class UserRecordResourceAdmin(ImportMixin, UserAdmin):
    resource_class = UserRecordResource
    import_template_name = 'admin/import_export/import_users.html'


class EnrollmentCertificateAdmin(admin.ModelAdmin):
    list_display = ["student", "created"]
    raw_id_fields = ["student"]


admin.site.register(User, UserRecordResourceAdmin)
admin.site.register(EnrollmentCertificate, EnrollmentCertificateAdmin)
admin.site.register(SHADCourseRecord, SHADCourseRecordAdmin)
