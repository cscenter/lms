# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0005_auto_20160323_1728'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicant',
            name='uuid',
            field=models.UUIDField(null=True, editable=False, blank=True),
        ),
        migrations.AlterField(
            model_name='exam',
            name='uuid',
            field=models.UUIDField(null=True, editable=False, blank=True),
        ),
        migrations.AlterField(
            model_name='test',
            name='uuid',
            field=models.UUIDField(null=True, editable=False, blank=True),
        ),
    ]
