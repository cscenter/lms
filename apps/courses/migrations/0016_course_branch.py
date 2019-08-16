# Generated by Django 2.2.4 on 2019-08-16 13:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_auto_20190816_1330'),
        ('courses', '0015_auto_20190814_1522'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='branch',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, related_name='courses', to='core.Branch', verbose_name='Branch'),
            preserve_default=False,
        ),
    ]
