import pytest
from datetime import datetime, date, time, timedelta
from mock_calendar.calendar_api import MockCalendarAPI
from mock_calendar.models import User, WorkingHours


@pytest.fixture
def temp_calendar(tmp_path):
    temp_file = str(tmp_path / "test_calendar.json")
    return MockCalendarAPI(data_file=temp_file)


def test_user_resolution(temp_calendar):
    # Test resolving known users
    users, unknown = temp_calendar.resolve_participants(["Alex", "bob", "Dana Vance"])
    user_names = [u.name for u in users]
    assert "Alex Rivera" in user_names
    assert "Bob Chen" in user_names
    assert "Dana Vance" in user_names
    assert len(unknown) == 0

    # Test unknown user
    users, unknown = temp_calendar.resolve_participants(["Elon Musk"])
    assert "Elon Musk" in unknown


def test_find_free_slots(temp_calendar):
    target_d = datetime.now().date() + timedelta(days=1)
    slots = temp_calendar.find_free_slots(
        participant_ids=["user_me", "user_alex"],
        target_date=target_d,
        duration_minutes=30,
    )
    assert len(slots) > 0
    for s in slots:
        assert s.start.date() == target_d
        assert (s.end - s.start).total_seconds() == 1800


def test_booking_conflict(temp_calendar):
    target_d = datetime.now().date() + timedelta(days=1)
    start_dt = datetime.combine(target_d, time(10, 0))
    end_dt = datetime.combine(target_d, time(11, 0))

    # user_alex is busy at 10:00 - 11:00 on Day 1 in seed data
    event, conflicts = temp_calendar.create_event(
        title="Test Conflict Meeting",
        participant_ids=["user_me", "user_alex"],
        start_time=start_dt,
        end_time=end_dt,
    )
    assert event is None
    assert len(conflicts) > 0
    assert "busy with" in conflicts[0].reason or "outside" in conflicts[0].reason


def test_successful_booking_and_cancellation(temp_calendar):
    target_d = datetime.now().date() + timedelta(days=1)
    # 12:00 PM is free for Alex and user_me
    start_dt = datetime.combine(target_d, time(12, 0))
    end_dt = datetime.combine(target_d, time(12, 30))

    event, conflicts = temp_calendar.create_event(
        title="Valid Lunch Sync",
        participant_ids=["user_me", "user_alex"],
        start_time=start_dt,
        end_time=end_dt,
    )
    assert event is not None
    assert len(conflicts) == 0
    assert event.status == "confirmed"

    # Now verify cancellation
    cancelled = temp_calendar.cancel_event(event.id)
    assert cancelled is True

