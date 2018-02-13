from django.db.models import DecimalField


class GradeField(DecimalField):
    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value
        decimal_as_int = value.to_integral_value()
        if value == decimal_as_int:
            return decimal_as_int
        return value.normalize()
