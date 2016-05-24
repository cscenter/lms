# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0035_campaign_current'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicant',
            name='yandex_id',
            field=models.CharField(validators=[django.core.validators.RegexValidator(regex='^[^@]*$', message='Only the part before "@yandex.ru" is expected')], max_length=80, blank=True, help_text='Applicant|yandex_id', null=True, verbose_name='Yandex ID'),
        ),
    ]
