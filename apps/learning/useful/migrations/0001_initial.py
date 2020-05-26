# Generated by Django 2.2.10 on 2020-05-26 13:17

from django.db import migrations, models
import django.db.models.deletion
import taggit.managers


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaggedUsefulItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.IntegerField(db_index=True, verbose_name='Object id')),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='useful_taggedusefulitem_tagged_items', to='contenttypes.ContentType', verbose_name='Content type')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='UsefulTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Name')),
                ('slug', models.SlugField(max_length=100, unique=True, verbose_name='Slug')),
            ],
            options={
                'verbose_name': 'Useful Tag',
                'verbose_name_plural': 'Useful Tags',
                'db_table': 'useful_tags',
            },
        ),
        migrations.CreateModel(
            name='Useful',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='Title')),
                ('content', models.TextField(verbose_name='Content')),
                ('sort', models.SmallIntegerField(blank=True, null=True, verbose_name='Sort order')),
                ('site', models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='useful_set', to='sites.Site', verbose_name='Site')),
                ('tags', taggit.managers.TaggableManager(help_text='A comma-separated list of tags.', through='useful.TaggedUsefulItem', to='useful.UsefulTag', verbose_name='Tags')),
            ],
            options={
                'verbose_name': 'Useful',
                'verbose_name_plural': 'Useful',
                'ordering': ['sort'],
            },
        ),
        migrations.AddField(
            model_name='taggedusefulitem',
            name='tag',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='useful.UsefulTag'),
        ),
    ]
