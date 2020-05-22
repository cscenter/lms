from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as _UserAdmin
from django.core.exceptions import ValidationError
from django.db import models as db_models
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from import_export.admin import ImportMixin

from core.admin import meta, BaseModelAdmin
from core.filters import AdminRelatedDropdownFilter
from core.widgets import AdminRichTextAreaWidget
from users.constants import Roles
from users.forms import UserCreationForm, UserChangeForm
from .import_export import UserRecordResource
from .models import User, EnrollmentCertificate, \
    OnlineCourseRecord, SHADCourseRecord, UserGroup, \
    StudentProfile, StudentStatusLog, StudentTypes


class OnlineCourseRecordAdmin(admin.StackedInline):
    model = OnlineCourseRecord
    extra = 0


class SHADCourseRecordInlineAdmin(admin.StackedInline):
    model = SHADCourseRecord
    extra = 0


class UserGroupForm(forms.ModelForm):
    """Form for adding new Course Access Roles view the Django Admin Panel."""

    class Meta:
        model = UserGroup
        fields = ('site', 'branch', 'role')

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data['user']
        site = cleaned_data['site']
        branch = cleaned_data.get('branch')
        permission_role = cleaned_data.get('role')
        if permission_role:
            permission_role = int(permission_role)
            if permission_role in {Roles.INVITED, Roles.VOLUNTEER, Roles.STUDENT}:
                profile_type = StudentTypes.from_permission_role(permission_role)
                student_profile = user.get_student_profile(
                    site, profile_type=profile_type)
                if not student_profile:
                    msg = _("Create Student Profile before assign student role")
                    self.add_error(None, ValidationError(msg))
                elif branch and branch.pk != student_profile.branch_id:
                    # TODO: add link to the student profile
                    msg = _("Selected branch does not match branch {} from "
                            "the student profile")
                    msg = msg.format(student_profile.branch)
                    self.add_error('branch', ValidationError(msg))
            # For student branch will be populated from the student profile
            if permission_role in {Roles.INVITED, Roles.VOLUNTEER} and not branch:
                msg = _("You have to specify branch for this role")
                self.add_error('branch', ValidationError(msg))
        if branch and branch.site_id != site.pk:
            msg = _("Assign branch relative to the selected site")
            self.add_error('branch', ValidationError(msg))


class UserGroupInlineAdmin(admin.TabularInline):
    form = UserGroupForm
    model = UserGroup
    extra = 0
    raw_id_fields = ('branch',)
    # readonly_fields = ('role', 'site', 'branch')
    insert_after_fieldset = _('Permissions')

    class Media:
        css = {
            'all': ('v2/css/django_admin.css',)
        }


class UserAdmin(_UserAdmin):
    add_form = UserCreationForm
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2',
                       'gender', 'branch'),
        }),
    )
    form = UserChangeForm
    change_form_template = 'admin/user_change_form.html'
    ordering = ['last_name', 'first_name']
    inlines = [OnlineCourseRecordAdmin, SHADCourseRecordInlineAdmin,
               UserGroupInlineAdmin]
    readonly_fields = ['comment_changed_at', 'comment_last_author',
                       'last_login', 'date_joined']
    list_display = ['id', 'username', 'email', 'first_name', 'last_name',
                    'is_staff']
    list_filter = ['is_active', 'branch', 'group__site', 'group__role',
                   'is_staff', 'is_superuser']
    filter_horizontal = []

    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }

    fieldsets = [
        (None, {'fields': ('username', 'email', 'password')}),
        (_('Personal info'), {
            'fields': ['gender', 'branch',
                       'last_name', 'first_name', 'patronymic', 'phone',
                       'workplace', 'photo', 'bio', 'private_contacts', 'social_networks']}),
        (_('Permissions'), {'fields': ['is_active', 'is_staff', 'is_superuser',
                                       ]}),
        (_('External services'), {'fields': ['yandex_login', 'stepic_id',
                                             'github_login', 'anytask_url']}),
        (_('Student info record [DEPRECATED, DONT EDIT THIS SECTION]'),
         {'fields': ['status', 'curriculum_year',
                     'university', 'uni_year_at_enrollment',
                     'academic_disciplines']}),
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


class StudentStatusLogAdminInline(admin.TabularInline):
    list_select_related = ['student_profile', 'entry_author']
    model = StudentStatusLog
    extra = 0
    show_change_link = True
    readonly_fields = ('get_semester', 'status', 'entry_author')
    ordering = ['-status_changed_at']

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @meta(_("Semester"))
    def get_semester(self, obj):
        from courses.utils import get_terms_in_range
        changed_at = obj.status_changed_at
        term = next(get_terms_in_range(changed_at, changed_at), None)
        return term.label if term else '-'


class StudentProfileAdmin(BaseModelAdmin):
    list_select_related = ['user', 'branch', 'branch__site']
    list_display = ('user', 'branch', 'status')
    list_filter = ('type', 'branch', 'site',)
    raw_id_fields = ('user', 'comment_last_author')
    search_fields = ['user__last_name']
    inlines = [StudentStatusLogAdminInline]
    fieldsets = [
        (None, {
            'fields': ['type', 'branch', 'user',
                       'status', 'year_of_admission', 'year_of_curriculum',
                       'university', 'level_of_education_on_admission',
                       'academic_disciplines']
        }),
        (_('Official Student Info'), {
            'fields': ['is_official_student', 'diploma_number',
                       'diploma_issued_on', 'diploma_issued_by']
        }),
        (_("Curator's note"), {
            'fields': ['comment', 'comment_changed_at', 'comment_last_author']
        }),
    ]

    class Media:
        css = {
            'all': ('v2/css/django_admin.css',)
        }

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and obj.pk:
            # TODO: add user change url
            return ['type', 'site', 'branch', 'year_of_admission',
                    'level_of_education_on_admission',
                    'comment_changed_at', 'comment_last_author',]
        return []

    def save_model(self, request, obj, form, change):
        if "comment" in form.changed_data:
            obj.comment_last_author = request.user
        if "status" in form.changed_data and obj.pk:
            log_entry = StudentStatusLog(status=form.cleaned_data['status'],
                                         student_profile=obj,
                                         entry_author=request.user)
            log_entry.save()
        super().save_model(request, obj, form, change)


class SHADCourseRecordAdmin(admin.ModelAdmin):
    list_display = ["name", "student", "grade"]
    list_filter = [
        "student__branch",
        ("semester", AdminRelatedDropdownFilter)
    ]
    raw_id_fields = ('student',)

    def get_readonly_fields(self, request, obj=None):
        return ('anytask_url',) if obj else []

    @meta(_("Anytask"))
    def anytask_url(self, obj):
        if obj.student_id and obj.student.anytask_url:
            url = obj.student.anytask_url
            return mark_safe(f"<a target='_blank' href='{url}'>Открыть профиль в новом окне</a>")
        return "-"


class UserRecordResourceAdmin(ImportMixin, UserAdmin):
    resource_class = UserRecordResource
    import_template_name = 'admin/import_export/import_users.html'


class EnrollmentCertificateAdmin(admin.ModelAdmin):
    list_display = ["student", "created"]
    raw_id_fields = ["student"]


admin.site.register(User, UserRecordResourceAdmin)
admin.site.register(StudentProfile, StudentProfileAdmin)
admin.site.register(EnrollmentCertificate, EnrollmentCertificateAdmin)
admin.site.register(SHADCourseRecord, SHADCourseRecordAdmin)
