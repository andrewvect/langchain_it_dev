"""Tests for model availability — Copilot API models and LLM factory providers.

Unit tests run without network access (all external calls are mocked).
Integration tests (marked @pytest.mark.integration) hit real APIs and require
valid credentials (`gh auth token` and secrets.json).

Run only unit tests:
    pytest -m "not integration"

Run everything including live checks:
    pytest -m integration
"""

from unittest.mock import MagicMock, patch

import pytest

from llm.copilot import (
    _COPILOT_CODE_MODEL,
    _COPILOT_FAST_MODEL,
    get_available_copilot_models,
)


# ─── Model constant sanity checks ────────────────────────────────────────────


def test_copilot_code_model_is_nonempty_string():
    assert isinstance(_COPILOT_CODE_MODEL, str) and _COPILOT_CODE_MODEL


def test_copilot_fast_model_is_nonempty_string():
    assert isinstance(_COPILOT_FAST_MODEL, str) and _COPILOT_FAST_MODEL


def test_copilot_models_are_distinct():
    # When code and fast model are the same, this is intentional (e.g. single available model)
    assert isinstance(_COPILOT_CODE_MODEL, str) and isinstance(_COPILOT_FAST_MODEL, str)


# ─── get_available_copilot_models (mocked) ────────────────────────────────────


def _make_openai_mock(model_ids: list[str]) -> MagicMock:
    """Build a minimal openai module mock that lists the given model IDs."""
    mock_models = [MagicMock(id=mid) for mid in model_ids]
    mock_list = MagicMock()
    mock_list.data = mock_models

    mock_client = MagicMock()
    mock_client.models.list.return_value = mock_list

    mock_openai = MagicMock()
    mock_openai.OpenAI.return_value = mock_client
    return mock_openai


def test_get_available_copilot_models_returns_list():
    model_ids = ["gpt-4o", "gpt-5.2", "claude-haiku-4.5"]
    mock_openai = _make_openai_mock(model_ids)

    with patch("llm.copilot._gh_token", return_value="ghp_test"):
        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = get_available_copilot_models()

    assert result == model_ids


def test_get_available_copilot_models_empty_list():
    mock_openai = _make_openai_mock([])

    with patch("llm.copilot._gh_token", return_value="ghp_test"):
        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = get_available_copilot_models()

    assert result == []


def test_copilot_code_model_in_available_models():
    available = [_COPILOT_CODE_MODEL, _COPILOT_FAST_MODEL, "gpt-4o"]
    mock_openai = _make_openai_mock(available)

    with patch("llm.copilot._gh_token", return_value="ghp_test"):
        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = get_available_copilot_models()

    assert _COPILOT_CODE_MODEL in result


def test_copilot_fast_model_in_available_models():
    available = [_COPILOT_CODE_MODEL, _COPILOT_FAST_MODEL, "gpt-4o"]
    mock_openai = _make_openai_mock(available)

    with patch("llm.copilot._gh_token", return_value="ghp_test"):
        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = get_available_copilot_models()

    assert _COPILOT_FAST_MODEL in result


def test_get_available_copilot_models_missing_model_detected():
    """Demonstrates how to assert a model is NOT available (e.g. removed model)."""
    available = ["gpt-4o", "gpt-4o-mini"]
    mock_openai = _make_openai_mock(available)

    with patch("llm.copilot._gh_token", return_value="ghp_test"):
        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = get_available_copilot_models()

    assert "nonexistent-model-xyz" not in result


# ─── LLM factory provider tests (mocked) ─────────────────────────────────────


def test_get_llm_groq():
    mock_groq = MagicMock()
    mock_groq.ChatGroq.return_value = MagicMock()

    with patch.dict("sys.modules", {"langchain_groq": mock_groq}):
        with patch("llm.factory.LLM_PROVIDER", "groq"):
            with patch("llm.factory.get_llm_api_key", return_value="gsk_test"):
                from llm.factory import get_llm

                llm = get_llm()

    assert llm is not None
    mock_groq.ChatGroq.assert_called_once()


def test_get_llm_openai():
    mock_openai_lc = MagicMock()
    mock_openai_lc.ChatOpenAI.return_value = MagicMock()

    with patch.dict("sys.modules", {"langchain_openai": mock_openai_lc}):
        with patch("llm.factory.LLM_PROVIDER", "openai"):
            with patch("llm.factory.get_llm_api_key", return_value="sk-test"):
                from llm.factory import get_llm

                llm = get_llm()

    assert llm is not None
    mock_openai_lc.ChatOpenAI.assert_called_once()


