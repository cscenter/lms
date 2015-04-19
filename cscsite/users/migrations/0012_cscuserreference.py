# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_auto_20150402_1559'),
    ]

    operations = [
        migrations.CreateModel(
            name='CSCUserReference',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('signature', models.CharField(max_length=255, verbose_name='Reference|signature')),
                ('note', models.TextField(verbose_name='Reference|note', blank=True)),
                ('student', models.ForeignKey(verbose_name='Student', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['signature'],
                'verbose_name': 'User reference record',
                'verbose_name_plural': 'User reference records',
            },
            bases=(models.Model,),
        ),
    ]
