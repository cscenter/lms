from django.db import models
from django.utils.translation import gettext_lazy as _


class Country(models.Model):
    name = models.CharField(_("Name"), max_length=255)

    class Meta:
        verbose_name = _("Country")
        verbose_name_plural = _("Countries")

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"[Country] id: {self.pk} name: {self.name}"


class City(models.Model):
    external_id = models.PositiveIntegerField(_("External ID"))
    name = models.TextField(_("Name"))
    display_name = models.TextField(_("Display Name"))
    country = models.ForeignKey(Country,
                                verbose_name=_("Country"),
                                related_name="cities",
                                on_delete=models.PROTECT)
    order = models.PositiveIntegerField(_("Order"), default=512)

    class Meta:
        verbose_name = _("City")
        verbose_name_plural = _("Cities")
        constraints = [
            models.UniqueConstraint(fields=['external_id'],
                                    name='unique_city_external_id')
        ]

    def __str__(self):
        return self.name


class University(models.Model):
    external_id = models.PositiveIntegerField(_("External ID"))
    name = models.TextField(_("Name"))
    display_name = models.TextField(_("Display Name"))
    city = models.ForeignKey(City,
                             verbose_name=_("City"),
                             related_name="universities",
                             on_delete=models.PROTECT)

    class Meta:
        verbose_name = _("University")
        verbose_name_plural = _("Universities")
        constraints = [
            models.UniqueConstraint(fields=['external_id'],
                                    name='unique_university_external_id')
        ]

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"[University] id: {self.pk} display_name: {self.display_name}"


class Faculty(models.Model):
    external_id = models.PositiveIntegerField(_("External ID"))
    name = models.TextField(_("Name"))
    display_name = models.TextField(_("Display Name"))
    university = models.ForeignKey(University,
                                   verbose_name=_("University"),
                                   related_name="faculties",
                                   on_delete=models.PROTECT)

    class Meta:
        verbose_name = _("Faculty")
        verbose_name_plural = _("Faculties")
        constraints = [
            models.UniqueConstraint(fields=['external_id'],
                                    name='unique_faculty_external_id')
        ]

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"[Faculty] id: {self.pk} display_name: {self.display_name}"
