# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0016_applicant_yandex_id_normalize'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicant',
            name='yandex_id_normalize',
            field=models.CharField(help_text='Applicant|yandex_id_normalization', verbose_name='Yandex ID normalisation', max_length=80, editable=False),
        ),
    ]
