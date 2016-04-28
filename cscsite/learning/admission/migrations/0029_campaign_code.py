# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0028_auto_20160428_1918'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='code',
            field=models.CharField(default=2016, help_text='Will be displayed in admin select', max_length=140, verbose_name='Campaign|Code'),
            preserve_default=False,
        ),
    ]
