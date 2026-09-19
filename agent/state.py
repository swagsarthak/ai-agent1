from enum import Enum
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from mock_calendar.models import User, TimeSlot, CalendarEvent


class SchedulingState(str, Enum):
    IDLE = "IDLE"
    COLLECTING_INFO = "COLLECTING_INFO"
    CHECKING_CALENDAR = "CHECKING_CALENDAR"
    PROPOSING_TIMES = "PROPOSING_TIMES"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    BOOKED = "BOOKED"
    FAILED_OR_CONFLICT = "FAILED_OR_CONFLICT"


class SchedulingRequest(BaseModel):
    title: str = "Meeting"
    participant_names: List[str] = Field(default_factory=list)
    resolved_users: List[User] = Field(default_factory=list)
    unresolved_names: List[str] = Field(default_factory=list)
    target_date: Optional[date] = None
    date_query_str: Optional[str] = None
    duration_minutes: int = 30
    preferred_time_of_day: Optional[str] = None  # "morning", "afternoon", "any"
    exact_time: Optional[str] = None  # e.g., "14:00"
    description: str = ""


class ThoughtStep(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    stage: str  # "Perception", "Planning", "Tool Call", "Reasoning", "State Transition"
    detail: str


class ConversationTurn(BaseModel):
    sender: str  # "user" or "agent" or "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    state: Optional[SchedulingState] = None


class AgentSession(BaseModel):
    session_id: str
    state: SchedulingState = SchedulingState.IDLE
    current_request: SchedulingRequest = Field(default_factory=SchedulingRequest)
    proposed_slots: List[TimeSlot] = Field(default_factory=list)
    selected_slot: Optional[TimeSlot] = None
    booked_event: Optional[CalendarEvent] = None
    turns: List[ConversationTurn] = Field(default_factory=list)
    thought_logs: List[ThoughtStep] = Field(default_factory=list)

    def log_thought(self, stage: str, detail: str):
        self.thought_logs.append(ThoughtStep(stage=stage, detail=detail))

    def reset_request(self):
        self.state = SchedulingState.IDLE
        self.current_request = SchedulingRequest()
        self.proposed_slots = []
        self.selected_slot = None
        self.booked_event = None

