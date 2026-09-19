import pytest
from datetime import datetime, date, timedelta
from mock_calendar.calendar_api import MockCalendarAPI
from agent.workflow import SchedulerWorkflowAgent
from agent.state import SchedulingState


@pytest.fixture
def agent(tmp_path):
    temp_file = str(tmp_path / "test_calendar_workflow.json")
    cal = MockCalendarAPI(data_file=temp_file)
    return SchedulerWorkflowAgent(calendar_api=cal)


def test_multi_turn_booking_flow(agent):
    # Step 1: User gives partial info (missing date)
    resp1 = agent.process_message("I need to schedule a 30 min sync with Alex")
    assert agent.session.state == SchedulingState.COLLECTING_INFO
    assert "date" in resp1.lower() or "day" in resp1.lower()

    # Step 2: User provides date
    resp2 = agent.process_message("tomorrow morning")
    assert agent.session.state == SchedulingState.AWAITING_CONFIRMATION
    assert len(agent.session.proposed_slots) > 0
    assert "best available" in resp2.lower()

    # Step 3: User confirms option 1
    resp3 = agent.process_message("Option 1")
    assert agent.session.state == SchedulingState.IDLE  # reset after booking
    assert "Meeting Confirmed" in resp3
    assert len(agent.calendar.events) > 0


def test_single_prompt_full_booking(agent):
    # Single prompt with all required details
    resp = agent.process_message("Schedule a 30m review with Bob Chen tomorrow at 2 PM")
    assert agent.session.state == SchedulingState.AWAITING_CONFIRMATION
    assert len(agent.session.proposed_slots) > 0

    # Confirm
    resp_conf = agent.process_message("sounds good")
    assert "Meeting Confirmed" in resp_conf


def test_cancellation(agent):
    agent.process_message("Book a meeting with Charlie")
    assert agent.session.state == SchedulingState.COLLECTING_INFO

    cancel_resp = agent.process_message("Never mind, cancel that")
    assert agent.session.state == SchedulingState.IDLE
    assert "cancelled" in cancel_resp.lower()


def test_thought_logging(agent):
    agent.process_message("Set up a 15 min quick sync with Dana tomorrow")
    assert len(agent.session.thought_logs) > 0
    stages = [log.stage for log in agent.session.thought_logs]
    assert "Perception" in stages
    assert "Tool Call" in stages

