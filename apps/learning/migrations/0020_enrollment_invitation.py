# Generated by Django 2.2.3 on 2019-07-30 14:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0019_remove_enrollmentinvitation_expire_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='enrollment',
            name='invitation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='learning.Invitation', verbose_name='Invitation'),
        ),
    ]