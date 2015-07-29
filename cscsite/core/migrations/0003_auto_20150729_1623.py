# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_city'),
    ]

    operations = [
        migrations.AlterField(
            model_name='city',
            name='code',
            field=models.CharField(help_text="UN/LOCODE notification preferable <a href='http://www.unece.org/cefact/locode/service/location' target='_blank'>Hint</a>", max_length=6, serialize=False, verbose_name='Code', primary_key=True),
        ),
    ]
