# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('treemenus', '0001_initial'),
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.CreateModel(
            name='MenuItemExtension',
            fields=[
                ('menu_item', models.OneToOneField(related_name='extension', primary_key=True, serialize=False, to='treemenus.MenuItem', on_delete=models.deletion.CASCADE,)),
                ('protected', models.BooleanField(default=False, help_text='Check if visible only for authenticated user')),
                ('unauthenticated', models.BooleanField(default=False, help_text='Check if visible only for unauthenticated user')),
                ('staff_only', models.BooleanField(default=False, help_text='Check if visible only for staff')),
                ('budge', models.CharField(default=b'', help_text='Variable name for unred_notifications_cache', max_length=255, blank=True)),
                ('classes', models.CharField(default=b'', help_text='Additional classes', max_length=255, blank=True)),
                ('select_patterns', models.TextField(default=b' ', help_text='Specify patterns when item is selected. One pattern for each line.', blank=True)),
                ('exclude_patterns', models.TextField(default=b' ', help_text='Specify patterns when item is not selected. One pattern for each line.', blank=True)),
                ('groups', models.ManyToManyField(related_query_name=b'menuitem', related_name='menuitems_set', to='auth.Group', blank=True, help_text='Restrict visibility to selected groups.', verbose_name='groups')),
            ],
            options={
                'verbose_name': 'Menu extensions',
                'verbose_name_plural': 'Menu extensions',
            },
        ),
    ]
