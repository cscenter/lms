import os

from django.conf import settings
from django.db import models
from django.utils.encoding import smart_text
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
from sorl.thumbnail import ImageField

from core.urls import reverse
from core.utils import ru_en_mapping
from projects.constants import ProjectTypes
from projects.models import Project, Supervisor
from users.constants import ThumbnailSizes, GenderTypes
from users.thumbnails import UserThumbnailMixin


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


def publication_photo_upload_to(instance: "ProjectPublication", filename):
    _, ext = os.path.splitext(filename)
    filename = instance.slug.replace("-", "_")
    return f"publications/projects/{filename}{ext}"


class ProjectPublicationQuerySet(models.QuerySet):
    pass


class _PublishedProjectsManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_draft=False)


PublishedProjectsManager = _PublishedProjectsManager.from_queryset(
    ProjectPublicationQuerySet)


class ProjectPublication(models.Model):
    created = models.DateTimeField(
        verbose_name=_("created"),
        editable=False,
        default=now)
    title = models.CharField(
        verbose_name=_("Title"),
        max_length=255)
    slug = models.SlugField(_("Slug"))
    is_draft = models.BooleanField(
        _("Draft"),
        default=False)
    authors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Authors"),
        related_name='+',
        through=ProjectPublicationAuthor)
    projects = models.ManyToManyField(
        Project,
        verbose_name=_("Projects"),
        related_name='publications')
    # XXX: Type is derivable only through admin interface
    type = models.CharField(
        choices=ProjectTypes.choices,
        editable=False,
        max_length=10)
    cover = ImageField(
        _("Cover"),
        upload_to=publication_photo_upload_to,
        help_text=_("Min height - 180px"),
        blank=True)
    description = models.TextField(
        verbose_name=_("Description"),
        blank=True)
    external_links = models.TextField(
        verbose_name=_("External Links"),
        blank=True)

    objects = models.Manager()
    published = PublishedProjectsManager()

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
        """
        Returns distinct students who participated in projects related to
        current publication.
        """
        participants = {}
        for project in self.projects.all():
            for student in project.students.all():
                if student.pk not in participants:
                    participants[student.pk] = student
        return list(participants.values())


def lecturer_photo_upload_to(instance: "Speaker", filename):
    _, ext = os.path.splitext(filename)
    filename = instance.abbreviated_name_in_latin
    return f"publications/speakers/{filename}{ext}"


class Speaker(UserThumbnailMixin, models.Model):
    first_name = models.CharField(_("First Name"), max_length=255)
    last_name = models.CharField(_("Surname"), max_length=255)
    patronymic = models.CharField(_("Patronymic"), max_length=255, blank=True)
    gender = models.CharField(_("Gender"), max_length=1,
                              choices=GenderTypes.choices,
                              default=GenderTypes.OTHER)
    description = models.TextField(_("Description"), blank=True)
    photo = models.ImageField(
        _("Photo"),
        upload_to=lecturer_photo_upload_to,
        blank=True,
        null=True,
        help_text=_("Aspect ratio 5:7. Min size: {}").format(ThumbnailSizes.BASE))
    workplace = models.CharField(_("Workplace"), max_length=255,
                                 blank=True, null=True)

    class Meta:
        verbose_name = _("Speaker")
        verbose_name_plural = _("Speakers")

    def __str__(self):
        return f"{self.full_name} [{self.workplace}]"

    @property
    def full_name(self):
        parts = (self.first_name, self.patronymic, self.last_name)
        return " ".join(p for p in parts if p).strip()

    @property
    def abbreviated_name(self):
        parts = [self.first_name[:1], self.patronymic[:1], self.last_name]
        return ". ".join(p for p in parts if p).strip()

    @property
    def abbreviated_name_in_latin(self):
        """
        Returns transliterated user surname + rest initials in lower case.
        Examples:
            Жуков Иван Викторович -> zhukov.i.v
            Иванов Кирилл -> ivanov.k
        """
        parts = (self.last_name, self.first_name[:1], self.patronymic[:1])
        parts = (p.lower() for p in parts if p)
        return ".".join(parts).translate(ru_en_mapping)


class RecordedEvent(TimeStampedModel):
    name = models.CharField(_("Title"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=70, unique=True)
    date_at = models.DateField(_("Event Date"))
    description = models.TextField(_("Description"), blank=True)
    video_url = models.URLField(
        _("Video URL"), blank=True, null=True,
        help_text=_("https://support.google.com/youtube/answer/171780?hl=en"))
    slides_url = models.URLField(_("Slides URL"), blank=True)
    speakers = models.ManyToManyField(
        Speaker,
        verbose_name=_("Speakers"),
        related_name='recorded_events')

    class Meta:
        verbose_name = _("Recorded Event")
        verbose_name_plural = _("Recorded Events")

    def __str__(self):
        return f"{self.name}"

    def get_absolute_url(self):
        return reverse("recorded_event_detail", kwargs={"slug": self.slug})

    def save(self, **kwargs):
        self.description = self.description.strip()
        super().save(**kwargs)

    @property
    def preview_url(self):
        video_id = self.video_url.rsplit('embed/', maxsplit=1)[-1]
        if video_id and not video_id.startswith("http"):
            return f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        else:
            return ""
