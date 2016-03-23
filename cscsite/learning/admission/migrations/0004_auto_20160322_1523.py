# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0003_auto_20160317_1953'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicant',
            name='has_job',
            field=models.CharField(help_text='Applicant|has_job', max_length=10, null=True, verbose_name='Do you work?', blank=True),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='motivation',
            field=models.TextField(help_text='Applicant|motivation_why', null=True, verbose_name='Your motivation', blank=True),
        ),
    ]
