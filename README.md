# 📅 AI Meeting Scheduler & Workflow Agent

An intelligent, multi-step agentic workflow system that schedules meetings across team calendars, detects and handles conflicts, interacts with a mock calendar API, and maintains conversation state with human-in-the-loop confirmation.

---

## 🌟 Key Features

1. **Multi-Step Agentic Architecture**:
   - **Perception & Entity Extraction**: Resolves attendee names, dates, durations, and time-of-day preferences from natural language.
   - **Calendar Tool Calling**: Integrates with a realistic mock calendar API to query busy intervals, calculate free slot intersections, and book events.
   - **State Machine Management**: Tracks the conversation across distinct states (`IDLE` $\rightarrow$ `COLLECTING_INFO` $\rightarrow$ `CHECKING_CALENDAR` $\rightarrow$ `PROPOSING_TIMES` $\rightarrow$ `AWAITING_CONFIRMATION` $\rightarrow$ `BOOKED` / `FAILED_OR_CONFLICT`).
   - **Conflict Resolution & Fallbacks**: Detects overlapping meetings or out-of-working-hours constraints and automatically suggests alternative days/slots.
   - **Human-in-the-Loop (HITL)**: Presents candidate slots for user confirmation before committing bookings.

2. **Interactive Streamlit Web Dashboard**:
   - Live two-way chat assistant with quick confirmation chips.
   - Visual team calendar grid showing schedules across team members.
   - **Agent Brain Inspector**: Transparent step-by-step logs of agent perceptions, tool invocations, and state transitions.
   - Pre-configured demo scenarios for instant testing.

3. **Offline & LLM Ready**:
   - Works immediately out-of-the-box with built-in semantic rule/NLP reasoning (zero API keys needed).
   - Can seamlessly integrate with Gemini/OpenAI API keys via environment variables.

---

## 📁 Project Structure

```
ai-agents/
├── README.md                   # Project documentation & guide
├── requirements.txt            # Python dependencies
├── mock_calendar/
│   ├── __init__.py
│   ├── models.py               # Pydantic schemas (User, CalendarEvent, TimeSlot, etc.)
│   └── calendar_api.py         # Mock calendar engine with conflict detection
├── agent/
│   ├── __init__.py
│   ├── state.py                # State machine & session memory
│   ├── tools.py                # Calendar tool execution wrappers
│   ├── llm_engine.py           # Intent parser & LLM connector
│   └── workflow.py             # Multi-step agent orchestrator
├── ui/
│   ├── app.py                  # Streamlit application
│   └── calendar_view.py        # Schedule visualizer component
└── tests/
    ├── test_calendar_api.py    # Unit tests for calendar arithmetic & conflicts
    └── test_workflow.py        # Unit tests for multi-turn agent states
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Interactive Web UI
```bash
streamlit run ui/app.py
```

### 3. Run Automated Tests
```bash
pytest -v
```

---

## 🧪 Example Conversions / Scenarios

### Scenario 1: Multi-Turn Discovery & Booking
- **User**: `"I want to set up a sync with Alex"`
- **Agent**: `"Got it, a meeting with Alex Rivera. What date or day of the week would you prefer?"`
- **User**: `"Tomorrow afternoon"`
- **Agent**: `"Here are the best available 30-minute options: 1. 11:00 AM, 2. 1:00 PM, 3. 2:00 PM. Please reply with option number."`
- **User**: `"Option 2"`
- **Agent**: `"🎉 Meeting Confirmed & Scheduled!"`

### Scenario 2: Automatic Conflict Resolution
- **User**: `"Schedule a 1 hour sync with Dana and Bob the day after tomorrow"`
- **Agent**: `"⚠️ Schedule Conflict: There are no overlapping free slots on Thursday. I checked upcoming days and found these alternatives: Friday 10:00 AM, Friday 2:00 PM..."`

