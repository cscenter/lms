# -*- coding: utf-8 -*-

import tablib
from django.core.exceptions import ValidationError
from import_export import resources, fields, widgets

from learning.settings import AcademicDegreeYears
from core.timezone import now_local
from users.constants import AcademicRoles
from .models import User, Group


class AcademicDegreeYearWidget(widgets.IntegerWidget):
    def clean(self, label, row=None, *args, **kwargs):
        if self.is_empty(label):
            return None
        # Key values depend on activated language, aggregate at runtime
        # TODO: seems translation should works even with class attribute. Write test to prove it
        mapping = {v.lower(): k for k, v in AcademicDegreeYears.values.items()}
        # Replace non-breaking space and tabs with common white space
        label = label.replace(u'\xa0', u' ')
        if label in mapping:
            return mapping[label]
        raise ValueError(f'Course should be one of {mapping}')

    def render(self, value, obj=None):
        return AcademicDegreeYears.values[value]


class UserEmailWidget(widgets.CharWidget):
    def clean(self, value, row=None, *args, **kwargs):
        # Check email is unique
        if '@' not in value:
            raise ValueError('Wrong email')
        return value.strip()

    def render(self, value, obj=None):
        return value


class UserGenderWidget(widgets.CharWidget):
    def clean(self, value, row=None, *args, **kwargs):
        value = value.strip().lower()
        if value in ["м", "m", "male"]:
            return "M"
        elif value in ["ж", "f", "female"]:
            return "F"
        raise ValueError('UserGenderWidget: supported values ["m", "f"]')

    def render(self, value, obj=None):
        if value == "M":
            return "муж"
        elif value == "F":
            return "жен"
        return value


class GroupManyToManyWidget(widgets.ManyToManyWidget):
    def clean(self, value, row=None, *args, **kwargs):
        if not value:
            return self.model.objects.filter(pk=AcademicRoles.VOLUNTEER)
        return super().clean(value, row, *args, **kwargs)

    def render(self, value, obj=None):
        ids = [obj.name for obj in value.all()]
        return self.separator.join(ids)


class UserRecordResource(resources.ModelResource):
    course = fields.Field(column_name='course',
                          attribute='uni_year_at_enrollment',
                          widget=AcademicDegreeYearWidget())
    email = fields.Field(column_name='email',
                         attribute='email',
                         widget=UserEmailWidget())
    gender = fields.Field(column_name='gender',
                          attribute='gender',
                          widget=UserGenderWidget())
    # FIXME: add groups back

    class Meta:
        model = User
        fields = (
            'email', 'username', 'status', 'last_name', 'first_name',
            'patronymic', 'gender', 'city', 'phone', 'university', 'course',
            'comment', 'yandex_id', 'stepic_id', 'github_id'
        )
        export_order = fields
        # m2m relationships won't be processed if imported fields
        # weren't changed
        skip_unchanged = False
        import_id_fields = ['email']

    def __init__(self):
        super().__init__()
        self.fields['status'].readonly = True

    def before_import(self, dataset: tablib.Dataset, using_transactions,
                      dry_run, **kwargs):
        if 'groups' not in dataset.headers:
            dataset.append_col(lambda row: '', header='groups')

    def before_import_row(self, row, **kwargs):
        if not row.get('city'):
            raise ValidationError("Value for `city` column is mandatory")

    def before_save_instance(self, instance, using_transactions, dry_run):
        if not instance.username:
            instance.username = instance.email.split('@')[0]
        if not instance.enrollment_year:
            instance.enrollment_year = now_local(instance.city_id).year
        instance.status = ''
        instance.set_password(raw_password=None)
