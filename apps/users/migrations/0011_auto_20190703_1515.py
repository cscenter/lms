# Generated by Django 2.2.3 on 2019-07-03 15:15

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_auto_20190703_1343'),
    ]

    operations = [
        migrations.RenameField(
            model_name='usergroup',
            old_name='group',
            new_name='role',
        ),
        migrations.AlterField(
            model_name='usergroup',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='groups', related_query_name='group', to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
    ]
