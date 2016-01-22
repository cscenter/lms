# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

CENTER_SITE_ID = 1
CLUB_SITE_ID = 2

def update_forward(apps, schema_editor):
    """Add sites list"""
    Site = apps.get_model('sites', 'Site')
    Site.objects.update_or_create(
        id=CENTER_SITE_ID,
        defaults={
            "domain": "compscicenter.ru",
            "name": "compscicenter.ru"
        }
    )
    Site.objects.update_or_create(
        id=CLUB_SITE_ID,
        defaults={
            "domain": "compsciclub.ru",
            "name": "compsciclub.ru"
        }
    )


def update_backward(apps, schema_editor):
    """Revert sites list to default"""
    Site = apps.get_model("sites", "Site")
    Site.objects.get(CLUB_SITE_ID).delete()
    Site.objects.update_or_create(
        id=CENTER_SITE_ID,
        defaults={
            "domain": "example.com",
            "name": "example.com"
        }
    )


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='City',
            fields=[
                ('code', models.CharField(help_text="UN/LOCODE notification preferable <a href='http://www.unece.org/cefact/locode/service/location' target='_blank'>Hint</a>", max_length=6, serialize=False, verbose_name='Code', primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='City name')),
                ('name_ru', models.CharField(max_length=255, null=True, verbose_name='City name')),
                ('name_en', models.CharField(max_length=255, null=True, verbose_name='City name')),
            ],
            options={
                'ordering': ['name'],
                'db_table': 'cities',
                'verbose_name': 'City',
                'verbose_name_plural': 'Cities',
            },
        ),
        migrations.RunPython(update_forward, update_backward),
    ]
