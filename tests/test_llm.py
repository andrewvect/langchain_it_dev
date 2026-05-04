"""Tests for llm/copilot.py — Claude CLI and Copilot call helpers."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from llm.copilot import _call, _call_copilot, _gh_token


# ─── _gh_token ────────────────────────────────────────────────────────────────


def test_gh_token_returns_token():
    mock_result = MagicMock()
    mock_result.stdout = "ghp_test_token\n"
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        token = _gh_token()
    assert token == "ghp_test_token"
    mock_run.assert_called_once()


# ─── _call (Claude CLI) ───────────────────────────────────────────────────────


def test_call_returns_stdout_on_success():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "  architecture doc  "
    with patch("subprocess.run", return_value=mock_result):
        result = _call("system prompt", "human prompt", "Architect")
    assert result == "architecture doc"


def test_call_raises_on_nonzero_returncode():
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "some error"
    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="Claude CLI error"):
            _call("sys", "human")


def test_call_returns_timeout_message():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=300)):
        result = _call("sys", "human", "Architect")
    assert "TIMEOUT" in result
    assert "Architect" in result


# ─── _call_copilot ────────────────────────────────────────────────────────────


def test_call_copilot_returns_content():
    mock_message = MagicMock()
    mock_message.content = "generated code"
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp

    mock_openai = MagicMock()
    mock_openai.OpenAI.return_value = mock_client

    with patch("llm.copilot._gh_token", return_value="ghp_token"):
        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = _call_copilot("system", "human", "Developer")

    assert result == "generated code"


def test_call_copilot_timeout_message():
    import openai as real_openai

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = real_openai.APITimeoutError(
        request=MagicMock()
    )

    mock_openai = MagicMock()
    mock_openai.OpenAI.return_value = mock_client
    mock_openai.APITimeoutError = real_openai.APITimeoutError

    with patch("llm.copilot._gh_token", return_value="ghp_token"):
        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = _call_copilot("sys", "human", "Dev")

    assert "TIMEOUT" in result


def test_call_copilot_handles_none_content():
    mock_message = MagicMock()
    mock_message.content = None
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp

    mock_openai = MagicMock()
    mock_openai.OpenAI.return_value = mock_client

    with patch("llm.copilot._gh_token", return_value="ghp_token"):
        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = _call_copilot("system", "human")

    assert result == ""
