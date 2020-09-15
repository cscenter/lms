# Generated by Django 3.0.9 on 2020-09-15 11:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_auto_20200911_0848'),
        ('courses', '0028_auto_20200902_0915'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='ask_ttc',
            field=models.BooleanField(default=False, help_text='Teacher must specify estimated amount of time required for an assignment to be completed. Student enters the actual time on submitting the solution.', verbose_name='Ask Time to Completion'),
        ),
        migrations.AlterField(
            model_name='learningspace',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='learning_spaces', to='core.Location', verbose_name='Address'),
        ),
        migrations.AlterField(
            model_name='learningspace',
            name='name',
            field=models.CharField(blank=True, help_text='The location name will be added to the end if provided', max_length=140, verbose_name='Name'),
        ),
    ]
