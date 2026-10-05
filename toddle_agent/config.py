import os
from pathlib import Path

TODDLE_URL = os.getenv("TODDLE_URL", "https://web.toddleapp.com")
MODEL = os.getenv("TODDLE_AGENT_MODEL", "claude-sonnet-5-5")
SESSION_DIR = Path(os.getenv("TODDLE_SESSION_DIR", ".toddle_session"))
STATE_FILE = SESSION_DIR / "state.json"
OUT_DIR = Path(os.getenv("TODDLE_OUT_DIR", "out"))
STUDENT_NAME = os.getenv("STUDENT_NAME", "my son")
STUDENT_GRADE = os.getenv("STUDENT_GRADE", "")  # e.g. "Grade 5"
# Comma-separated page paths to read after login. Adjust to what your school's Toddle shows.
# If TODDLE_PAGES is unset the agent finds the right pages itself by reading Toddle's menu.
PAGES_EXPLICIT = bool(os.getenv("TODDLE_PAGES"))
PAGES = [p.strip() for p in os.getenv("TODDLE_PAGES", "").split(",") if p.strip()]