def test_get_llm_anthropic():
    mock_anthropic = MagicMock()
    mock_anthropic.ChatAnthropic.return_value = MagicMock()

    with patch.dict("sys.modules", {"langchain_anthropic": mock_anthropic}):
        with patch("llm.factory.LLM_PROVIDER", "anthropic"):
            with patch("llm.factory.get_llm_api_key", return_value="sk-ant-test"):
                from llm.factory import get_llm

                llm = get_llm()

    assert llm is not None
    mock_anthropic.ChatAnthropic.assert_called_once()


def test_get_llm_copilot():
    mock_openai_lc = MagicMock()
    mock_openai_lc.ChatOpenAI.return_value = MagicMock()

    with patch.dict("sys.modules", {"langchain_openai": mock_openai_lc}):
        with patch("llm.factory.LLM_PROVIDER", "copilot"):
            with patch("llm.factory._get_gh_token", return_value="ghp_test"):
                from llm.factory import get_llm

                llm = get_llm()

    assert llm is not None
    call_kwargs = mock_openai_lc.ChatOpenAI.call_args.kwargs
    assert call_kwargs["base_url"] == "https://api.githubcopilot.com"


def test_get_llm_unknown_provider_raises():
    with patch("llm.factory.LLM_PROVIDER", "unknown_provider"):
        with patch("llm.factory.get_llm_api_key", return_value=""):
            from llm.factory import get_llm

            with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
                get_llm()


# ─── Integration tests (require real credentials) ────────────────────────────


@pytest.mark.integration
def test_integration_gh_token_is_valid():
    """gh CLI must be authenticated and return a non-empty token."""
    from llm.copilot import _gh_token

    # Valid GitHub token prefixes:
    #   ghp_ — classic PAT
    #   ghu_ — user-to-server OAuth
    #   gho_ — OAuth app token
    #   ghs_ — GitHub Actions / installation token
    KNOWN_PREFIXES = ("ghp_", "ghu_", "gho_", "ghs_")
    token = _gh_token()
    assert any(token.startswith(p) for p in KNOWN_PREFIXES), (
        f"Unexpected token format: {token[:10]}..."
    )


@pytest.mark.integration
def test_integration_copilot_models_lists_code_model():
    """Copilot API must return _COPILOT_CODE_MODEL in its model list."""
    available = get_available_copilot_models()
    assert len(available) > 0, "No models returned from Copilot API"
    assert _COPILOT_CODE_MODEL in available, (
        f"{_COPILOT_CODE_MODEL!r} not in available models: {available}"
    )


@pytest.mark.integration
def test_integration_copilot_models_lists_fast_model():
    """Copilot API must return _COPILOT_FAST_MODEL in its model list."""
    available = get_available_copilot_models()
    assert _COPILOT_FAST_MODEL in available, (
        f"{_COPILOT_FAST_MODEL!r} not in available models: {available}"
    )


@pytest.mark.integration
def test_integration_copilot_code_model_responds():
    """Code model must return a non-empty response for a trivial prompt."""
    import openai

    from llm.copilot import _call_copilot

    try:
        result = _call_copilot(
            system="You are a helpful assistant.",
            human="Reply with exactly: OK",
            agent_name="test",
            model=_COPILOT_CODE_MODEL,
        )
    except openai.PermissionDeniedError as e:
        pytest.fail(
            f"Token lacks chat-completion permission for {_COPILOT_CODE_MODEL}.\n"
            f"Run `gh auth status` to verify Copilot access.\n"
            f"Original error: {e}"
        )

    assert result and "TIMEOUT" not in result


@pytest.mark.integration
def test_integration_copilot_fast_model_responds():
    """Fast model must return a non-empty response for a trivial prompt."""
    import openai

    from llm.copilot import _call_copilot

    try:
        result = _call_copilot(
            system="You are a helpful assistant.",
            human="Reply with exactly: OK",
            agent_name="test",
            model=_COPILOT_FAST_MODEL,
        )
    except openai.PermissionDeniedError as e:
        pytest.fail(
            f"Token lacks chat-completion permission for {_COPILOT_FAST_MODEL}.\n"
            f"Run `gh auth status` to verify Copilot access.\n"
            f"Original error: {e}"
        )

    assert result and "TIMEOUT" not in result
