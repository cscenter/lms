# -*- coding: utf-8 -*-

import tablib
from import_export import resources, fields, widgets

from .models import User


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


class UserRecordResource(resources.ModelResource):
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
            'email', 'username', 'last_name', 'first_name', 'patronymic',
            'gender', 'phone', 'yandex_login', 'stepic_id', 'github_login'
        )
        export_order = fields
        # m2m relationships won't be processed if imported fields
        # weren't changed
        skip_unchanged = False
        import_id_fields = ['email']

    def before_import(self, dataset: tablib.Dataset, using_transactions,
                      dry_run, **kwargs):
        if 'groups' not in dataset.headers:
            dataset.append_col(lambda row: '', header='groups')

    def before_save_instance(self, instance, using_transactions, dry_run):
        if not instance.username:
            instance.username = instance.email.split('@')[0]
        instance.set_password(raw_password=None)
