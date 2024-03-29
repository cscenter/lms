# Generated by Django 2.2.10 on 2020-05-21 11:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_auto_20200520_1651'),
        ('learning', '0012_auto_20200316_1238'),
    ]

    operations = [
        migrations.AddField(
            model_name='enrollment',
            name='student_profile',
            field=models.ForeignKey(default=1, editable=False, on_delete=django.db.models.deletion.CASCADE, to='users.StudentProfile', verbose_name='Student Profile'),
            preserve_default=False,
        ),
    ]
