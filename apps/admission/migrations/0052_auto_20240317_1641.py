# Generated by Django 3.2.18 on 2024-03-17 16:41

import datetime
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admission', '0051_alter_applicant_photo'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicant',
            name='internship_beginning',
            field=models.DateField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(datetime.date(2050, 1, 1)), django.core.validators.MinValueValidator(datetime.date(1900, 1, 1))], verbose_name='Date of the internship beginning'),
        ),
        migrations.AddField(
            model_name='applicant',
            name='internship_end',
            field=models.DateField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(datetime.date(2050, 1, 1)), django.core.validators.MinValueValidator(datetime.date(1900, 1, 1))], verbose_name='Date of the internship end'),
        ),
        migrations.AddField(
            model_name='applicant',
            name='internship_not_ended',
            field=models.BooleanField(default=False, help_text='Applicant|internship_not_ended', verbose_name='Does your internship still going?'),
        ),
        migrations.AlterField(
            model_name='applicant',
            name='birth_date',
            field=models.DateField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(datetime.date(2024, 1, 1)), django.core.validators.MinValueValidator(datetime.date(1900, 1, 1))], verbose_name='Date of Birth'),
        ),
    ]
