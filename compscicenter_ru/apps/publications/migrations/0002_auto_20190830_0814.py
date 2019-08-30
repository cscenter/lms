# Generated by Django 2.2.4 on 2019-08-30 08:14

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('publications', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('projects', '0002_auto_20190830_0814'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectpublicationauthor',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='projectpublication',
            name='authors',
            field=models.ManyToManyField(related_name='_projectpublication_authors_+', through='publications.ProjectPublicationAuthor', to=settings.AUTH_USER_MODEL, verbose_name='Authors'),
        ),
        migrations.AddField(
            model_name='projectpublication',
            name='projects',
            field=models.ManyToManyField(related_name='publications', to='projects.Project', verbose_name='Projects'),
        ),
        migrations.AlterUniqueTogether(
            name='projectpublicationauthor',
            unique_together={('user', 'project_publication')},
        ),
    ]
