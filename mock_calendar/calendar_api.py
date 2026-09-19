import json
import os
import uuid
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Tuple

from mock_calendar.models import User, CalendarEvent, TimeSlot, WorkingHours, ConflictReport


class MockCalendarAPI:
    """Mock Calendar Service managing users, schedules, busy intervals, and bookings."""

    def __init__(self, data_file: Optional[str] = None):
        self.data_file = data_file or os.path.join(os.path.dirname(__file__), "calendar_data.json")
        self.users: Dict[str, User] = {}
        self.events: List[CalendarEvent] = []
        self._load_or_initialize_data()

    def _get_default_seed_data(self) -> Tuple[List[User], List[CalendarEvent]]:
        users = [
            User(
                id="user_me",
                name="You",
                email="me@company.com",
                role="Organizer / Team Lead",
                timezone="EST",
                working_hours=WorkingHours(start_time="09:00", end_time="17:00", work_days=[0, 1, 2, 3, 4]),
            ),
            User(
                id="user_alex",
                name="Alex Rivera",
                email="alex.rivera@company.com",
                role="Senior Product Manager",
                timezone="EST",
                working_hours=WorkingHours(start_time="09:00", end_time="17:00", work_days=[0, 1, 2, 3, 4]),
            ),
            User(
                id="user_bob",
                name="Bob Chen",
                email="bob.chen@company.com",
                role="Staff Engineer",
                timezone="EST",
                working_hours=WorkingHours(start_time="10:00", end_time="18:00", work_days=[0, 1, 2, 3, 4]),
            ),
            User(
                id="user_charlie",
                name="Charlie Davis",
                email="charlie.davis@company.com",
                role="Lead UX Designer",
                timezone="EST",
                working_hours=WorkingHours(start_time="08:30", end_time="16:30", work_days=[0, 1, 2, 3, 4]),
            ),
            User(
                id="user_dana",
                name="Dana Vance",
                email="dana.vance@company.com",
                role="Director of Engineering",
                timezone="EST",
                working_hours=WorkingHours(start_time="09:00", end_time="17:00", work_days=[0, 1, 2, 3, 4]),
            ),
        ]

        # Populate realistic recurring/sample events for today and next few days
        base_date = datetime.now().date()
        events = []
        
        # Generate some sample busy slots for each day from today to +7 days
        sample_busy = [
            # Day 0 (today)
            (0, "user_alex", "Sprint Planning", "09:30", "11:00"),
            (0, "user_alex", "Product Review", "14:00", "15:30"),
            (0, "user_bob", "Architecture Sync", "10:30", "12:00"),
            (0, "user_bob", "Focus Time / Deep Work", "13:00", "15:00"),
            (0, "user_charlie", "Design Critique", "10:00", "11:30"),
            (0, "user_charlie", "User Research Session", "14:30", "16:00"),
            (0, "user_dana", "Executive Sync", "09:00", "10:30"),
            (0, "user_dana", "Budget Review", "15:00", "16:30"),

            # Day 1 (tomorrow)
            (1, "user_alex", "Customer Discovery Call", "10:00", "11:00"),
            (1, "user_alex", "1:1 with Dana", "15:00", "16:00"),
            (1, "user_bob", "Code Review / PR Backlog", "10:00", "11:30"),
            (1, "user_bob", "Backend Guild Sync", "14:00", "15:00"),
            (1, "user_charlie", "Prototype Testing", "09:00", "10:30"),
            (1, "user_charlie", "Wireframing Block", "13:00", "14:30"),
            (1, "user_dana", "1:1 with Alex", "15:00", "16:00"),
            (1, "user_dana", "All-Hands Prep", "11:00", "12:30"),

            # Day 2
            (2, "user_alex", "Roadmap Workshop", "09:00", "12:00"),
            (2, "user_alex", "Backlog Grooming", "13:30", "14:30"),
            (2, "user_bob", "Incident Postmortem", "11:00", "12:00"),
            (2, "user_bob", "Infrastructure Migration", "14:00", "17:00"),
            (2, "user_charlie", "Design System Working Group", "10:00", "12:00"),
            (2, "user_charlie", "Brand Review", "15:00", "16:00"),
            (2, "user_dana", "Strategy Offsite", "09:00", "17:00"),  # Fully booked
        ]

        for day_offset, uid, title, start_str, end_str in sample_busy:
            target_d = base_date + timedelta(days=day_offset)
            sh, sm = map(int, start_str.split(":"))
            eh, em = map(int, end_str.split(":"))
            start_dt = datetime.combine(target_d, time(sh, sm))
            end_dt = datetime.combine(target_d, time(eh, em))
            events.append(
                CalendarEvent(
                    id=str(uuid.uuid4())[:8],
                    title=title,
                    participants=[uid],
                    start_time=start_dt,
                    end_time=end_dt,
                    description=f"Standard calendar block for {title}",
                    status="confirmed",
                )
            )

        return users, events

    def _load_or_initialize_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                self.users = {u["id"]: User(**u) for u in raw.get("users", [])}
                self.events = [CalendarEvent(**e) for e in raw.get("events", [])]
                return
            except Exception:
                pass
        
        users, events = self._get_default_seed_data()
        self.users = {u.id: u for u in users}
        self.events = events
        self._save_data()

    def _save_data(self):
        data = {
            "users": [u.model_dump() for u in self.users.values()],
            "events": [
                {
                    **e.model_dump(),
                    "start_time": e.start_time.isoformat(),
                    "end_time": e.end_time.isoformat(),
                }
                for e in self.events
            ],
        }
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def reset_database(self):
        users, events = self._get_default_seed_data()
        self.users = {u.id: u for u in users}
        self.events = events
        self._save_data()

    def list_users(self) -> List[User]:
        return list(self.users.values())

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)

    def find_user_by_name_or_alias(self, query: str) -> Optional[User]:
        q = query.strip().lower()
        if not q:
            return None
        if q in ["me", "myself", "i", "you", "user"]:
            return self.users.get("user_me")
        
        for user in self.users.values():
            if q == user.id.lower() or q == user.name.lower() or q in user.name.lower().split():
                return user
            if q == user.email.lower() or q in user.email.lower():
                return user
        return None

    def resolve_participants(self, participant_queries: List[str]) -> Tuple[List[User], List[str]]:
        """Resolves names/emails/ids to User objects, returning (resolved_users, unknown_names)."""
        resolved = []
        unknown = []
        # Always ensure 'user_me' is included if not specified
        seen_ids = set()
        
        for q in participant_queries:
            user = self.find_user_by_name_or_alias(q)
            if user:
                if user.id not in seen_ids:
                    resolved.append(user)
                    seen_ids.add(user.id)
            else:
                unknown.append(q)
        
        # Ensure user_me is in participant list by default for meetings
        if "user_me" not in seen_ids and "user_me" in self.users:
            resolved.insert(0, self.users["user_me"])
            seen_ids.add("user_me")

        return resolved, unknown

    def get_events_for_date(self, user_id: str, target_date: date) -> List[CalendarEvent]:
        """Returns all confirmed events for a user on a given date."""
        day_events = []
        for event in self.events:
            if event.status == "confirmed" and user_id in event.participants:
                if event.start_time.date() == target_date or event.end_time.date() == target_date:
                    day_events.append(event)
        day_events.sort(key=lambda x: x.start_time)
        return day_events

    def check_conflicts(
        self, participant_ids: List[str], start_time: datetime, end_time: datetime
    ) -> List[ConflictReport]:
        """Checks if the proposed window conflicts with any participant's schedule or working hours."""
        conflicts: List[ConflictReport] = []
        
        for uid in participant_ids:
            user = self.get_user_by_id(uid)
            if not user:
                conflicts.append(
                    ConflictReport(
                        has_conflict=True,
                        conflicting_user_id=uid,
                        reason=f"User ID {uid} not found in system.",
                    )
                )
                continue

            # Check working days
            weekday = start_time.weekday()
            if weekday not in user.working_hours.work_days:
                conflicts.append(
                    ConflictReport(
                        has_conflict=True,
                        conflicting_user_id=uid,
                        reason=f"{user.name} does not work on {start_time.strftime('%A')}.",
                    )
                )
                continue

            # Check working hours
            sh, sm = map(int, user.working_hours.start_time.split(":"))
            eh, em = map(int, user.working_hours.end_time.split(":"))
            user_work_start = datetime.combine(start_time.date(), time(sh, sm))
            user_work_end = datetime.combine(start_time.date(), time(eh, em))

            if start_time < user_work_start or end_time > user_work_end:
                conflicts.append(
                    ConflictReport(
                        has_conflict=True,
                        conflicting_user_id=uid,
                        reason=f"Time is outside {user.name}'s working hours ({user.working_hours.start_time} - {user.working_hours.end_time}).",
                    )
                )
                continue

            # Check existing overlapping events
            for event in self.events:
                if event.status == "confirmed" and uid in event.participants:
                    if event.overlaps_with(start_time, end_time):
                        conflicts.append(
                            ConflictReport(
                                has_conflict=True,
                                conflicting_user_id=uid,
                                conflicting_event=event,
                                reason=f"{user.name} is busy with '{event.title}' ({event.start_time.strftime('%I:%M %p')} - {event.end_time.strftime('%I:%M %p')}).",
                            )
                        )
                        break

        return conflicts

    def find_free_slots(
        self,
        participant_ids: List[str],
        target_date: date,
        duration_minutes: int = 30,
        slot_increment_minutes: int = 30,
    ) -> List[TimeSlot]:
        """Finds common available free time slots for all participants on a given date."""
        if not participant_ids:
            return []

        users = [self.get_user_by_id(uid) for uid in participant_ids if self.get_user_by_id(uid)]
        if not users:
            return []

        # Find overlapping working window for all participants
        start_bounds = []
        end_bounds = []
        for u in users:
            if target_date.weekday() not in u.working_hours.work_days:
                return []  # Someone does not work on this day
            sh, sm = map(int, u.working_hours.start_time.split(":"))
            eh, em = map(int, u.working_hours.end_time.split(":"))
            start_bounds.append(datetime.combine(target_date, time(sh, sm)))
            end_bounds.append(datetime.combine(target_date, time(eh, em)))

        common_work_start = max(start_bounds)
        common_work_end = min(end_bounds)

        if common_work_start >= common_work_end:
            return []

        # Get all busy intervals for all participants
        busy_intervals: List[Tuple[datetime, datetime]] = []
        for uid in participant_ids:
            events = self.get_events_for_date(uid, target_date)
            for ev in events:
                busy_intervals.append((ev.start_time, ev.end_time))

        # Sort and merge busy intervals
        busy_intervals.sort(key=lambda x: x[0])
        merged_busy: List[Tuple[datetime, datetime]] = []
        for start, end in busy_intervals:
            if not merged_busy:
                merged_busy.append((start, end))
            else:
                prev_start, prev_end = merged_busy[-1]
                if start < prev_end:
                    merged_busy[-1] = (prev_start, max(prev_end, end))
                else:
                    merged_busy.append((start, end))

        # Iterate through common working hours in increments
        free_slots: List[TimeSlot] = []
        current_time = common_work_start
        delta = timedelta(minutes=slot_increment_minutes)
        slot_dur = timedelta(minutes=duration_minutes)

        while current_time + slot_dur <= common_work_end:
            slot_candidate_end = current_time + slot_dur
            
            # Check if candidate overlaps with any busy interval
            is_free = True
            for busy_start, busy_end in merged_busy:
                if max(current_time, busy_start) < min(slot_candidate_end, busy_end):
                    is_free = False
                    break
            
            if is_free:
                free_slots.append(TimeSlot(start=current_time, end=slot_candidate_end))
            
            current_time += delta

        return free_slots

    def create_event(
        self,
        title: str,
        participant_ids: List[str],
        start_time: datetime,
        end_time: datetime,
        description: str = "",
    ) -> Tuple[Optional[CalendarEvent], List[ConflictReport]]:
        """Attempts to book an event, checking for conflicts first."""
        conflicts = self.check_conflicts(participant_ids, start_time, end_time)
        if conflicts:
            return None, conflicts

        event = CalendarEvent(
            id=str(uuid.uuid4())[:8],
            title=title,
            participants=participant_ids,
            start_time=start_time,
            end_time=end_time,
            description=description,
            status="confirmed",
        )
        self.events.append(event)
        self._save_data()
        return event, []

    def cancel_event(self, event_id: str) -> bool:
        for ev in self.events:
            if ev.id == event_id:
                ev.status = "cancelled"
                self._save_data()
                return True
        return False

