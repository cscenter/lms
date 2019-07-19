from django.db import models
from django.db.models import Subquery, Count


class SubqueryCount(Subquery):
    """
    There is no API in Django ORM for using aggregation inside subquery
    https://code.djangoproject.com/ticket/28296

    As a workaround, let's use `.annotate` but remove `GROUP BY` added by
    `values()`. Also make sure it returns 0 in case there is no aggregated data.

    Usage Example:
        subquery = Enrollment.objects.filter(course_id=OuterRef('id'))
        q = (Course.objects
            .filter(id=1)
            .update(learners_count=SubqueryCount(subquery)))
    """
    template = 'COALESCE((%(subquery)s), 0)'
    output_field = models.IntegerField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = self.queryset.annotate(cnt=Count("*")).values("cnt")
        # Remove GROUP BY added by `values()`
        self.queryset.query.set_group_by()
