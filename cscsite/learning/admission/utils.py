import datetime


def slot_range(start_at, end_at, step):
    current = datetime.timedelta(hours=start_at.hour, minutes=start_at.minute)
    end_at = datetime.timedelta(hours=end_at.hour, minutes=end_at.minute)
    while current < end_at:
        in_datetime = datetime.datetime.min + current
        # (start_at : datetime.time, end_at: datetime.time)
        yield in_datetime.time(), (in_datetime + step).time()
        current += step
