# Generated by Django 3.2.9 on 2021-12-15 11:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0035_auto_20211214_1848'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='studentprofile',
            name='birthday',
        ),
    ]
