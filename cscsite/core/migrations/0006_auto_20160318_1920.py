# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_auto_20160318_1919'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='faqcategory',
            options={'ordering': ['sort'], 'verbose_name': 'FAQ category', 'verbose_name_plural': 'FAQ categories'},
        ),
    ]
