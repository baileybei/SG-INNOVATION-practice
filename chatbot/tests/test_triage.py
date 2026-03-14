"""Test triage keyword pre-classification."""
from chatbot.agents.triage import keyword_preclassify


def test_medical_keywords():
    assert keyword_preclassify("我血糖有点高") == "medical"
    assert keyword_preclassify("吃了药") == "medical"


def test_non_medical_returns_none():
    """Non-medical input should return None (fall back to LLM, then companion)."""
    assert keyword_preclassify("我好难过") is None
    assert keyword_preclassify("今天天气不错") is None
    assert keyword_preclassify("你好") is None
