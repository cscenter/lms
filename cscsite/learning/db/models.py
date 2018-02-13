from django.db.models import DecimalField


class GradeField(DecimalField):
    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value
        return value.normalize()
