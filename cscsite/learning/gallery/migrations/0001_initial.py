# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import sorl.thumbnail.fields
import mptt.fields
import django.db.models.deletion
from django.conf import settings
import learning.gallery.models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0014_courseoffering_grading_type'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Album',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='Name')),
                ('order', models.IntegerField(default=100, verbose_name='Order')),
                ('brief', models.CharField(default='', help_text='Short description', max_length=255, verbose_name='Brief', blank=True)),
                ('lft', models.PositiveIntegerField(editable=False, db_index=True)),
                ('rght', models.PositiveIntegerField(editable=False, db_index=True)),
                ('tree_id', models.PositiveIntegerField(editable=False, db_index=True)),
                ('level', models.PositiveIntegerField(editable=False, db_index=True)),
            ],
            options={
                'ordering': ('order', 'name'),
            },
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255, null=True, verbose_name='Title', blank=True)),
                ('order', models.IntegerField(default=0, verbose_name='Order')),
                ('image', sorl.thumbnail.fields.ImageField(upload_to=learning.gallery.models.gen_path_to_image, max_length=255, verbose_name='File')),
                ('album', models.ForeignKey(related_name='images', verbose_name='Album', blank=True, to='gallery.Album', null=True)),
                ('semester', models.ForeignKey(verbose_name='Semester', to='learning.Semester')),
                ('user', models.ForeignKey(related_name='images', verbose_name='User', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ('order', 'id'),
                'verbose_name': 'Image',
                'verbose_name_plural': 'Images',
            },
        ),
        migrations.AddField(
            model_name='album',
            name='head',
            field=models.ForeignKey(related_name='head_of', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Head', blank=True, to='gallery.Image', null=True),
        ),
        migrations.AddField(
            model_name='album',
            name='parent',
            field=mptt.fields.TreeForeignKey(related_name='children', blank=True, to='gallery.Album', null=True),
        ),
        migrations.AddField(
            model_name='album',
            name='semester',
            field=models.ForeignKey(verbose_name='Semester', to='learning.Semester'),
        ),
    ]
