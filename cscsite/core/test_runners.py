from django_coverage.coverage_runner import CoverageRunner
from django.test.runner import DiscoverRunner  # Django 1.6's default
from colour_runner.django_runner import ColourRunnerMixin


class ColoredRunner(ColourRunnerMixin, DiscoverRunner):
    pass


class ColoredCoverageRunner(ColourRunnerMixin, CoverageRunner):
    pass
