# Generated by Django 2.2.4 on 2019-08-30 08:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Name')),
                ('sort', models.SmallIntegerField(blank=True, null=True, verbose_name='Sort order')),
                ('site', models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to='sites.Site', verbose_name='Site')),
            ],
            options={
                'verbose_name': 'Category',
                'verbose_name_plural': 'Categories',
                'ordering': ['sort'],
            },
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(max_length=255, verbose_name='Question')),
                ('answer', models.TextField(verbose_name='Answer')),
                ('sort', models.SmallIntegerField(blank=True, null=True, verbose_name='Sort order')),
                ('categories', models.ManyToManyField(blank=True, related_name='categories', to='faq.Category', verbose_name='Categories')),
                ('site', models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to='sites.Site', verbose_name='Site')),
            ],
            options={
                'verbose_name': 'Question',
                'verbose_name_plural': 'Questions',
                'ordering': ['sort'],
            },
        ),
    ]
