from sorl.thumbnail import ImageField
from taggit.managers import TaggableManager
from taggit.models import TagBase, TaggedItemBase

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import Branch
from core.urls import reverse
from core.utils import ru_en_mapping


class BookTag(TagBase):
    class Meta:
        verbose_name = _("Book Tag")
        verbose_name_plural = _("Book Tags")

    def slugify(self, tag, i=None):
        """Transliterates cyrillic symbols before slugify"""
        tag = tag.translate(ru_en_mapping)
        return super().slugify(tag, i)


class TaggedBook(TaggedItemBase):
    content_object = models.ForeignKey(
        'library.Book',
        verbose_name=_("Book"),
        on_delete=models.CASCADE)
    tag = models.ForeignKey(
        BookTag,
        verbose_name=_("Tag"),
        on_delete=models.CASCADE,
        related_name="tagged_books"
    )


class Book(models.Model):
    author = models.CharField(_("Book|author"), max_length=255)
    title = models.CharField(_("Book|title"), max_length=255)
    description = models.TextField(
        verbose_name=_("Book|description"), default="")
    cover = ImageField(
        _("Book|cover"),
        upload_to="books",
        max_length=200,
        blank=True)

    tags = TaggableManager(through=TaggedBook)

    class Meta:
        ordering = ["title"]
        verbose_name = _("book")
        verbose_name_plural = _("books")

    def __str__(self):
        return "{0.author} \"{0.title}\"".format(self)


class Stock(models.Model):
    book = models.ForeignKey(Book, verbose_name=_("Book"),
                             related_name="stocks",
                             on_delete=models.CASCADE)
    branch = models.ForeignKey(
        Branch,
        verbose_name=_("Branch"),
        related_name="+",  # Disable backwards relation
        on_delete=models.CASCADE)
    copies = models.PositiveSmallIntegerField(
        _("Book|number of copies"), default=1)

    class Meta:
        unique_together = [['book', 'branch']]
        ordering = ["book__title"]
        verbose_name = _("Stock")
        verbose_name_plural = _("Stocks")

    def __str__(self):
        return "{0.book} [{0.branch}]".format(self)

    def get_absolute_url(self):
        return reverse("library:book_detail",
                       subdomain=settings.LMS_SUBDOMAIN,
                       args=[self.id])

    @property
    def available_copies(self):
        return max(self.copies - self.borrows.count(), 0)

    # TODO(lebedev): how to make sure that the number of borrows
    # does not exceed the number of copies?


class Borrow(models.Model):
    stock = models.ForeignKey("Stock", related_name="borrows",
                              on_delete=models.PROTECT)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="borrows", verbose_name=_("Borrow|student"))
    borrowed_on = models.DateField(_("Borrow|borrowed on"))

    class Meta:
        verbose_name = _("Borrowed Book")
        verbose_name_plural = _("Borrowed Books")
        ordering = ["borrowed_on"]

    def __str__(self):
        return str(self.student)
