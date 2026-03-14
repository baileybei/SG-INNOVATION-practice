"""Test glucose_reader node."""
from chatbot.agents.glucose_reader import glucose_reader_node


_MOCK_CGM = [
    {"recorded_at": "2026-03-13T14:00:00", "glucose": 7.2},
    {"recorded_at": "2026-03-13T14:10:00", "glucose": 7.5},
    {"recorded_at": "2026-03-13T14:20:00", "glucose": 8.1},
]


def test_glucose_reader_returns_readings():
    state = {"user_id": "user_001"}
    result = glucose_reader_node(state)
    assert "glucose_readings" in result
    assert isinstance(result["glucose_readings"], list)


def test_glucose_reader_no_medication():
    """glucose_reader should NOT return medication data."""
    state = {"user_id": "user_001"}
    result = glucose_reader_node(state)
    assert "device_data" not in result
    assert "medication" not in result.get("glucose_readings", [{}])[0] if result.get("glucose_readings") else True
