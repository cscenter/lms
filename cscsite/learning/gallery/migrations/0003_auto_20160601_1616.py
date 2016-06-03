# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
import mptt.fields
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('gallery', '0002_auto_20160601_1354'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='album',
            options={'ordering': ('order', 'name'), 'verbose_name': 'Album', 'verbose_name_plural': 'Albums'},
        ),
        migrations.AddField(
            model_name='album',
            name='slug',
            field=models.SlugField(default=datetime.datetime(2016, 6, 1, 13, 16, 8, 604598, tzinfo=utc), max_length=70, help_text='Short name in ASCII, used in images upload path', unique=True, verbose_name='Slug'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='album',
            name='parent',
            field=mptt.fields.TreeForeignKey(related_name='children', blank=True, to='gallery.Album', help_text='Parent album', null=True, verbose_name='Parent'),
        ),
        migrations.AlterField(
            model_name='album',
            name='semester',
            field=models.ForeignKey(blank=True, to='learning.Semester', help_text='Set semester for album and all uploaded images will inherit it.', null=True, verbose_name='Semester'),
        ),
        migrations.AlterField(
            model_name='image',
            name='semester',
            field=models.ForeignKey(verbose_name='Semester', blank=True, to='learning.Semester'),
        ),
    ]
