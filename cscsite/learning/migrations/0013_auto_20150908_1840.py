# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0012_auto_20150813_1700'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseclass',
            name='slides_url',
            field=models.URLField(verbose_name='SlideShare URL', blank=True),
        ),
        migrations.AddField(
            model_name='courseclass',
            name='video_url',
            field=models.URLField(help_text='Both YouTube and Yandex Video are supported', verbose_name='Video URL', blank=True),
        ),
    ]
