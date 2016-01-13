# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
from django.conf import settings
import users.models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0035_auto_20151230_1213'),
        ('users', '0012_cscuser_status_changed_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='CSCUserStatusLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateField(default=django.utils.timezone.now, verbose_name='created')),
                ('status', models.CharField(max_length=15, verbose_name='Status', choices=[('expelled', 'StudentInfo|Expelled'), ('reinstated', 'StudentInfo|Reinstalled'), ('will_graduate', 'StudentInfo|Will graduate')])),
                ('semester', models.ForeignKey(verbose_name='Semester', to='learning.Semester')),
            ],
        ),
        migrations.AlterField(
            model_name='cscuser',
            name='status_changed_at',
            field=users.models.LoggingMonitorField(monitor='status', log_class=users.models.CSCUserStatusLog, blank=True, help_text="Don't touch this field to automatically update it when status field changed", null=True, verbose_name='Status changed'),
        ),
        migrations.AddField(
            model_name='cscuserstatuslog',
            name='student',
            field=models.ForeignKey(verbose_name='Student', to=settings.AUTH_USER_MODEL),
        ),
    ]
