# Generated by Django 2.2.10 on 2020-03-11 11:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0011_auto_20200311_1138'),
    ]

    operations = [
        migrations.RenameField(
            model_name='course',
            old_name='materials_slides',
            new_name='public_slides_count',
        ),
    ]
