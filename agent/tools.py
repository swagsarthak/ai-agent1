from datetime import date, datetime
from typing import List, Dict, Any, Optional
from mock_calendar.calendar_api import MockCalendarAPI
from mock_calendar.models import TimeSlot, CalendarEvent, User


class AgentTools:
    """Tool execution layer for calendar and directory operations."""

    def __init__(self, calendar_api: MockCalendarAPI):
        self.calendar = calendar_api

    def list_team_members(self) -> List[Dict[str, Any]]:
        """List all team members and their working hours."""
        users = self.calendar.list_users()
        return [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "role": u.role,
                "working_hours": f"{u.working_hours.start_time} - {u.working_hours.end_time}",
            }
            for u in users
        ]

    def resolve_attendees(self, names: List[str]) -> Dict[str, Any]:
        """Resolves names or nicknames to user profiles in the company directory."""
        resolved, unknown = self.calendar.resolve_participants(names)
        return {
            "resolved_users": [u.model_dump() for u in resolved],
            "unknown_names": unknown,
        }

    def check_user_schedule(self, name_or_id: str, target_date: date) -> Dict[str, Any]:
        """Inspect a user's calendar schedule on a given date."""
        user = self.calendar.find_user_by_name_or_alias(name_or_id)
        if not user:
            return {"error": f"User '{name_or_id}' not found."}

        events = self.calendar.get_events_for_date(user.id, target_date)
        return {
            "user": user.name,
            "date": target_date.isoformat(),
            "events": [
                {
                    "title": e.title,
                    "start": e.start_time.strftime("%I:%M %p"),
                    "end": e.end_time.strftime("%I:%M %p"),
                }
                for e in events
            ],
        }

    def find_available_slots(
        self, participant_ids: List[str], target_date: date, duration_minutes: int = 30
    ) -> Dict[str, Any]:
        """Finds common free slots across all participants on the specified date."""
        slots = self.calendar.find_free_slots(
            participant_ids=participant_ids,
            target_date=target_date,
            duration_minutes=duration_minutes,
        )
        return {
            "date": target_date.isoformat(),
            "count": len(slots),
            "slots": [
                {
                    "formatted": s.format_slot(),
                    "start": s.start.isoformat(),
                    "end": s.end.isoformat(),
                }
                for s in slots
            ],
        }

    def check_slot_conflicts(
        self, participant_ids: List[str], start_time: datetime, end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Checks for direct conflicts with a proposed start and end time."""
        reports = self.calendar.check_conflicts(participant_ids, start_time, end_time)
        return [r.model_dump() for r in reports]

    def book_meeting(
        self,
        title: str,
        participant_ids: List[str],
        start_time: datetime,
        end_time: datetime,
        description: str = "",
    ) -> Dict[str, Any]:
        """Books a calendar event if no conflicts exist."""
        event, conflicts = self.calendar.create_event(
            title=title,
            participant_ids=participant_ids,
            start_time=start_time,
            end_time=end_time,
            description=description,
        )
        if conflicts:
            return {
                "success": False,
                "conflicts": [c.reason for c in conflicts if c.reason],
            }
        return {
            "success": True,
            "event": {
                "id": event.id,
                "title": event.title,
                "participants": [self.calendar.get_user_by_id(uid).name for uid in event.participants if self.calendar.get_user_by_id(uid)],
                "start": event.start_time.strftime("%Y-%m-%d %I:%M %p"),
                "end": event.end_time.strftime("%I:%M %p"),
                "description": event.description,
            },
        }

    def cancel_meeting(self, event_id: str) -> bool:
        return self.calendar.cancel_event(event_id)

