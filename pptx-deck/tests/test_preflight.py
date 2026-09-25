# -*- coding: utf-8 -*-
"""Tests for the image checks in preflight.py: jq, and whether a key is set and valid.

    uv run --directory pptx-deck pytest

No test reaches OpenRouter. The `openrouter` fixture answers in its place.
"""
import io
import sys
import urllib.error
import urllib.request

import pytest

import preflight as P


@pytest.fixture
def no_keys(tmp_path, monkeypatch):
    """No key in the environment, and a HOME of its own, so a key file on this
    machine is never read."""
    for k in P.IMAGE_KEYS:
        monkeypatch.delenv(k, raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def openrouter(monkeypatch):
    """Call it with an HTTP code, or with an exception to raise. 200 accepts the key."""
    def answer(code_or_error):
        def urlopen(req, timeout=None):
            if isinstance(code_or_error, Exception):
                raise code_or_error
            if code_or_error == 200:
                return io.BytesIO(b'{"data": {}}')
            body = b'{"error": {"message": "API key expired", "code": %d}}' % code_or_error
            raise urllib.error.HTTPError(req.full_url, code_or_error, "", {}, io.BytesIO(body))
        monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    return answer


def test_keys_come_from_the_environment_then_the_user_file_then_the_project(no_keys, tmp_path,
                                                                           monkeypatch):
    user = no_keys / ".config" / "pptx-deck"
    user.mkdir(parents=True)
    (user / "image.env").write_text('OPENAI_API_KEY=sk-user\nGEMINI_API_KEY="sk-user"\n')
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text('export GEMINI_API_KEY="sk-project"\nXAI_API_KEY=sk-project\n'
                                   'GROK_API_KEY=\n# OPENROUTER_API_KEY=x\n')
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    assert P.image_keys() == {
        "OPENAI_API_KEY": ("sk-env", "the environment"),
        "GEMINI_API_KEY": ("sk-user", "~/.config/pptx-deck/image.env"),
        "XAI_API_KEY": ("sk-project", ".env"),
    }


@pytest.mark.parametrize("answer, state, detail", [
    pytest.param(200, "valid", "", id="accepted"),
    pytest.param(401, "invalid", "HTTP 401: API key expired", id="expired"),
    pytest.param(502, "unchecked", "HTTP 502", id="server error"),
    pytest.param(urllib.error.URLError("offline"), "unchecked", "offline", id="offline"),
])
def test_an_openrouter_key_is_asked_about_itself(openrouter, answer, state, detail):
    openrouter(answer)
    assert P.check_key("OPENROUTER_API_KEY", "sk-or") == (state, detail)


def test_other_keys_are_not_sent_anywhere(openrouter):
    openrouter(AssertionError("no request expected"))
    assert P.check_key("GEMINI_API_KEY", "sk-secret") == ("unchecked", "")


def test_present_but_invalid_is_not_reported_as_missing(no_keys, openrouter, tmp_path,
                                                        monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["preflight.py"])
    P.main()
    out = capsys.readouterr().out
    assert "MISS  image key                    (optional)" in out
    assert "put it in ~/.config/pptx-deck/image.env as NAME=..., mode 600" in out
    for page in ("https://openrouter.ai/keys", "https://aistudio.google.com/apikey",
                 "https://platform.openai.com/api-keys", "https://console.x.ai"):
        assert page in out
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-secret")
    openrouter(401)
    P.main()
    out = capsys.readouterr().out
    assert "MISS  image key OPENROUTER_API_KEY invalid, from the environment" in out
    assert "OpenRouter answered HTTP 401: API key expired" in out
    assert "make a new one at https://openrouter.ai/keys" in out
    assert "replace it in the environment" in out
    assert "aistudio" not in out
    assert "never paste it into the chat" in out
    assert "sk-secret" not in out


def test_without_sudo_jq_goes_into_the_home_directory(monkeypatch):
    monkeypatch.setattr(P, "BREW", False)
    monkeypatch.setattr(P, "APT", True)
    monkeypatch.setattr(P.shutil, "which", lambda name: None)
    cmd = P.jq_cmd()
    assert "sudo" not in cmd
    assert cmd.startswith("mkdir -p ~/.local/bin && curl -fsSL -o ~/.local/bin/jq ")
