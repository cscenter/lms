# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'AssignmentNotification'
        db.create_table(u'learning_assignmentnotification', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['users.CSCUser'])),
            ('assignment_student', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['learning.AssignmentStudent'])),
            ('is_passed', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_unread', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('is_notified', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'learning', ['AssignmentNotification'])


    def backwards(self, orm):
        # Deleting model 'AssignmentNotification'
        db.delete_table(u'learning_assignmentnotification')


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
        u'learning.assignment': {
            'Meta': {'ordering': "[u'created', u'course_offering']", 'object_name': 'Assignment'},
            'assigned_to': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['users.CSCUser']", 'symmetrical': 'False', 'through': u"orm['learning.AssignmentStudent']", 'blank': 'True'}),
            'attached_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'course_offering': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['learning.CourseOffering']", 'on_delete': 'models.PROTECT'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'deadline_at': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_online': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '140'})
        },
        u'learning.assignmentcomment': {
            'Meta': {'ordering': "[u'created']", 'object_name': 'AssignmentComment'},
            'assignment_student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['learning.AssignmentStudent']"}),
            'attached_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.CSCUser']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        u'learning.assignmentnotification': {
            'Meta': {'ordering': "[u'-created']", 'object_name': 'AssignmentNotification'},
            'assignment_student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['learning.AssignmentStudent']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_notified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_passed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_unread': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.CSCUser']"})
        },
        u'learning.assignmentstudent': {
            'Meta': {'ordering': "[u'assignment', u'student']", 'object_name': 'AssignmentStudent'},
            'assignment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['learning.Assignment']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'state': ('model_utils.fields.StatusField', [], {'default': "u'not_checked'", 'max_length': '100', u'no_check_for_status': 'True'}),
            'state_changed': ('model_utils.fields.MonitorField', [], {'default': 'datetime.datetime.now', u'monitor': "u'state'"}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.CSCUser']"})
        },
        u'learning.course': {
            'Meta': {'ordering': "[u'name']", 'object_name': 'Course'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '70'})
        },
        u'learning.courseclass': {
            'Meta': {'ordering': "[u'-date', u'course_offering', u'starts_at']", 'object_name': 'CourseClass'},
            'course_offering': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['learning.CourseOffering']", 'on_delete': 'models.PROTECT'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'ends_at': ('django.db.models.fields.TimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'other_materials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slides': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'starts_at': ('django.db.models.fields.TimeField', [], {}),
            'type': ('model_utils.fields.StatusField', [], {'default': "u'lecture'", 'max_length': '100', u'no_check_for_status': 'True'}),
            'venue': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['learning.Venue']", 'on_delete': 'models.PROTECT'})
        },
        u'learning.courseclassattachment': {
            'Meta': {'ordering': "[u'course_class', u'-created']", 'object_name': 'CourseClassAttachment'},
            'course_class': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['learning.CourseClass']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'material': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'})
        },
        u'learning.courseoffering': {
            'Meta': {'ordering': "[u'-semester', u'course__created']", 'object_name': 'CourseOffering'},
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['learning.Course']", 'on_delete': 'models.PROTECT'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'enrolled_students': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'enrolled_on_set'", 'blank': 'True', 'through': u"orm['learning.Enrollment']", 'to': u"orm['users.CSCUser']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'semester': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['learning.Semester']", 'on_delete': 'models.PROTECT'}),
            'teachers': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "u'teaching_set'", 'symmetrical': 'False', 'to': u"orm['users.CSCUser']"})
        },
        u'learning.courseofferingnews': {
            'Meta': {'ordering': "[u'-created']", 'object_name': 'CourseOfferingNews'},
            'course_offering': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['learning.CourseOffering']", 'on_delete': 'models.PROTECT'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '140'})
        },
        u'learning.enrollment': {
            'Meta': {'ordering': "[u'student', u'course_offering']", 'object_name': 'Enrollment'},
            'course_offering': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['learning.CourseOffering']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'grade': ('model_utils.fields.StatusField', [], {'default': "u'not_graded'", 'max_length': '100', u'no_check_for_status': 'True'}),
            'grade_changed': ('model_utils.fields.MonitorField', [], {'default': 'datetime.datetime.now', u'monitor': "u'grade'"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.CSCUser']"})
        },
        u'learning.semester': {
            'Meta': {'ordering': "[u'year', u'-type']", 'object_name': 'Semester'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('model_utils.fields.StatusField', [], {'default': "u'spring'", 'max_length': '100', u'no_check_for_status': 'True'}),
            'year': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        u'learning.venue': {
            'Meta': {'ordering': "[u'name']", 'object_name': 'Venue'},
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '140'})
        },
        u'users.cscuser': {
            'Meta': {'object_name': 'CSCUser'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'enrolment_year': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
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
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        }
    }

    complete_apps = ['learning']