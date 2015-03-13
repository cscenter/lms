# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0008_data_add_studyprograms_again'),
    ]

    operations = [
        migrations.AlterField(
            model_name='city',
            name='code',
            field=models.CharField(help_text='This should be UN/LOCODE, e.g. "RU LED"', max_length=6, serialize=False, verbose_name='PK|Code', primary_key=True),
            preserve_default=True,
        ),
    ]
