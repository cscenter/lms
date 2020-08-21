# -*- coding: utf-8 -*-

import logging
import os

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel
from sorl.thumbnail import ImageField, get_thumbnail
from sorl.thumbnail.helpers import ThumbnailError

from courses.models import Course, Semester

logger = logging.getLogger(__name__)


def gen_path_to_image(self, filename):
    if self.album:
        slug = self.album.slug
    elif self.course:
        slug = "{}_{}".format(self.course.semester.year,
                              self.course.semester.type)
    else:
        slug = "misc"
    return os.path.join('gallery',
                        slug,
                        filename)


class Image(models.Model):
    title = models.CharField(verbose_name=_('Title'), max_length=255,
                             blank=True, null=True)
    album = models.ForeignKey('Album',
                              on_delete=models.CASCADE, verbose_name=_('Album'),
                              blank=True, null=True, related_name='images')
    order = models.IntegerField(verbose_name=_('Order'), default=0)
    image = ImageField(verbose_name=_('File'), max_length=255,
                       upload_to=gen_path_to_image)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('User'),
                             null=True, blank=True,
                             related_name='images',
                             on_delete=models.CASCADE)
    course = models.ForeignKey(
        Course,
        verbose_name=_("Course offering"),
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )

    class Meta:
        ordering = ('order', 'id')
        verbose_name = _('Image')
        verbose_name_plural = _('Images')

    def __str__(self):
        return '%s' % self.id


class Album(MPTTModel):
    name = models.CharField(verbose_name=_('Name'), max_length=100,
                            blank=False, null=False)
    slug = models.SlugField(
        _("Slug"),
        max_length=70,
        help_text=_("Short name in ASCII, used in images upload path"),
        unique=True)
    order = models.IntegerField(verbose_name=_('Order'), default=100)
    brief = models.CharField(verbose_name=_('Brief'), max_length=255,
                             blank=True, default='',
                             help_text=_('Short description'))

    head = models.ForeignKey(Image,
                             on_delete=models.SET_NULL, verbose_name=_('Head'),
                             related_name='head_of', blank=True, null=True)
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        verbose_name=_("Semester"),
        blank=True,
        null=True,
        help_text=_("Set semester for album and all uploaded images "
                    "will inherit it."))

    parent = TreeForeignKey('self', verbose_name=_('Parent'),
                            null=True, blank=True,
                            related_name='children', db_index=True,
                            help_text=_("Parent album"),
                            on_delete=models.CASCADE)

    class MPTTMeta:
        order_insertion_by = ['order']

    class Meta:
        ordering = ('order', 'name')
        verbose_name = _('Album')
        verbose_name_plural = _('Albums')

    def __str__(self):
        return self.name

    def admin_thumbnail(self):
        img = self.get_head()
        if not img:
            return _('Empty album')

        try:
            thumb = get_thumbnail(img.image, '100x100', crop='center')
            return '<img src="{}" alt="">'.format(thumb.url)
        except (IOError, ThumbnailError):
            logger.info('Can\'t crate thumbnail from image {}'.format(img),
                        exc_info=settings.DEBUG)
            return ''
    admin_thumbnail.short_description = _('Head')
    admin_thumbnail.allow_tags = True

    def get_head(self):
        if not self.head:
            self.head = self.images.first()
            if self.head:
                self.save()
        return self.head

