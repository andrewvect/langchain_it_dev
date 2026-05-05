"""Tests for config.py — secret loading and derived values."""

import json
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

import config


def _make_secrets(overrides: dict | None = None) -> dict:
    base = {
        "groq": {"api_key": "gsk_test"},
        "anthropic": "sk-ant-test",
        "jira": {
            "base_url": "https://example.atlassian.net",
            "email": "dev@example.com",
            "api_token": "jira-token",
        },
    }
    if overrides:
        base.update(overrides)
    return base


@pytest.fixture()
def mock_secrets(tmp_path: Path):
    secrets = _make_secrets()
    secrets_file = tmp_path / "secrets.json"
    secrets_file.write_text(json.dumps(secrets))
    with patch.object(config, "_SECRETS_PATH", secrets_file):
        yield secrets


def test_load_secrets_returns_dict(mock_secrets):
    result = config.load_secrets()
    assert isinstance(result, dict)
    assert "groq" in result


def test_get_jira_config(mock_secrets):
    cfg = config.get_jira_config()
    assert cfg["base_url"] == "https://example.atlassian.net"
    assert cfg["email"] == "dev@example.com"
    assert cfg["api_token"] == "jira-token"


def test_get_jira_config_missing_section(tmp_path: Path):
    secrets_file = tmp_path / "secrets.json"
    secrets_file.write_text(json.dumps({}))
    with patch.object(config, "_SECRETS_PATH", secrets_file):
        cfg = config.get_jira_config()
    assert cfg == {"base_url": "", "email": "", "api_token": ""}


@pytest.mark.parametrize(
    "provider,expected_key",
    [
        ("groq", "gsk_test"),
        ("anthropic", "sk-ant-test"),
    ],
)
def test_get_llm_api_key(mock_secrets, provider, expected_key):
    with patch.object(config, "LLM_PROVIDER", provider):
        key = config.get_llm_api_key()
    assert key == expected_key


def test_get_llm_api_key_copilot_returns_empty(mock_secrets):
    with patch.object(config, "LLM_PROVIDER", "copilot"):
        key = config.get_llm_api_key()
    assert key == ""


def test_get_llm_api_key_missing_raises(tmp_path: Path):
    secrets_file = tmp_path / "secrets.json"
    secrets_file.write_text(json.dumps({}))
    with patch.object(config, "_SECRETS_PATH", secrets_file):
        with patch.object(config, "LLM_PROVIDER", "groq"):
            with pytest.raises(ValueError, match="not found"):
                config.get_llm_api_key()
