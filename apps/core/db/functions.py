from django.db.models import DateField, Field
from django.db.models.functions.datetime import TruncBase


class TruncDateInTZ(TruncBase):
    """
    Works the same way as `django.db.models.functions.TruncDate`, but before
    truncation it converts datetime to the timezone provided with `tzinfo`
    argument. It's' useful for correct aggregation by local dates.
    Example:
        timezone = pytz.timezone('Europe/Moscow')
        ...
        .annotate(date=TruncDateInTZ('created', tzinfo=timezone)
        ...
        # Will produce the output
        SELECT ("created" AT TIME ZONE 'Europe/Moscow')::date
    """
    kind = 'date'
    lookup_name = 'date'
    output_field: Field = DateField()

    def as_sql(self, compiler, connection):
        # Cast to date rather than truncate to date.
        lhs, lhs_params = compiler.compile(self.lhs)
        tzname = self.tzinfo.tzname(None) if self.tzinfo else None
        sql = connection.ops.datetime_cast_date_sql(lhs, tzname)
        return sql, lhs_params
