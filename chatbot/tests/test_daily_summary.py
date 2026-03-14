"""Test daily emotion summary: scheduled job logic."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from chatbot.memory.long_term import HealthEventStore


def _make_store():
    """Create a temp DB and return (store, db_path) for cleanup."""
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = Path(f.name)
    f.close()
    with patch("chatbot.memory.long_term.DB_PATH", db_path):
        store = HealthEventStore()
    return store, db_path


def test_emotion_summary_table_created():
    """emotion_summary table should exist after init."""
    store, db_path = _make_store()
    try:
        import sqlite3
        with sqlite3.connect(str(db_path)) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='emotion_summary'"
            ).fetchall()
        assert len(tables) == 1
    finally:
        os.unlink(db_path)


def test_save_and_get_emotion_summary():
    """save_emotion_summary should write, get_emotion_summaries should read."""
    store, db_path = _make_store()
    try:
        with patch("chatbot.memory.long_term.DB_PATH", db_path):
            store.save_emotion_summary("user_001", "患者今日情绪低落，因血糖控制不佳感到焦虑", "2026-03-13")
            summaries = store.get_emotion_summaries("user_001", days=7)
            assert len(summaries) == 1
            assert summaries[0]["text"] == "患者今日情绪低落，因血糖控制不佳感到焦虑"
            assert "2026-03-13" in summaries[0]["date"]
    finally:
        os.unlink(db_path)


def test_run_daily_summary_calls_llm_and_stores():
    """run_daily_summary should read today's log, call LLM, write summary."""
    store, db_path = _make_store()
    try:
        with patch("chatbot.memory.long_term.DB_PATH", db_path):
            # Seed some emotion logs
            store.log_emotion("user_001", "sad", "我今天很难过")
            store.log_emotion("user_001", "anxious", "血糖又高了好焦虑")

            from chatbot.jobs.daily_summary import run_daily_summary

            mock_llm = MagicMock(return_value="患者今日情绪波动较大，先是难过后又焦虑，可能与血糖控制有关。")
            with patch("chatbot.jobs.daily_summary.call_sealion", mock_llm):
                with patch("chatbot.jobs.daily_summary.get_health_store", return_value=store):
                    run_daily_summary()

            # Summary should be written
            summaries = store.get_emotion_summaries("user_001", days=1)
            assert len(summaries) == 1
            assert "情绪波动" in summaries[0]["text"]

    finally:
        os.unlink(db_path)


def test_run_daily_summary_skips_empty_users():
    """If no daily emotions, should not call LLM or write summary."""
    store, db_path = _make_store()
    try:
        with patch("chatbot.memory.long_term.DB_PATH", db_path):
            from chatbot.jobs.daily_summary import run_daily_summary

            mock_llm = MagicMock()
            with patch("chatbot.jobs.daily_summary.call_sealion", mock_llm):
                with patch("chatbot.jobs.daily_summary.get_health_store", return_value=store):
                    run_daily_summary()

            mock_llm.assert_not_called()
    finally:
        os.unlink(db_path)
