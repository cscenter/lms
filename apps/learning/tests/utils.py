def flatten_calendar_month_events(calendar_month):
    return [calendar_event.event for week in calendar_month.weeks()
            for day in week.days
            for calendar_event in day.events]
