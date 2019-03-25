# Generated by Django 2.1.5 on 2019-03-25 11:58

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0005_auto_20190322_1229'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='application_starts_at',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Application Starts At'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='campaign',
            name='exam_max_score',
            field=models.SmallIntegerField(blank=True, null=True, verbose_name='Campaign|Exam_max_score'),
        ),
        migrations.AlterField(
            model_name='campaign',
            name='exam_passing_score',
            field=models.SmallIntegerField(blank=True, help_text='Campaign|Exam_passing_score-help', null=True, verbose_name='Campaign|Exam_passing_score'),
        ),
    ]
