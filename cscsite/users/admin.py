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
        groups = [x.pk for x in cleaned_data.get('groups', [])]
        if self.instance.group.STUDENT_CENTER in groups \
           and enrollment_year is None:
            self.add_error('enrollment_year', ValidationError(
                _("CSCUser|enrollment year should be provided for students")))

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


class CSCUserStatusLogAdmin(admin.StackedInline):
    model = CSCUserStatusLog
    extra = 0
    readonly_fields = ('created', 'semester', 'status')

    def has_add_permission(self, request, obj=None):
        return False


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
    list_display = ('id', 'username', 'email', 'first_name', 'last_name',
        'is_staff')

    formfield_overrides = {
        db_models.TextField: {'widget': AdminRichTextAreaWidget},
    }

    fieldsets = [
        (None, {'fields': ('username', 'email', 'password')}),
        (_('Personal info'), {'fields': ['last_name', 'first_name',
                                         'patronymic', 'gender',
                                         'photo', 'note', 'private_contacts',
                                         'csc_review']}),
        (_('Permissions'), {'fields': ['is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions']}),
        (_('External services'), {'fields': ['yandex_id', 'stepic_id',
                                             'github_id']}),
        (_('Student info record'),
         {'fields': ['status', 'status_changed_at', 'enrollment_year',
                     'graduation_year', 'curriculum_year', 'areas_of_study',
                     'university', 'workplace', 'uni_year_at_enrollment',
                     'phone']}),
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
