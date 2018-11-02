from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as _UserAdmin
from django.contrib.auth.forms import UserCreationForm as _UserCreationForm, \
    UserChangeForm as _UserChangeForm
from django.db import models as db_models
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _
from import_export.admin import ImportMixin

from core.models import RelatedSpecMixin
from core.widgets import AdminRichTextAreaWidget, AdminRelatedDropdownFilter
from learning.settings import AcademicRoles
from .import_export import UserRecordResource
from .models import User, EnrollmentCertificate, \
    OnlineCourseRecord, SHADCourseRecord, UserStatusLog


class UserCreationForm(_UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email')


class UserChangeForm(_UserChangeForm):
    class Meta:
        fields = '__all__'
        model = User

    def clean(self):
        """XXX: we can't validate m2m like `groups` in Model.clean() method"""
        cleaned_data = super().clean()
        enrollment_year = cleaned_data.get('enrollment_year')
        groups = {x.pk for x in cleaned_data.get('groups', [])}
        u: User = self.instance
        if u.roles.STUDENT_CENTER in groups:
            if enrollment_year is None:
                self.add_error('enrollment_year', ValidationError(
                    _("Enrollment year should be provided for students")))
        if groups.intersection({AcademicRoles.STUDENT_CENTER,
                                AcademicRoles.VOLUNTEER,
                                AcademicRoles.GRADUATE_CENTER}):
            if not cleaned_data.get('city', ''):
                self.add_error('city', ValidationError(
                    _("Provide city for student")))

        if u.roles.VOLUNTEER in groups and enrollment_year is None:
            self.add_error('enrollment_year', ValidationError(
                _("CSCUser|enrollment year should be provided for volunteers")))

        graduation_year = cleaned_data.get('graduation_year')
        if u.roles.GRADUATE_CENTER in groups and graduation_year is None:
            self.add_error('graduation_year', ValidationError(
                _("CSCUser|graduation year should be provided for graduates")))

        if u.roles.VOLUNTEER in groups and u.roles.STUDENT_CENTER in groups:
            msg = _("User can't be volunteer and student at the same time")
            self.add_error('groups', ValidationError(msg))

        if u.roles.GRADUATE_CENTER in groups and u.roles.STUDENT_CENTER in groups:
            msg = _("User can't be graduated and student at the same time")
            self.add_error('groups', ValidationError(msg))


class ForeignKeyCacheMixin(object):
    """
    Cache foreignkey choices in the request object to prevent unnecessary queries.
    """

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        formfield = super(ForeignKeyCacheMixin, self).formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name != 'semester':
            return formfield
        cache = getattr(request, 'db_field_cache', {})
        if cache.get(db_field.name):
            formfield.choices = cache[db_field.name]
        else:
            formfield.choices.field.cache_choices = True
            formfield.choices.field.choice_cache = [
                formfield.choices.choice(obj) for obj in
                formfield.choices.queryset.all()
            ]
            request.db_field_cache = cache
            request.db_field_cache[db_field.name] = formfield.choices
        return formfield


class UserStatusLogAdmin(RelatedSpecMixin, admin.TabularInline):
    model = UserStatusLog
    extra = 0
    readonly_fields = ('created', 'status')
    related_spec = {'select': ['semester', 'student']}

    # Uncomment on Django > 2.1.0
    # https://code.djangoproject.com/ticket/29637
    # def has_add_permission(self, request):
    #     return False


    # FIXME: formfield_for_foreignkey creates additional queries :<
    # FIXME: Find out how to prevent of doing it (see ForeignKeyCacheMixin)


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
