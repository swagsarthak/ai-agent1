import os
import sys
from datetime import datetime, date, timedelta

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from mock_calendar.calendar_api import MockCalendarAPI
from agent.workflow import SchedulerWorkflowAgent
from agent.state import SchedulingState
from ui.calendar_view import render_calendar_grid

# Page setup
st.set_page_config(
    page_title="AI Meeting Scheduler & Workflow Agent",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        background: linear-gradient(90deg, #1E88E5, #7E57C2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .state-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .state-IDLE { background-color: #E8F5E9; color: #2E7D32; }
    .state-COLLECTING_INFO { background-color: #FFF8E1; color: #F57F17; }
    .state-CHECKING_CALENDAR { background-color: #E3F2FD; color: #1565C0; }
    .state-PROPOSING_TIMES { background-color: #EDE7F6; color: #512DA8; }
    .state-AWAITING_CONFIRMATION { background-color: #F3E5F5; color: #7B1FA2; }
    .state-BOOKED { background-color: #E8F5E9; color: #2E7D32; }
    .state-FAILED_OR_CONFLICT { background-color: #FFEBEE; color: #C62828; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Session State
if "calendar" not in st.session_state:
    st.session_state.calendar = MockCalendarAPI()

if "agent" not in st.session_state:
    st.session_state.agent = SchedulerWorkflowAgent(calendar_api=st.session_state.calendar)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "👋 **Hello! I'm your AI Scheduling Agent.**\n\nI can check team availability, resolve schedule conflicts, and book meetings across calendars.\n\nTry asking:\n- *'Schedule a 30m sync with Alex tomorrow afternoon'* \n- *'Book a 45 min design review with Charlie on Friday'* \n- *'Set up a team meeting with Bob and Dana'*",
        }
    ]

agent = st.session_state.agent
cal = st.session_state.calendar

# Header Row
col_title, col_state = st.columns([3, 1])
with col_title:
    st.markdown("<div class='main-header'>📅 AI Meeting Scheduler & Workflow Agent</div>", unsafe_allow_html=True)
    st.caption("Multi-step reasoning • Calendar Tool Calling • Conflict Detection • Human-in-the-Loop Confirmation")

with col_state:
    state_name = agent.session.state.value
    st.markdown(
        f"""
        <div style='text-align: right; padding-top: 10px;'>
            <span class='state-badge state-{state_name}'>Status: {state_name}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# Sidebar: Controls & Scenarios
with st.sidebar:
    st.header("⚡ Quick Demo Scenarios")
    
    if st.button("🤝 1:1 with Alex (Tomorrow)", use_container_width=True):
        st.session_state.scenario_input = "Schedule a 30m 1-on-1 with Alex tomorrow"

    if st.button("⚠️ Multi-Party Conflict Demo", use_container_width=True):
        st.session_state.scenario_input = "Schedule a 1 hour workshop with Dana and Bob for the day after tomorrow"

    if st.button("🎨 Design Sync with Charlie (Morning)", use_container_width=True):
        st.session_state.scenario_input = "Set up a 30 min sync with Charlie tomorrow morning"

    st.markdown("---")
    st.subheader("🛠️ Management")
    if st.button("🔄 Reset Calendar & Memory", use_container_width=True):
        cal.reset_database()
        st.session_state.agent = SchedulerWorkflowAgent(calendar_api=cal)
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "🔄 System and memory have been reset. What would you like to schedule?",
            }
        ]
        st.rerun()

    st.markdown("---")
    st.markdown("### ℹ️ Active Session Info")
    req = agent.session.current_request
    if req.resolved_users:
        st.write(f"**Attendees**: {', '.join([u.name for u in req.resolved_users])}")
    if req.target_date:
        st.write(f"**Date**: {req.target_date.strftime('%Y-%m-%d')}")
    st.write(f"**Duration**: {req.duration_minutes} mins")

# Main 2-Column Layout
left_col, right_col = st.columns([1.1, 1.2], gap="large")

# --- Left Column: Chat Interface ---
with left_col:
    st.subheader("💬 Scheduling Assistant")
    
    # Message History Container
    chat_container = st.container(height=480)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Quick action chips if awaiting confirmation
    if agent.session.state == SchedulingState.AWAITING_CONFIRMATION and agent.session.proposed_slots:
        st.markdown("**Quick Confirmation:**")
        chip_cols = st.columns(len(agent.session.proposed_slots) + 1)
        for i, slot in enumerate(agent.session.proposed_slots):
            with chip_cols[i]:
                if st.button(f"Option {i+1}", key=f"btn_opt_{i}", use_container_width=True):
                    st.session_state.scenario_input = f"Option {i+1}"
        with chip_cols[-1]:
            if st.button("❌ Cancel", key="btn_cancel", use_container_width=True):
                st.session_state.scenario_input = "cancel"

    # Chat Input handler
    prompt = st.chat_input("E.g., Schedule a 30m sync with Alex tomorrow afternoon...")
    
    # Check if a demo scenario or chip was clicked
    if "scenario_input" in st.session_state and st.session_state.scenario_input:
        prompt = st.session_state.scenario_input
        st.session_state.scenario_input = None

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        # Process with Agent
        response = agent.process_message(prompt)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

# --- Right Column: Live Calendar & Brain Inspector ---
with right_col:
    tab_calendar, tab_brain, tab_team = st.tabs(["📅 Live Calendar", "🧠 Agent Brain & Tools", "👥 Team Directory"])

    with tab_calendar:
        view_col1, view_col2 = st.columns([1, 1])
        with view_col1:
            default_d = agent.session.current_request.target_date or (datetime.now().date() + timedelta(days=1))
            selected_date = st.date_input("Select Date to View", value=default_d)
        with view_col2:
            all_users = cal.list_users()
            user_options = {u.name: u.id for u in all_users}
            selected_user_names = st.multiselect(
                "Filter Team Members",
                options=list(user_options.keys()),
                default=list(user_options.keys()),
            )
        
        selected_user_ids = [user_options[name] for name in selected_user_names]
        render_calendar_grid(cal, selected_date, selected_user_ids)

    with tab_brain:
        st.markdown("#### 🔍 Step-by-Step Agent Trace")
        if not agent.session.thought_logs:
            st.info("No thoughts recorded yet. Send a message to inspect agent reasoning!")
        else:
            for i, thought in enumerate(reversed(agent.session.thought_logs)):
                stage_colors = {
                    "Perception": "🟣",
                    "Planning": "🟡",
                    "Tool Call": "🔵",
                    "Reasoning": "🟠",
                    "Decision": "🟢",
                    "State Transition": "🔴",
                }
                icon = stage_colors.get(thought.stage, "⚪")
                with st.expander(f"{icon} Step {len(agent.session.thought_logs) - i}: {thought.stage} ({thought.timestamp.strftime('%H:%M:%S')})", expanded=(i == 0)):
                    st.write(thought.detail)

    with tab_team:
        st.markdown("#### 👥 Company Directory")
        for u in cal.list_users():
            st.markdown(
                f"""
                - **{u.name}** (`{u.email}`)
                  - **Role**: {u.role}
                  - **Timezone**: {u.timezone}
                  - **Working Hours**: {u.working_hours.start_time} to {u.working_hours.end_time}
                """
            )

