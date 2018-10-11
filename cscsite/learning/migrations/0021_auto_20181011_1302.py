# Generated by Django 2.1.1 on 2018-10-11 13:02

import core.db.models
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0020_auto_20180903_1354'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseoffering',
            name='online_course_url',
            field=models.URLField(blank=True, verbose_name='Online Course URL'),
        ),
        migrations.AlterField(
            model_name='studentassignment',
            name='grade',
            field=core.db.models.GradeField(blank=True, decimal_places=2,
                                            max_digits=6, null=True,
                                            verbose_name='Grade'),
        ),
    ]
