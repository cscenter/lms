# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EnrollmentApplEmail',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('email', models.EmailField(max_length=254, verbose_name='email')),
                ('is_notified', models.BooleanField(default=False, verbose_name='User is notified')),
            ],
            options={
                'ordering': ['email'],
                'verbose_name': 'Enrollment application email',
                'verbose_name_plural': 'Enrollment application emails',
            },
        ),
    ]
