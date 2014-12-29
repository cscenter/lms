# -*- coding: utf-8 -*-

from __future__ import print_function

import posixpath
import sys
from urlparse import urlparse

from django.db.models import Q
from lxml import html
from south.v2 import DataMigration


def extract_youtube_url(pk, html_source):
    html_tree = html.fromstring(html_source)
    iframes = html_tree.xpath(r"./iframe[contains(@src, 'youtube.com/embed')]")
    if not iframes:
        print("{:03d} no embed found".format(pk), file=sys.stderr)
        print(html_source, file=sys.stderr)
        return
    elif len(iframes) > 1:
        print("{:03d}: multiple embeds found".format(pk), file=sys.stderr)
        print(html_source, file=sys.stderr)
        return

    [iframe] = iframes
    return iframe.attrib["src"]


class Migration(DataMigration):

    def forwards(self, orm):
        q = (Q(video__contains="youtube") |
             Q(other_materials__contains="youtube"))
        for course_class in orm.CourseClass.objects.filter(q):
            iframe_url = extract_youtube_url(
                course_class.pk,
                course_class.video + course_class.other_materials)
            if iframe_url is None:
                continue

            result = urlparse(iframe_url)
            _prefix, yt_id = posixpath.split(result.path)
            course_class.video_url = "http://www.youtube.com/watch?v=" + yt_id
            course_class.save()

    def backwards(self, orm):
        raise RuntimeError("Cannot reverse this migration.")

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
            'grade_max': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '5'}),
            'grade_min': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '2'}),
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
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'learning.assignmentnotification': {
            'Meta': {'ordering': "[u'-created']", 'object_name': 'AssignmentNotification'},
            'assignment_student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['learning.AssignmentStudent']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_about_creation': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_about_deadline': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_about_passed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_notified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_unread': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.CSCUser']"})
        },
        u'learning.assignmentstudent': {
            'Meta': {'ordering': "[u'assignment', u'student']", 'object_name': 'AssignmentStudent'},
            'assignment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['learning.Assignment']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'grade': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'grade_changed': ('model_utils.fields.MonitorField', [], {'default': 'datetime.datetime.now', u'monitor': "u'grade'"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
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
            'Meta': {'ordering': "[u'-date', u'course_offering', u'-starts_at']", 'object_name': 'CourseClass'},
            'course_offering': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['learning.CourseOffering']", 'on_delete': 'models.PROTECT'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'ends_at': ('django.db.models.fields.TimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'other_materials': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'slides': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'slides_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'starts_at': ('django.db.models.fields.TimeField', [], {}),
            'type': ('model_utils.fields.StatusField', [], {'default': "u'lecture'", 'max_length': '100', u'no_check_for_status': 'True'}),
            'venue': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['learning.Venue']", 'on_delete': 'models.PROTECT'}),
            'video': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'video_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
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
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.CSCUser']", 'on_delete': 'models.PROTECT'}),
            'course_offering': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['learning.CourseOffering']", 'on_delete': 'models.PROTECT'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '140'})
        },
        u'learning.courseofferingnewsnotification': {
            'Meta': {'ordering': "[u'-created']", 'object_name': 'CourseOfferingNewsNotification'},
            'course_offering_news': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['learning.CourseOfferingNews']"}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_notified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_unread': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['users.CSCUser']"})
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
        u'learning.overallgrade': {
            'Meta': {'ordering': "[u'student']", 'object_name': 'OverallGrade'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'grade': ('model_utils.fields.StatusField', [], {'default': "u'not_graded'", 'max_length': '100', u'no_check_for_status': 'True'}),
            'grade_changed': ('model_utils.fields.MonitorField', [], {'default': 'datetime.datetime.now', u'monitor': "u'grade'"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'student': ('annoying.fields.AutoOneToOneField', [], {'related_name': "u'overall_grade'", 'unique': 'True', 'to': u"orm['users.CSCUser']"})
        },
        u'learning.semester': {
            'Meta': {'ordering': "[u'-year', u'type']", 'object_name': 'Semester'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('model_utils.fields.StatusField', [], {'default': "u'spring'", 'max_length': '100', u'no_check_for_status': 'True'}),
            'year': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        u'learning.venue': {
            'Meta': {'ordering': "[u'-is_preferred', u'name']", 'object_name': 'Venue'},
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_preferred': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '140'})
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
            'stepic_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'yandex_id': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'})
        }
    }

    complete_apps = ['learning']
    symmetrical = True
