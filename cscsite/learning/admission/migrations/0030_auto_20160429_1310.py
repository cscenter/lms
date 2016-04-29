# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0029_campaign_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='interview',
            name='decision',
            field=models.CharField(default='approval', max_length=15, verbose_name='Interview|Decision', choices=[('approval', 'Approval'), ('waiting', 'Waiting for interview'), ('canceled', 'Canceled'), ('accept', 'Accept'), ('decline', 'Decline'), ('volunteer', 'Volunteer')]),
        ),
    ]
