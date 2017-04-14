from __future__ import unicode_literals

from django.conf import settings
from django.urls import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from sorl.thumbnail import ImageField
from taggit.managers import TaggableManager
from users.models import CSCUser


class Borrow(models.Model):
    book = models.ForeignKey("Book")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        # XXX: Can generate duplicates here if related user has both groups
        # It's unlikely due to admin form validation, but possible in theory
        limit_choices_to={'groups__in': [
            CSCUser.group.STUDENT_CENTER, CSCUser.group.VOLUNTEER]},
        related_name="borrows", verbose_name=_("Borrow|student"))
    borrowed_on = models.DateField(_("Borrow|borrowed on"))

    class Meta:
        verbose_name = _("borrow")
        verbose_name_plural = _("borrows")
        ordering = ["borrowed_on"]


@python_2_unicode_compatible
class Book(models.Model):
    author = models.CharField(_("Book|author"), max_length=255)
    title = models.CharField(_("Book|title"), max_length=255)
    description = models.TextField(
        verbose_name=_("Book|description"), default="")
    cover = ImageField(
        _("Book|cover"), upload_to="books", null=True, blank=True)
    copies = models.PositiveSmallIntegerField(
        _("Book|number of copies"), default=1)
    read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="Borrow", related_name="books",
        verbose_name=_("read by"))

    tags = TaggableManager()

    class Meta:
        ordering = ["title"]
        verbose_name = _("book")
        verbose_name_plural = _("books")

    def __str__(self):
        return "{0.author} \"{0.title}\"".format(self)

    def get_absolute_url(self):
        return reverse("library_book_detail", args=[self.pk])

    @property
    def available_copies(self):
        return max(self.copies - self.read_by.count(), 0)

    # TODO(lebedev): how to make sure that the number of borrows
    # does not exceed the number of copies?
