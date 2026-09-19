from datetime import datetime, time
from typing import List, Optional
from pydantic import BaseModel, Field


class WorkingHours(BaseModel):
    start_time: str = "09:00"  # HH:MM 24h format
    end_time: str = "17:00"    # HH:MM 24h format
    work_days: List[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])  # 0=Monday, 6=Sunday


class User(BaseModel):
    id: str
    name: str
    email: str
    role: str
    timezone: str = "UTC"
    working_hours: WorkingHours = Field(default_factory=WorkingHours)


class TimeSlot(BaseModel):
    start: datetime
    end: datetime

    def format_slot(self) -> str:
        return f"{self.start.strftime('%Y-%m-%d (%a) %I:%M %p')} - {self.end.strftime('%I:%M %p')}"


class CalendarEvent(BaseModel):
    id: str
    title: str
    participants: List[str]  # List of user IDs or names
    start_time: datetime
    end_time: datetime
    description: Optional[str] = ""
    status: str = "confirmed"  # confirmed, cancelled

    def overlaps_with(self, start: datetime, end: datetime) -> bool:
        if self.status == "cancelled":
            return False
        return max(self.start_time, start) < min(self.end_time, end)


class ConflictReport(BaseModel):
    has_conflict: bool
    conflicting_user_id: Optional[str] = None
    conflicting_event: Optional[CalendarEvent] = None
    reason: Optional[str] = None

