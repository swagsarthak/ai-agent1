import os
import re
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dateutil import parser as date_parser

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


class IntentParser:
    """Parses user natural language queries into structured scheduling intent."""

    WEEKDAYS = {
        "monday": 0, "mon": 0,
        "tuesday": 1, "tue": 1, "tues": 1,
        "wednesday": 2, "wed": 2,
        "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
        "friday": 4, "fri": 4,
        "saturday": 5, "sat": 5,
        "sunday": 6, "sun": 6,
    }

    @staticmethod
    def parse_relative_date(text: str, base_date: Optional[date] = None) -> Optional[date]:
        base = base_date or datetime.now().date()
        lower = text.lower()

        if "today" in lower:
            return base
        if "tomorrow" in lower:
            return base + timedelta(days=1)
        if "day after tomorrow" in lower:
            return base + timedelta(days=2)

        # Match weekdays like "next Friday", "this Thursday", "on Monday"
        for name, target_weekday in IntentParser.WEEKDAYS.items():
            pattern = rf"\b(?:next\s+|this\s+|on\s+)?{name}\b"
            if re.search(pattern, lower):
                current_weekday = base.weekday()
                days_ahead = target_weekday - current_weekday
                if "next" in lower and days_ahead <= 0:
                    days_ahead += 7
                elif days_ahead <= 0:
                    days_ahead += 7
                return base + timedelta(days=days_ahead)

        # Match standard date patterns (e.g. 2026-09-18, Sep 18, 18th September)
        date_matches = re.findall(r"\b(?:\d{4}-\d{1,2}-\d{1,2}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\d{4})?|\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*(?:\s+\d{4})?)\b", lower)
        if date_matches:
            try:
                dt = date_parser.parse(date_matches[0], default=datetime(base.year, base.month, base.day))
                return dt.date()
            except Exception:
                pass

        return None

    @staticmethod
    def parse_duration(text: str) -> int:
        lower = text.lower()
        # Look for "1 hour", "1.5 hours", "2 hr", "30 mins", "45 min", "15m"
        hour_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hour|hr|hrs|h)\b", lower)
        if hour_match:
            return int(float(hour_match.group(1)) * 60)

        min_match = re.search(r"(\d+)\s*(?:min|mins|minute|minutes|m)\b", lower)
        if min_match:
            return int(min_match.group(1))

        if "quick sync" in lower or "standup" in lower:
            return 15
        if "workshop" in lower:
            return 60

        return 30  # Default 30 min

    @staticmethod
    def parse_time_preference(text: str) -> Tuple[Optional[str], Optional[str]]:
        """Returns (time_of_day_preference, exact_time_str)."""
        lower = text.lower()
        pref = None
        exact = None

        if "morning" in lower or "am" in lower and not re.search(r"\d+\s*am", lower):
            pref = "morning"
        elif "afternoon" in lower or "pm" in lower and not re.search(r"\d+\s*pm", lower):
            pref = "afternoon"

        # Check for specific time: e.g. "at 3 pm", "at 10:30am", "2:00 PM", "14:00"
        time_match = re.search(r"\b(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", lower)
        if time_match and ("at " in lower or "am" in lower or "pm" in lower or ":" in lower):
            hr = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            meridiem = time_match.group(3)
            
            if meridiem:
                if meridiem == "pm" and hr < 12:
                    hr += 12
                elif meridiem == "am" and hr == 12:
                    hr = 0
            exact = f"{hr:02d}:{minute:02d}"

        return pref, exact

    @staticmethod
    def parse_attendees(text: str, known_names: List[str]) -> List[str]:
        lower = text.lower()
        found = []
        for name in known_names:
            first_name = name.split()[0].lower()
            if re.search(rf"\b{first_name}\b", lower) or re.search(rf"\b{name.lower()}\b", lower):
                found.append(name)
        return found

    @staticmethod
    def detect_confirmation_choice(text: str, num_options: int) -> Optional[int]:
        """Detects if user is confirming or choosing an option (0-indexed)."""
        lower = text.lower().strip()
        
        # Explicit option numbers: "option 1", "1st", "number 2", "slot 3", "#1"
        opt_match = re.search(r"(?:option|slot|choice|number|#)?\s*(\d+)", lower)
        if opt_match and opt_match.group(1):
            val = int(opt_match.group(1))
            if 1 <= val <= num_options:
                return val - 1

        ordinal_map = {"first": 0, "1st": 0, "second": 1, "2nd": 1, "third": 2, "3rd": 2, "fourth": 3, "4th": 3}
        for ord_word, idx in ordinal_map.items():
            if ord_word in lower and idx < num_options:
                return idx

        # Generic positive affirmation chooses the first proposed slot
        confirm_words = ["yes", "yeah", "yep", "sure", "sounds good", "perfect", "let's do it", "confirm", "book it", "go ahead", "works for me", "awesome", "great"]
        if any(w in lower for w in confirm_words) and not any(neg in lower for neg in ["not", "don't", "no", "cancel"]):
            return 0

        return None

    @staticmethod
    def detect_cancellation(text: str) -> bool:
        lower = text.lower()
        cancel_phrases = ["cancel", "never mind", "stop", "abort", "reset", "start over", "forget it", "no thanks"]
        return any(p in lower for p in cancel_phrases)


class LLMEngine:
    """Combines deterministic intent parsing with LLM reasoning when configured."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.parser = IntentParser()

    def parse_user_input(
        self, user_text: str, known_names: List[str], base_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Extracts structured scheduling requirements from user prompt."""
        parsed_date = self.parser.parse_relative_date(user_text, base_date)
        duration = self.parser.parse_duration(user_text)
        pref, exact_time = self.parser.parse_time_preference(user_text)
        attendees = self.parser.parse_attendees(user_text, known_names)
        is_cancel = self.parser.detect_cancellation(user_text)

        # Extract meeting title if mentioned (e.g. "for Sprint Planning", "about Architecture Sync")
        title = "Meeting"
        title_match = re.search(r"(?:for|about|titled)\s+([A-Za-z0-9\s\-]+?)(?:\s+(?:with|on|at|tomorrow|next|for|\.|$))", user_text, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip().title()

        return {
            "attendees": attendees,
            "date": parsed_date,
            "duration": duration,
            "time_preference": pref,
            "exact_time": exact_time,
            "is_cancellation": is_cancel,
            "title": title,
        }

