from dal_select2.widgets import Select2Multiple
from import_export.admin import ImportMixin

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as _UserAdmin
from django.core.exceptions import ValidationError
from django.db import models as db_models, models
from django.utils import formats
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from core.admin import BaseModelAdmin, meta
from core.filters import AdminRelatedDropdownFilter
from core.widgets import AdminRichTextAreaWidget
from learning.settings import StudentStatuses
from users.constants import Roles, student_permission_roles
from users.forms import UserChangeForm, UserCreationForm

from .import_export import UserRecordResource
from .models import (
    CertificateOfParticipation, OnlineCourseRecord, SHADCourseRecord, StudentProfile,
    StudentStatusLog, StudentTypes, User, UserConsent, UserGroup, YandexUserData, StudentFieldLog, StudentAcademicDisciplineLog,
    PartnerTag
)
from .services import assign_role, update_student_status, update_student_academic_discipline


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
            if permission_role in student_permission_roles:
                profile_type = StudentTypes.from_permission_role(permission_role)
                student_profile = user.get_student_profile(
                    site, profile_type=profile_type)
                if not student_profile:
                    msg = _("Create Student Profile before adding student "
                            "permissions")
                    self.add_error(None, ValidationError(msg))
                elif branch and branch.pk != student_profile.branch_id:
                    # TODO: add link to the student profile
                    msg = _("Selected branch does not match branch {} from "
                            "the student profile")
                    msg = msg.format(student_profile.branch)
                    self.add_error('branch', ValidationError(msg))
            # FIXME: Lame. Later you could remove user.branch value
            if permission_role == Roles.TEACHER and not user.branch_id:
                msg = _("You have to specify branch for user before "
                        "adding teacher permissions")
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


class YandexUserDataInlineAdmin(admin.StackedInline):
    model = YandexUserData
    fk_name = 'user'
    extra = 0
    fields = ['uid', 'login', 'display_name', 'changed_by', 'modified_at']
    readonly_fields = ['user', 'uid', 'changed_by', 'modified_at']
    exclude = ['first_name', 'last_name', 'real_name']
    can_delete = True

    def has_add_permission(self, request, obj=None):
        return False

class UserConsentInlineAdmin(admin.TabularInline):
    model = UserConsent
    extra = 0
    readonly_fields = ['type', 'created']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

