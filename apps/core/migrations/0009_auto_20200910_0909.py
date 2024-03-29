# Generated by Django 3.0.9 on 2020-09-10 09:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_siteconfiguration'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteconfiguration',
            name='email_backend',
            field=models.CharField(default='django.core.mail.backends.smtp.EmailBackend', help_text='Python import path of the backend to use for sending emails', max_length=255, verbose_name='Email Backend'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='siteconfiguration',
            name='lms_subdomain',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='LMS Subdomain'),
        ),
    ]
