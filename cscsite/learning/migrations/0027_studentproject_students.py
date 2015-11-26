# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('learning', '0026_auto_20151126_1636'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentproject',
            name='students',
            field=models.ManyToManyField(related_name='students_set', verbose_name='Students', to=settings.AUTH_USER_MODEL),
        ),
    ]
