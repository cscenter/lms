# Generated by Django 3.2.18 on 2024-12-13 13:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0052_auto_20240903_1001'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='is_draft',
            field=models.BooleanField(default=True, verbose_name='Is draft'),
        ),
    ]