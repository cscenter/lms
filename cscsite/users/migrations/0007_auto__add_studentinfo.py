# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'StudentInfo'
        db.create_table(u'users_studentinfo', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('student', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['users.CSCUser'], unique=True)),
            ('university', self.gf('django.db.models.fields.CharField')(max_length=140, blank=True)),
            ('phone', self.gf('django.db.models.fields.CharField')(max_length=40, blank=True)),
            ('uni_year_at_enrollment', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True, blank=True)),
            ('comment', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('comment_changed', self.gf('model_utils.fields.MonitorField')(default=datetime.datetime.now, monitor=u'comment')),
            ('comment_last_author', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'studentinfo_commented', on_delete=models.PROTECT, to=orm['users.CSCUser'])),
            ('nondegree', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=15, blank=True)),
            ('study_program', self.gf('django.db.models.fields.CharField')(max_length=2, blank=True)),
            ('online_courses', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('shad_courses', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('workplace', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
        ))
        db.send_create_signal(u'users', ['StudentInfo'])


    def backwards(self, orm):
        # Deleting model 'StudentInfo'
        db.delete_table(u'users_studentinfo')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'users.cscuser': {
            'Meta': {'ordering': "[u'last_name', u'first_name']", 'object_name': 'CSCUser'},
            'csc_review': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'enrollment_year': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'graduation_year': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'patronymic': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'photo': (u'sorl.thumbnail.fields.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'private_contacts': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'stepic_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'yandex_id': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'})
        },
        u'users.studentinfo': {
            'Meta': {'ordering': "[u'student']", 'object_name': 'StudentInfo'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'comment_changed': ('model_utils.fields.MonitorField', [], {'default': 'datetime.datetime.now', u'monitor': "u'comment'"}),
            'comment_last_author': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'studentinfo_commented'", 'on_delete': 'models.PROTECT', 'to': u"orm['users.CSCUser']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'nondegree': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'online_courses': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'shad_courses': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'student': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['users.CSCUser']", 'unique': 'True'}),
            'study_program': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'uni_year_at_enrollment': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'university': ('django.db.models.fields.CharField', [], {'max_length': '140', 'blank': 'True'}),
            'workplace': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        }
    }

    complete_apps = ['users']