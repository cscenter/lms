import attr

from courses.calendar import CalendarEvent


@attr.s
class LearningCalendarEvent(CalendarEvent):
    @property
    def name(self):
        return self.event.name