class UserAdmin(_UserAdmin):
    add_form = UserCreationForm
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2',
                       'gender', 'time_zone', 'branch'),
        }),
    )
    form = UserChangeForm
    change_form_template = 'admin/user_change_form.html'
    ordering = ['last_name', 'first_name']
    inlines = [UserConsentInlineAdmin, YandexUserDataInlineAdmin, OnlineCourseRecordAdmin, SHADCourseRecordInlineAdmin,
               UserGroupInlineAdmin]
    readonly_fields = ['last_login', 'date_joined']
    list_display = ['id', 'username', 'email', 'first_name', 'last_name',
                    'is_staff']
    list_filter = ['is_active', 'branch', 'group__site', 'group__role',
                   'is_staff', 'is_superuser']
    filter_horizontal = []
    search_fields = ('username', 'first_name', 'last_name', 'patronymic', 'email', 'telegram_username',
                     'yandex_login', 'yandex_login_normalized')

    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }

    fieldsets = [
        (None, {'fields': ('username', 'email', 'password')}),
        (_('Personal info'), {
            'fields': ['gender', 'birth_date', 'branch',
                       'last_name', 'first_name', 'patronymic', 'phone',
                       'workplace', 'living_place', 'photo', 'bio', 'private_contacts',
                       'social_networks', 'badge_number', 'time_zone']}),
        (_('Permissions'), {'fields': ['is_active', 'is_staff', 'is_superuser',
                                       ]}),
        (_('External services'), {'fields': ['telegram_username',
                                             'yandex_login', 'stepic_id',
                                             'github_login', 'anytask_url',
                                             'codeforces_login']}),
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

    def save_formset(self, request, form, formset, change):
        for form in formset.forms:
            if isinstance(form.instance, YandexUserData):
                obj = form.instance
                obj.changed_by = request.user
                obj.save()
        formset.save()
        
    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if search_term.startswith("@"):
            queryset |= self.model.objects.filter(telegram_username=search_term[1:])
        return queryset, use_distinct

class StudentFieldLogAdminInline(admin.TabularInline):
    list_select_related = ['student_profile', 'entry_author']
    model = StudentFieldLog
    extra = 0
    readonly_fields = ('student_profile', 'entry_author', 'is_processed', 'processed_at')

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class StudentStatusLogAdminInline(StudentFieldLogAdminInline):
    model = StudentStatusLog
    readonly_fields = StudentFieldLogAdminInline.readonly_fields + ('former_status', 'status')

class StudentAcademicDisciplineLogAdminInline(StudentFieldLogAdminInline):
    model = StudentAcademicDisciplineLog
    readonly_fields = StudentFieldLogAdminInline.readonly_fields + ('former_academic_discipline', 'academic_discipline')


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        profile_type = cleaned_data.get('type')
        invitation = cleaned_data.get('invitation')
        user = cleaned_data.get('user')
        branch = cleaned_data.get('branch')
        year_of_admission = cleaned_data.get('year_of_admission')
        required_for_validation = [user, branch, year_of_admission]
        if all(f for f in required_for_validation):
            # Show user-friendly error if unique constraint is failed
            if profile_type == StudentTypes.REGULAR:
                profile = (StudentProfile.objects
                           .filter(user=user, branch=branch,
                                   type=StudentTypes.REGULAR,
                                   year_of_admission=year_of_admission))
                if profile.exists():
                    msg = _('Regular student profile already exists for this '
                            'admission campaign year.')
                    self.add_error('year_of_admission', ValidationError(msg))
        if profile_type == StudentTypes.INVITED and invitation is None:
            msg = _('Student profile with type INVITED must have invitation')
            self.add_error('invitation', ValidationError(msg))


class StudentProfileAdmin(BaseModelAdmin):
    form = StudentProfileForm
    list_select_related = ['user', 'branch', 'branch__site']
    list_display = ('user', 'branch', 'type', 'year_of_admission', 'status', 'priority')
    list_filter = ('type', 'site', 'branch', 'status',)
    raw_id_fields = ('user', 'comment_last_author', 'invitation')
    search_fields = ['user__last_name']
    inlines = [StudentStatusLogAdminInline, StudentAcademicDisciplineLogAdminInline]
    formfield_overrides = {
        models.ManyToManyField: {
            "widget": Select2Multiple(attrs={"data-width": "style"})
        }
    }

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and obj.pk:
            # TODO: add user change url
            return ['type', 'site', 'year_of_admission', 'birth_date',
                    'comment_changed_at', 'comment_last_author', 'invitation']
        return ['birth_date']

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (None, {
                'fields': ['type', 'is_paid_basis', 'new_track', 'branch', 'user', 'university', 'partner', 'faculty',
                           'level_of_education_on_admission', 'level_of_education_on_admission_other',
                           'diploma_degree', 'graduation_year',
                           'year_of_admission', 'year_of_curriculum', 'invitation']
            }),
            (_('Official Student Info'), {
                'fields': ['is_official_student', 'birth_date',
                           'diploma_number', 'diploma_issued_on', 'diploma_issued_by', 'snils']
            }),
            (_("Curator's note"), {
                'fields': ['comment', 'comment_changed_at', 'comment_last_author']
            }),
        ]
        graduate_statuses = {StudentStatuses.GRADUATE, StudentStatuses.WILL_GRADUATE}

        if obj:
            fields: list[str, ...] = fieldsets[0][1]['fields']
            # Status and academic discipline logs work correctly only if object exists
            fields.insert(fields.index('university'), 'status')
            fields.insert(fields.index('invitation'), 'academic_disciplines')
            if obj.status in graduate_statuses:
                fields.insert(fields.index('status'), 'graduate_without_diploma')

        return fieldsets

    def save_model(self, request, obj: StudentProfile,
                   form: StudentProfileForm, change: bool) -> None:
        if "comment" in form.changed_data:
            obj.comment_last_author = request.user
        if change:
            if "status" in form.changed_data:
                update_student_status(obj, new_status=form.cleaned_data['status'],
                                      editor=request.user)
            if "academic_disciplines" in form.changed_data:
                update_student_academic_discipline(obj, new_academic_discipline=form.cleaned_data[
                    'academic_disciplines'].first(),
                                      editor=request.user)
        super().save_model(request, obj, form, change)
        if not change and obj.status not in StudentStatuses.inactive_statuses:
            permission_role = StudentTypes.to_permission_role(obj.type)
            assign_role(account=obj.user, role=permission_role, site=obj.site)

    @admin.display(description=_("Date of Birth"))
    def birth_date(self, obj):
        if obj.user_id and obj.user.birth_date:
            d = formats.date_format(obj.user.birth_date, 'd.m.Y')
            return mark_safe(d)
        return "Не указана"


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


class CertificateOfParticipationAdmin(admin.ModelAdmin):
    list_display = ["student_profile", "created"]
    raw_id_fields = ["student_profile"]

class PartnerTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')


admin.site.register(User, UserRecordResourceAdmin)
admin.site.register(StudentProfile, StudentProfileAdmin)
admin.site.register(CertificateOfParticipation, CertificateOfParticipationAdmin)
admin.site.register(SHADCourseRecord, SHADCourseRecordAdmin)
admin.site.register(PartnerTag, PartnerTagAdmin)
