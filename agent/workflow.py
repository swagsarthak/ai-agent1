from datetime import datetime, date, timedelta, time
from typing import Dict, Any, List, Optional, Tuple

from mock_calendar.calendar_api import MockCalendarAPI
from mock_calendar.models import TimeSlot, User, CalendarEvent
from agent.state import AgentSession, SchedulingState, SchedulingRequest, ThoughtStep, ConversationTurn
from agent.tools import AgentTools
from agent.llm_engine import LLMEngine, IntentParser


class SchedulerWorkflowAgent:
    """Multi-step Agent orchestrating calendar queries, conflict handling, and bookings."""

    def __init__(self, calendar_api: Optional[MockCalendarAPI] = None):
        self.calendar = calendar_api or MockCalendarAPI()
        self.tools = AgentTools(self.calendar)
        self.engine = LLMEngine()
        self.session = AgentSession(session_id="default_session")

    def process_message(self, user_message: str) -> str:
        """Main agent entrypoint: receives user message and advances state machine."""
        # Record user turn
        self.session.turns.append(ConversationTurn(sender="user", content=user_message, state=self.session.state))
        
        # 1. Check for cancellation
        if self.engine.parser.detect_cancellation(user_message):
            self.session.log_thought("Perception", f"User requested cancellation with input: '{user_message}'")
            self.session.reset_request()
            response = "I've cancelled the current scheduling request. Let me know when you'd like to schedule another meeting!"
            self.session.turns.append(ConversationTurn(sender="agent", content=response, state=self.session.state))
            return response

        # 2. Handle state: AWAITING_CONFIRMATION
        if self.session.state == SchedulingState.AWAITING_CONFIRMATION and self.session.proposed_slots:
            choice_idx = self.engine.parser.detect_confirmation_choice(user_message, len(self.session.proposed_slots))
            if choice_idx is not None:
                selected_slot = self.session.proposed_slots[choice_idx]
                self.session.selected_slot = selected_slot
                self.session.log_thought(
                    "Decision",
                    f"User confirmed slot #{choice_idx + 1}: {selected_slot.format_slot()}"
                )
                return self._execute_booking()

        # 3. Parse and accumulate info from input
        known_users = [u.name for u in self.calendar.list_users()]
        parsed = self.engine.parse_user_input(user_message, known_users)
        
        self.session.log_thought(
            "Perception",
            f"Extracted entities -> Attendees: {parsed['attendees']}, Date: {parsed['date']}, Duration: {parsed['duration']}m, Pref: {parsed['time_preference']}"
        )

        req = self.session.current_request
        if parsed["title"] and parsed["title"] != "Meeting":
            req.title = parsed["title"]
        if parsed["attendees"]:
            req.participant_names = list(set(req.participant_names + parsed["attendees"]))
        if parsed["date"]:
            req.target_date = parsed["date"]
        if parsed["duration"]:
            req.duration_minutes = parsed["duration"]
        if parsed["time_preference"]:
            req.preferred_time_of_day = parsed["time_preference"]
        if parsed["exact_time"]:
            req.exact_time = parsed["exact_time"]

        # Resolve user entities
        resolved_users, unknown = self.calendar.resolve_participants(req.participant_names)
        req.resolved_users = resolved_users
        req.unresolved_names = unknown

        # Check for missing required parameters
        other_attendees = [u for u in req.resolved_users if u.id != "user_me"]
        if not other_attendees and not req.unresolved_names:
            self.session.state = SchedulingState.COLLECTING_INFO
            self.session.log_thought("Planning", "Missing attendees. Prompting user for participants.")
            response = "Who would you like to schedule this meeting with? (Available team members: Alex Rivera, Bob Chen, Charlie Davis, Dana Vance)"
            self.session.turns.append(ConversationTurn(sender="agent", content=response, state=self.session.state))
            return response

        if req.unresolved_names:
            self.session.state = SchedulingState.COLLECTING_INFO
            self.session.log_thought("Planning", f"Unrecognized participants: {req.unresolved_names}")
            response = f"I couldn't find {', '.join(req.unresolved_names)} in the company directory. Did you mean Alex Rivera, Bob Chen, Charlie Davis, or Dana Vance?"
            self.session.turns.append(ConversationTurn(sender="agent", content=response, state=self.session.state))
            return response

        if not req.target_date:
            self.session.state = SchedulingState.COLLECTING_INFO
            self.session.log_thought("Planning", "Missing target date. Prompting user.")
            attendee_names = ", ".join([u.name for u in other_attendees])
            response = f"Got it, a meeting with {attendee_names}. What date or day of the week would you prefer (e.g., today, tomorrow, Friday)?"
            self.session.turns.append(ConversationTurn(sender="agent", content=response, state=self.session.state))
            return response

        # All basic info present -> Check calendar
        return self._search_and_propose_slots()

    def _search_and_propose_slots(self) -> str:
        req = self.session.current_request
        participant_ids = [u.id for u in req.resolved_users]
        target_date = req.target_date
        
        self.session.state = SchedulingState.CHECKING_CALENDAR
        self.session.log_thought(
            "Tool Call",
            f"Invoking tools.find_available_slots(participants={participant_ids}, date={target_date}, duration={req.duration_minutes}m)"
        )

        slots = self.calendar.find_free_slots(
            participant_ids=participant_ids,
            target_date=target_date,
            duration_minutes=req.duration_minutes,
        )

        # Filter by preference if specified
        filtered_slots = slots
        if req.exact_time:
            sh, sm = map(int, req.exact_time.split(":"))
            target_time = time(sh, sm)
            filtered_slots = [s for s in slots if s.start.time() == target_time]
            if not filtered_slots:
                self.session.log_thought("Reasoning", f"Exact time {req.exact_time} not available. Showing nearest available options.")
                filtered_slots = slots
        elif req.preferred_time_of_day == "morning":
            filtered_slots = [s for s in slots if s.start.hour < 12] or slots
        elif req.preferred_time_of_day == "afternoon":
            filtered_slots = [s for s in slots if s.start.hour >= 12] or slots

        # Scenario 1: Slots are available
        if filtered_slots:
            self.session.proposed_slots = filtered_slots[:3]
            self.session.state = SchedulingState.AWAITING_CONFIRMATION
            
            attendees_str = ", ".join([u.name for u in req.resolved_users if u.id != "user_me"])
            self.session.log_thought(
                "State Transition",
                f"Transitioned to AWAITING_CONFIRMATION. Presenting {len(self.session.proposed_slots)} slots."
            )

            options_text = "\n".join(
                [f"  **{i+1}.** {slot.format_slot()}" for i, slot in enumerate(self.session.proposed_slots)]
            )
            response = (
                f"I checked the calendar for **{attendees_str}** on **{target_date.strftime('%A, %B %d')}**.\n\n"
                f"Here are the best available **{req.duration_minutes}-minute** options:\n\n"
                f"{options_text}\n\n"
                f"Please reply with the option number (e.g. **1**, **2**) or say **'sounds good'** to confirm."
            )
            self.session.turns.append(ConversationTurn(sender="agent", content=response, state=self.session.state))
            return response

        # Scenario 2: No slots available (Conflict / Partial Failure handling)
        self.session.state = SchedulingState.FAILED_OR_CONFLICT
        self.session.log_thought(
            "Reasoning",
            f"Schedule conflict! 0 slots found for {participant_ids} on {target_date}. Searching alternative days."
        )

        # Inspect next 2 business days for alternatives
        alternatives: List[Tuple[date, List[TimeSlot]]] = []
        for offset in range(1, 4):
            alt_date = target_date + timedelta(days=offset)
            if alt_date.weekday() < 5:  # Monday-Friday
                alt_slots = self.calendar.find_free_slots(
                    participant_ids=participant_ids,
                    target_date=alt_date,
                    duration_minutes=req.duration_minutes,
                )
                if alt_slots:
                    alternatives.append((alt_date, alt_slots[:2]))

        attendees_str = ", ".join([u.name for u in req.resolved_users if u.id != "user_me"])
        if alternatives:
            alt_lines = []
            flat_alt_slots = []
            for alt_date, slist in alternatives:
                alt_lines.append(f"• **{alt_date.strftime('%A, %b %d')}**:")
                for s in slist:
                    flat_alt_slots.append(s)
                    idx = len(flat_alt_slots)
                    alt_lines.append(f"   **{idx}.** {s.start.strftime('%I:%M %p')} - {s.end.strftime('%I:%M %p')}")

            self.session.proposed_slots = flat_alt_slots
            self.session.state = SchedulingState.AWAITING_CONFIRMATION
            
            response = (
                f"⚠️ **Schedule Conflict**: There are no overlapping free slots with **{attendees_str}** on **{target_date.strftime('%A, %B %d')}**.\n\n"
                f"I checked upcoming days and found these alternatives:\n\n"
                + "\n".join(alt_lines)
                + f"\n\nWould you like to book one of these options, or pick a different date?"
            )
        else:
            response = (
                f"⚠️ **Schedule Conflict**: No available slots found for **{attendees_str}** on **{target_date.strftime('%A, %B %d')}** or nearby days.\n"
                f"Would you like to try a different week or adjust the meeting duration?"
            )

        self.session.turns.append(ConversationTurn(sender="agent", content=response, state=self.session.state))
        return response

    def _execute_booking(self) -> str:
        req = self.session.current_request
        slot = self.session.selected_slot
        participant_ids = [u.id for u in req.resolved_users]

        self.session.log_thought(
            "Tool Call",
            f"Invoking tools.book_meeting(title='{req.title}', start='{slot.start}', end='{slot.end}')"
        )

        res = self.tools.book_meeting(
            title=req.title,
            participant_ids=participant_ids,
            start_time=slot.start,
            end_time=slot.end,
            description=f"Scheduled by AI Workflow Agent for {', '.join([u.name for u in req.resolved_users])}",
        )

        if res.get("success"):
            self.session.state = SchedulingState.BOOKED
            ev = res["event"]
            self.session.booked_event = CalendarEvent(
                id=ev["id"],
                title=ev["title"],
                participants=participant_ids,
                start_time=slot.start,
                end_time=slot.end,
                description=ev["description"],
                status="confirmed",
            )
            self.session.log_thought(
                "State Transition",
                f"Meeting booked successfully with ID {ev['id']}. Resetting active request."
            )

            attendee_list = ", ".join(ev["participants"])
            response = (
                f"🎉 **Meeting Confirmed & Scheduled!**\n\n"
                f"• **Title**: {ev['title']}\n"
                f"• **Attendees**: {attendee_list}\n"
                f"• **Date & Time**: {ev['start']} - {ev['end']}\n"
                f"• **Event ID**: `{ev['id']}`\n\n"
                f"Calendar invites have been sent to all participants."
            )
            self.session.reset_request()
        else:
            self.session.state = SchedulingState.FAILED_OR_CONFLICT
            reasons = "\n".join([f"- {r}" for r in res.get("conflicts", [])])
            response = f"❌ **Booking Failed due to sudden conflict**:\n{reasons}\n\nPlease choose another time."

        self.session.turns.append(ConversationTurn(sender="agent", content=response, state=self.session.state))
        return response

