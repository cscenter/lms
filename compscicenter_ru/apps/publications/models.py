from django.conf import settings
from django.db import models
from django.utils.encoding import smart_text
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from core.urls import reverse
from learning.projects.models import Project, Supervisor
from users.models import User


class ProjectPublicationAuthor(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    project_publication = models.ForeignKey('ProjectPublication',
                                            on_delete=models.CASCADE)
    description = models.CharField(
        verbose_name=_("Short Description"), blank=True, null=True,
        max_length=256)

    class Meta:
        verbose_name = _("Project Publication Author")
        verbose_name_plural = _("Project Publication Authors")
        unique_together = [('user', 'project_publication')]

    def __str__(self):
        return "{0} [{1}]".format(smart_text(self.project_publication),
                                  smart_text(self.user))

    @property
    def short_description(self):
        if self.description:
            return self.description
        elif self.user.graduation_year:
            s = f"Выпуск {self.user.graduation_year}"
            areas = ", ".join(str(d) for d in self.user.areas_of_study.all())
            return f"{s}, {areas}" if areas else s
        return ""


class ProjectPublication(models.Model):
    created = models.DateTimeField(
        verbose_name=_("created"),
        editable=False,
        default=now)
    title = models.CharField(
        verbose_name=_("Title"),
        max_length=255)
    slug = models.SlugField(_("Slug"))
    authors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Authors"),
        related_name='+',
        through=ProjectPublicationAuthor)
    projects = models.ManyToManyField(
        Project,
        verbose_name=_("Projects"),
        related_name='publications')
    description = models.TextField(
        verbose_name=_("Description"),
        blank=True)
    external_links = models.TextField(
        verbose_name=_("External Links"),
        blank=True)

    class Meta:
        db_table = 'publications_projects'
        verbose_name = _('Project Publication')
        verbose_name_plural = _('Project Publications')

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("project_publication", kwargs={"slug": self.slug})

    def get_publication_authors(self):
        return (ProjectPublicationAuthor.objects
                .filter(project_publication=self)
                .select_related("user"))

    def get_supervisors(self):
        projects = [p.pk for p in self.projects.all()]
        return Supervisor.objects.filter(projects__in=projects).distinct()

    def get_participants(self):
        projects = [p.pk for p in self.projects.all()]
        return (User.objects
                .filter(projectstudent__project__in=projects)
                .distinct()
                .order_by("projectstudent__project_id"))
