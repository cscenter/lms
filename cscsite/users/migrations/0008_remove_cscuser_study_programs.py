# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_cscuser_is_center_student'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cscuser',
            name='study_programs',
        ),
    ]
