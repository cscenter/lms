# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
        ('core', '0004_auto_20160318_1708'),
    ]

    operations = [
        migrations.CreateModel(
            name='FaqCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='Category name')),
                ('sort', models.SmallIntegerField(null=True, verbose_name='Sort order', blank=True)),
                ('site', models.ForeignKey(default=1, verbose_name='Site', to='sites.Site')),
            ],
        ),
        migrations.AddField(
            model_name='faq',
            name='categories',
            field=models.ManyToManyField(related_name='categories', verbose_name='Categories', to='core.FaqCategory'),
        ),
    ]
