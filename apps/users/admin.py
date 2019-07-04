from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as _UserAdmin
from django.core.exceptions import ValidationError
from django.db import models as db_models
from django.utils.translation import ugettext_lazy as _
from import_export.admin import ImportMixin

from core.admin import RelatedSpecMixin
from core.widgets import AdminRichTextAreaWidget
from core.filters import AdminRelatedDropdownFilter
from users.constants import AcademicRoles
from users.forms import UserCreationForm, UserChangeForm
from users.groups import REGISTERED_ACCESS_ROLES
from .import_export import UserRecordResource
from .models import User, EnrollmentCertificate, \
    OnlineCourseRecord, SHADCourseRecord, UserStatusLog, UserGroup


class UserStatusLogAdmin(RelatedSpecMixin, admin.TabularInline):
    model = UserStatusLog
    extra = 0
    readonly_fields = ('created', 'status')
    related_spec = {'select': ['semester', 'student']}

    def has_add_permission(self, request, obj=None):
        return False


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
        fields = '__all__'

    # ACCESS_ROLES = [(role_name, _(cls.verbose_name)) for role_name, cls
    #                 in REGISTERED_ACCESS_ROLES.items()]
    # FIXME: Use registred roles
    ACCESS_ROLES = AcademicRoles.choices
    role = forms.ChoiceField(choices=ACCESS_ROLES)

    def clean(self):
        cleaned_data = super().clean()
        role = int(cleaned_data['role'])
        user = cleaned_data['user']
        if role == AcademicRoles.STUDENT_CENTER:
            if user.enrollment_year is None:
                msg = _("Enrollment year should be provided for students")
                self.add_error(None, ValidationError(msg))
        if role in {AcademicRoles.STUDENT_CENTER,
                    AcademicRoles.VOLUNTEER,
                    AcademicRoles.GRADUATE_CENTER}:
            if not user.city_id:
                msg = _("Provide city for student")
                self.add_error(None, ValidationError(msg))
        if role == AcademicRoles.VOLUNTEER:
            if user.enrollment_year is None:
                msg = _("CSCUser|enrollment year should be provided for "
                        "volunteers")
                self.add_error(None, ValidationError(msg))


class UserGroupInlineAdmin(admin.TabularInline):
    form = UserGroupForm
    model = UserGroup
    extra = 0
    # XXX: fieldset name should be unique and not None
    insert_after_fieldset = _('Permissions')


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
               UserStatusLogAdmin, UserGroupInlineAdmin]
    readonly_fields = ['comment_changed_at', 'comment_last_author',
                       'last_login', 'date_joined']
    list_display = ['id', 'username', 'email', 'first_name', 'last_name',
                    'is_staff']
    list_filter = ['is_active', 'city', 'group__site', 'group__role',
                   'is_staff', 'is_superuser']
    filter_horizontal = []

    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }

    fieldsets = [
        (None, {'fields': ('username', 'email', 'password')}),
        (_('Personal info'), {
            'fields': ['last_name', 'first_name', 'patronymic', 'workplace',
                       'gender', 'city', 'photo', 'bio', 'private_contacts']}),
        (_('Permissions'), {'fields': ['is_active', 'is_staff', 'is_superuser',
                                       ]}),
        (_('External services'), {'fields': ['yandex_id', 'stepic_id',
                                             'github_id']}),
        (_('Student info record'),
         {'fields': ['branch', 'status', 'enrollment_year', 'curriculum_year',
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
            kwargs["queryset"] = User.objects.filter(group__role__in=[
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
