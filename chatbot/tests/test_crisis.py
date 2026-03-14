"""Test crisis detection in triage layer."""
from chatbot.agents.triage import is_crisis


def test_crisis_chinese_patterns():
    assert is_crisis("我不想活了")
    assert is_crisis("活着没什么意思")
    assert is_crisis("我想伤害自己")


def test_crisis_english_patterns():
    assert is_crisis("I want to die")
    assert is_crisis("no point living anymore")


def test_non_crisis_not_triggered():
    assert not is_crisis("我今天很难过")
    assert not is_crisis("血糖高了怎么办")
    assert not is_crisis("打卡")
