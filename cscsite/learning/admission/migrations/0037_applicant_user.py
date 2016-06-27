# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('admission', '0036_auto_20160524_1451'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicant',
            name='user',
            field=models.ForeignKey(related_name='+', on_delete=models.SET(django.db.models.deletion.SET_NULL), blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
    ]
