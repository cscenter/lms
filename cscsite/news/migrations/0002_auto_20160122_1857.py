# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0001_initial'),
        ('news', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='news',
            name='author',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, editable=False, to=settings.AUTH_USER_MODEL, null=True, verbose_name='News|author'),
        ),
        migrations.AddField(
            model_name='news',
            name='city',
            field=models.ForeignKey(default=b'RU SPB', blank=True, to='core.City', null=True),
        ),
        migrations.AddField(
            model_name='news',
            name='site',
            field=models.ForeignKey(to='sites.Site'),
        ),
    ]
