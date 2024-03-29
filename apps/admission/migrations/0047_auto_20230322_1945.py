# Generated by Django 3.2.13 on 2023-03-22 19:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0039_yandexuserdata'),
        ('admission', '0046_campaign_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicant',
            name='has_internship',
            field=models.BooleanField(help_text='Applicant|Has internship', null=True, verbose_name='Have you had an internship?'),
        ),
        migrations.AddField(
            model_name='applicant',
            name='internship_position',
            field=models.CharField(blank=True, help_text='Applicant|Internship position', max_length=255, null=True, verbose_name='Internship position'),
        ),
        migrations.AddField(
            model_name='applicant',
            name='internship_workplace',
            field=models.CharField(blank=True, help_text='Applicant|Internship workplace', max_length=255, null=True, verbose_name='Internship workplace'),
        ),
        migrations.AddField(
            model_name='applicant',
            name='partner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.partnertag', verbose_name='Partner'),
        ),
    ]
