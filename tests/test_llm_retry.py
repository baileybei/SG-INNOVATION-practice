"""Tests for RetryVLM wrapper."""

from unittest.mock import MagicMock, call, patch
import pytest

from src.vision_agent.llm.base import VLMError
from src.vision_agent.llm.mock import MockVLM
from src.vision_agent.llm.retry import RetryVLM


class TestRetryVLM:
    def test_model_name_delegates(self):
        inner = MockVLM(forced_scene="FOOD")
        retry = RetryVLM(inner, max_retries=3)
        assert retry.model_name == inner.model_name

    def test_succeeds_on_first_try(self):
        inner = MockVLM(forced_scene="FOOD")
        retry = RetryVLM(inner, max_retries=3, delay_s=0)
        result = retry.call("prompt", "b64")
        assert "FOOD" in result

    def test_succeeds_after_one_failure(self):
        inner = MagicMock()
        inner.call.side_effect = [VLMError("timeout"), "success response"]
        retry = RetryVLM(inner, max_retries=3, delay_s=0)
        result = retry.call("prompt", "b64")
        assert result == "success response"
        assert inner.call.call_count == 2

    def test_succeeds_after_two_failures(self):
        inner = MagicMock()
        inner.call.side_effect = [
            VLMError("err1"),
            VLMError("err2"),
            "final success",
        ]
        retry = RetryVLM(inner, max_retries=3, delay_s=0)
        result = retry.call("prompt", "b64")
        assert result == "final success"
        assert inner.call.call_count == 3

    def test_raises_after_max_retries_exhausted(self):
        inner = MagicMock()
        inner.call.side_effect = VLMError("always fails")
        retry = RetryVLM(inner, max_retries=3, delay_s=0)
        with pytest.raises(VLMError, match="3 attempts"):
            retry.call("prompt", "b64")
        assert inner.call.call_count == 3

    def test_max_retries_one_means_no_retry(self):
        inner = MagicMock()
        inner.call.side_effect = VLMError("fail once")
        retry = RetryVLM(inner, max_retries=1, delay_s=0)
        with pytest.raises(VLMError):
            retry.call("prompt", "b64")
        assert inner.call.call_count == 1

    def test_delay_called_between_retries(self):
        inner = MagicMock()
        inner.call.side_effect = [VLMError("err"), VLMError("err"), "ok"]
        retry = RetryVLM(inner, max_retries=3, delay_s=0.5, backoff_factor=2.0)
        with patch("src.vision_agent.llm.retry.time.sleep") as mock_sleep:
            retry.call("prompt", "b64")
            # First retry: delay=0.5, second retry: delay=1.0
            assert mock_sleep.call_count == 2
            calls = mock_sleep.call_args_list
            assert calls[0] == call(0.5)
            assert calls[1] == call(1.0)

    def test_no_delay_on_final_failure(self):
        inner = MagicMock()
        inner.call.side_effect = VLMError("fail")
        retry = RetryVLM(inner, max_retries=2, delay_s=1.0)
        with patch("src.vision_agent.llm.retry.time.sleep") as mock_sleep:
            with pytest.raises(VLMError):
                retry.call("prompt", "b64")
            # Only 1 sleep (between attempt 1 and 2), not after final failure
            assert mock_sleep.call_count == 1


class TestRetryVLMCallMulti:
    def test_call_multi_succeeds(self):
        inner = MockVLM(forced_scene="FOOD")
        retry = RetryVLM(inner, max_retries=3, delay_s=0)
        result = retry.call_multi("prompt", ["b64"])
        assert "FOOD" in result

    def test_call_multi_retries_on_failure(self):
        inner = MagicMock()
        inner.call_multi.side_effect = [VLMError("timeout"), "success"]
        retry = RetryVLM(inner, max_retries=3, delay_s=0)
        result = retry.call_multi("prompt", ["b64"])
        assert result == "success"
        assert inner.call_multi.call_count == 2

    def test_call_multi_raises_after_exhausted(self):
        inner = MagicMock()
        inner.call_multi.side_effect = VLMError("always fails")
        retry = RetryVLM(inner, max_retries=2, delay_s=0)
        with pytest.raises(VLMError, match="2 attempts"):
            retry.call_multi("prompt", ["b64"])
        assert inner.call_multi.call_count == 2
