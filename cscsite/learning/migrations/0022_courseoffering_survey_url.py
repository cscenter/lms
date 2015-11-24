# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0021_last_commented_change_verbose_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseoffering',
            name='survey_url',
            field=models.URLField(help_text='Link to Survey', verbose_name='Survey URL', blank=True),
        ),
    ]
