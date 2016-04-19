# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0015_auto_20160418_1939'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicant',
            name='yandex_id_normalize',
            field=models.CharField(default='', help_text='Applicant|yandex_id_normalization', max_length=80, verbose_name='Yandex ID normalisation'),
            preserve_default=False,
        ),
    ]
