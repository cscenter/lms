# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        # ('taggit', '0002_auto_20150218_1950'),
    ]

    operations = [
        migrations.AddField(
            model_name='borrow',
            name='student',
            field=models.ForeignKey(related_name='borrows', verbose_name='Borrow|student', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='book',
            name='read_by',
            field=models.ManyToManyField(related_name='books', verbose_name='read by', through='library.Borrow', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='book',
            name='tags',
            field=taggit.managers.TaggableManager(to='taggit.Tag', through='taggit.TaggedItem', help_text='A comma-separated list of tags.', verbose_name='Tags'),
            preserve_default=True,
        ),
    ]
