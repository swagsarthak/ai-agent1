from datetime import date, datetime, timedelta
from typing import List, Dict, Any
import streamlit as st

from mock_calendar.calendar_api import MockCalendarAPI
from mock_calendar.models import User, CalendarEvent


def render_calendar_grid(calendar_api: MockCalendarAPI, target_date: date, highlight_user_ids: List[str] = None):
    """Renders a clean visual timeline grid of team members' schedules for a selected date."""
    users = calendar_api.list_users()
    highlight_ids = highlight_user_ids or [u.id for u in users]
    
    st.markdown(f"#### 📅 Schedule for **{target_date.strftime('%A, %B %d, %Y')}**")

    # Time slots from 08:00 to 18:00
    hours = list(range(8, 19))
    
    for user in users:
        is_highlighted = user.id in highlight_ids
        card_border = "border: 2px solid #4CAF50;" if is_highlighted else "border: 1px solid #E0E0E0;"
        
        events = calendar_api.get_events_for_date(user.id, target_date)
        
        with st.container():
            st.markdown(
                f"""
                <div style="padding: 8px 12px; background: rgba(240, 242, 246, 0.5); border-radius: 8px; margin-bottom: 8px; {card_border}">
                    <strong>{user.name}</strong> <span style="color: #666; font-size: 0.85em;">({user.role})</span><br/>
                    <small style="color: #888;">Working Hours: {user.working_hours.start_time} - {user.working_hours.end_time}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )
            
            if not events:
                st.caption("🟢 Entire day is open / free")
            else:
                cols = st.columns(len(events) if len(events) <= 4 else 4)
                for i, ev in enumerate(events):
                    with cols[i % 4]:
                        status_color = "#E3F2FD" if ev.status == "confirmed" else "#FFEBEE"
                        border_color = "#2196F3" if ev.status == "confirmed" else "#F44336"
                        st.markdown(
                            f"""
                            <div style="background: {status_color}; border-left: 4px solid {border_color}; padding: 6px 10px; border-radius: 4px; margin-bottom: 6px; font-size: 0.85em;">
                                <strong>{ev.title}</strong><br/>
                                ⏱️ {ev.start_time.strftime('%I:%M %p')} - {ev.end_time.strftime('%I:%M %p')}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
            st.divider()

