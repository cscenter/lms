# Generated by Django 2.2.10 on 2020-05-25 15:10

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_auto_20200525_1419'),
    ]

    operations = [
        migrations.AlterField(
            model_name='enrollmentcertificate',
            name='student',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='enrollment_certificates', to=settings.AUTH_USER_MODEL, verbose_name='Student'),
        ),
    ]
