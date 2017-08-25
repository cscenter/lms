# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.db import models as db_models
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _
from sorl.thumbnail.admin import AdminImageMixin
from import_export.admin import ImportExportMixin, ImportMixin

from core.forms import AdminRichTextAreaWidget
from core.models import RelatedSpecMixin
from learning.settings import PARTICIPANT_GROUPS
from .models import CSCUser, CSCUserReference, \
    OnlineCourseRecord, SHADCourseRecord, CSCUserStatusLog
from .import_export import SHADCourseRecordResource, CSCUserRecordResource


class CSCUserCreationForm(UserCreationForm):
    class Meta:
        model = CSCUser
        # FIXME: Ok, it's really don't work.
        fields = ('username',)
        error_messages = {
            'duplicate_username': _("Username must be unique"),
        }

    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            self._meta.model._default_manager.get(username=username)
        except self._meta.model.DoesNotExist:
            return username
        raise ValidationError(self._meta.error_messages["duplicate_username"])


class CSCUserChangeForm(UserChangeForm):
    class Meta:
        fields = '__all__'
        model = CSCUser

    def clean(self):
        """XXX: we can't validate m2m like `groups` in Model.clean() method"""
        cleaned_data = super(CSCUserChangeForm, self).clean()
        enrollment_year = cleaned_data.get('enrollment_year')
        groups = {x.pk for x in cleaned_data.get('groups', [])}
        if self.instance.group.STUDENT_CENTER in groups:
            if enrollment_year is None:
                self.add_error('enrollment_year', ValidationError(
                    _("Enrollment year should be provided for students")))
        if groups.intersection({PARTICIPANT_GROUPS.STUDENT_CENTER,
                                PARTICIPANT_GROUPS.VOLUNTEER,
                                PARTICIPANT_GROUPS.GRADUATE_CENTER}):
            if not cleaned_data.get('city', ''):
                self.add_error('city', ValidationError(
                    _("Provide city for student")))

        if self.instance.group.VOLUNTEER in groups \
           and enrollment_year is None:
            self.add_error('enrollment_year', ValidationError(
                _("CSCUser|enrollment year should be provided for volunteers")))

        graduation_year = cleaned_data.get('graduation_year')
        if self.instance.group.GRADUATE_CENTER in groups \
           and graduation_year is None:
            self.add_error('graduation_year', ValidationError(
                _("CSCUser|graduation year should be provided for graduates")))

        if self.instance.group.VOLUNTEER in groups \
                and self.instance.group.STUDENT_CENTER in groups:
            self.add_error('groups', ValidationError(
                _("User can't be simultaneously in volunteer and student group")))

        if self.instance.group.GRADUATE_CENTER in groups \
                and self.instance.group.STUDENT_CENTER in groups:
            self.add_error('groups', ValidationError(
                _("User can't be simultaneously in graduate and student group")))


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


class CSCUserStatusLogAdmin(RelatedSpecMixin, admin.TabularInline):
    model = CSCUserStatusLog
    extra = 0
    readonly_fields = ('created', 'status')
    related_spec = {'select': ['semester', 'student']}

    def has_add_permission(self, request, obj=None):
        return False


    # FIXME: formfield_for_foreignkey creates additional queries :<
    # FIXME: Find out how to prevent of doing it (see ForeignKeyCacheMixin)


class OnlineCourseRecordAdmin(admin.StackedInline):
    model = OnlineCourseRecord
    extra = 0


class SHADCourseRecordInlineAdmin(admin.StackedInline):
    model = SHADCourseRecord
    extra = 0


class CSCUserAdmin(AdminImageMixin, UserAdmin):
    form = CSCUserChangeForm
    add_form = CSCUserCreationForm
    change_form_template = 'admin/user_change_form.html'
    ordering = ['last_name', 'first_name']
    inlines = [OnlineCourseRecordAdmin, SHADCourseRecordInlineAdmin,
               CSCUserStatusLogAdmin]
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

    def save_model(self, request, obj, form, change):
        if "comment" in form.changed_data:
            obj.comment_last_author = request.user
        super(CSCUserAdmin, self).save_model(request, obj, form, change)


class SHADCourseRecordResourceAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = SHADCourseRecordResource

    def formfield_for_foreignkey(self, db_field, *args, **kwargs):
        if db_field.name == "student":
            kwargs["queryset"] = CSCUser.objects.filter(groups__in=[
                PARTICIPANT_GROUPS.STUDENT_CENTER,
                PARTICIPANT_GROUPS.VOLUNTEER]).distinct()
        return super(SHADCourseRecordResourceAdmin,
                     self).formfield_for_foreignkey(db_field, *args, **kwargs)


class CSCUserRecordResourceAdmin(ImportMixin, CSCUserAdmin):
    resource_class = CSCUserRecordResource
    pass

admin.site.register(CSCUser, CSCUserRecordResourceAdmin)
admin.site.register(CSCUserReference)
admin.site.register(SHADCourseRecord, SHADCourseRecordResourceAdmin)
