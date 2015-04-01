# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0009_data_add_cities'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentProjectTimeframe',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('year', models.PositiveSmallIntegerField(verbose_name='CSCUser|Year', validators=[django.core.validators.MinValueValidator(1990)])),
                ('type', models.IntegerField(verbose_name='Semester|type', choices=[(0, 'spring'), (1, 'summer'), (2, 'autumn')])),
            ],
            options={
                'ordering': ['-year', '-type'],
                'verbose_name': 'Student project timeframe',
                'verbose_name_plural': 'Student project timeframes',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='studentproject',
            name='timeframes',
            field=models.ManyToManyField(to='learning.StudentProjectTimeframe', verbose_name='Semesters'),
            preserve_default=True,
        ),
    ]
