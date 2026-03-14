"""Test emotion storage: emotion_log table (append-only, includes neutral)."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from chatbot.memory.long_term import HealthEventStore


def test_log_emotion():
    """Emotion should be logged with user_input."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    try:
        with patch("chatbot.memory.long_term.DB_PATH", db_path):
            store = HealthEventStore()
            store.log_emotion("user_001", "sad", "我今天很难过")
            logs = store.get_today_emotions("user_001")
            assert len(logs) == 1
            assert logs[0]["emotion_label"] == "sad"
            assert logs[0]["user_input"] == "我今天很难过"
    finally:
        os.unlink(db_path)


def test_neutral_also_logged():
    """Neutral emotion should also be logged (append-only, no filtering)."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    try:
        with patch("chatbot.memory.long_term.DB_PATH", db_path):
            store = HealthEventStore()
            store.log_emotion("user_001", "neutral", "hello")
            logs = store.get_today_emotions("user_001")
            assert len(logs) == 1
            assert logs[0]["emotion_label"] == "neutral"
    finally:
        os.unlink(db_path)


def test_multiple_emotions_appended():
    """Multiple emotions should all be stored (no overwrite)."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    try:
        with patch("chatbot.memory.long_term.DB_PATH", db_path):
            store = HealthEventStore()
            store.log_emotion("user_001", "sad", "难过")
            store.log_emotion("user_001", "anxious", "焦虑")
            store.log_emotion("user_001", "neutral", "嗯嗯")
            logs = store.get_today_emotions("user_001")
            assert len(logs) == 3
    finally:
        os.unlink(db_path)
