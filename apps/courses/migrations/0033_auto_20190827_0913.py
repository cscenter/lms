# Generated by Django 2.2.4 on 2019-08-27 09:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0032_auto_20190827_0906'),
    ]

    operations = [
        migrations.AlterField(
            model_name='semester',
            name='ends_at',
            field=models.DateTimeField(editable=False, help_text='Value in UTC format and is predefined.', verbose_name='Semester|EndsAt'),
        ),
        migrations.AlterField(
            model_name='semester',
            name='starts_at',
            field=models.DateTimeField(editable=False, help_text='Value in UTC format and is predefined.', verbose_name='Semester|StartsAt'),
        ),
    ]
