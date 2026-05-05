"""Tests for utils.py — file-save helpers and human_checkpoint."""

import os
from unittest.mock import patch

import pytest

from utils import _save_code_to_project, _save_to_md, human_checkpoint


# ─── _save_to_md ──────────────────────────────────────────────────────────────


def test_save_to_md_creates_file(tmp_path):
    project_dir = str(tmp_path / "myproject")
    os.makedirs(project_dir)
    import utils as utils_module
    import unittest.mock as mock
    with mock.patch.object(utils_module, "_MD_DIR", str(tmp_path / "outputs")):
        _save_to_md(1, "Architect", "architecture",
                    "# Design", project_dir=project_dir)
    md = tmp_path / "outputs" / "myproject" / "architect.md"
    assert md.exists()
    content = md.read_text()
    assert "Architect" in content
    assert "architecture" in content
    assert "# Design" in content


def test_save_to_md_appends_on_multiple_calls(tmp_path):
    project_dir = str(tmp_path / "myproject")
    os.makedirs(project_dir)
    import utils as utils_module
    import unittest.mock as mock
    with mock.patch.object(utils_module, "_MD_DIR", str(tmp_path / "outputs")):
        _save_to_md(1, "A", "f1", "first", project_dir=project_dir)
        _save_to_md(1, "A", "f2", "second", project_dir=project_dir)
    content = (tmp_path / "outputs" / "myproject" / "a.md").read_text()
    assert "first" in content
    assert "second" in content


def test_save_to_md_uses_fallback_outputs_dir(tmp_path, monkeypatch):
    import utils as utils_module

    monkeypatch.setattr(utils_module, "_MD_DIR", str(tmp_path))
    _save_to_md(2, "QA", "tests", "test content")
    assert (tmp_path / "task_2" / "qa.md").exists()


# ─── _save_code_to_project ────────────────────────────────────────────────────


def test_save_code_extracts_named_files(tmp_path):
    code = "```python main.py\nprint('hello')\n```"
    _save_code_to_project(1, code, project_dir=str(tmp_path))
    assert (tmp_path / "main.py").exists()
    assert (tmp_path / "main.py").read_text().strip() == "print('hello')"


def test_save_code_fallback_to_main_py(tmp_path):
    code = "print('no fenced filename here')"
    _save_code_to_project(1, code, project_dir=str(tmp_path))
    assert (tmp_path / "main.py").exists()


def test_save_code_sanitizes_path_traversal(tmp_path):
    code = "```python ../../evil.py\nmalicious\n```"
    _save_code_to_project(1, code, project_dir=str(tmp_path))
    # Must NOT create a file outside tmp_path
    assert not (tmp_path.parent / "evil.py").exists()
    # Should save as 'evil.py' inside tmp_path (basename only)
    assert (tmp_path / "evil.py").exists()


def test_save_code_multiple_files(tmp_path):
    code = "```python app.py\napp code\n```\n```python models.py\nmodels\n```"
    _save_code_to_project(1, code, project_dir=str(tmp_path))
    assert (tmp_path / "app.py").exists()
    assert (tmp_path / "models.py").exists()


# ─── human_checkpoint ─────────────────────────────────────────────────────────


def test_human_checkpoint_returns_content_when_disabled():
    with patch("utils.HUMAN_IN_THE_LOOP", False):
        result = human_checkpoint("Dev", "code", "my code")
    assert result == "my code"


def test_human_checkpoint_approve_on_enter(monkeypatch):
    with patch("utils.HUMAN_IN_THE_LOOP", True):
        monkeypatch.setattr("builtins.input", lambda _: "")
        result = human_checkpoint("Dev", "code", "my code")
    assert result == "my code"


def test_human_checkpoint_returns_feedback(monkeypatch):
    with patch("utils.HUMAN_IN_THE_LOOP", True):
        monkeypatch.setattr("builtins.input", lambda _: "fix the imports")
        result = human_checkpoint("Dev", "code", "my code")
    assert result == "fix the imports"
