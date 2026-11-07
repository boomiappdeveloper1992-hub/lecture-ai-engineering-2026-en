"""Lecture 01 tests for app/ask.py and scripts/lec01_experiments.py (no LLM or API key used)."""

import sys
from pathlib import Path
from types import SimpleNamespace

from google.genai import errors

from app import ask

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import lec01_experiments as exp  # noqa: E402


def usage(prompt=10, out=5, think=None):
    total = prompt + out + (think or 0)
    return SimpleNamespace(prompt_token_count=prompt, candidates_token_count=out,
                           thoughts_token_count=think, total_token_count=total)


class FakeModels:
    """Stands in for client.models: records what was sent, answers with a numbered reply."""
    def __init__(self, fail_with=None):
        self.sent, self.fail_with = [], fail_with

    def generate_content(self, model, contents, config=None):
        if self.fail_with:
            raise self.fail_with
        self.sent.append(list(contents) if isinstance(contents, list) else contents)
        n = len(self.sent)
        prompt = 10 * len(contents) if isinstance(contents, list) else 10
        return SimpleNamespace(text=f"answer {n}", usage_metadata=usage(prompt=prompt, out=5, think=3))


def fake_client(**kw):
    return SimpleNamespace(models=FakeModels(**kw))


def test_format_usage_shows_input_output_and_thinking():
    assert ask.format_usage(usage(12, 34)) == "[tokens] input=12 output=34 total=46"
    assert ask.format_usage(usage(12, 34, 7)) == "[tokens] input=12 output=34 thinking=7 total=53"
    assert ask.format_usage(None) == "[tokens] not reported"


def test_make_config_only_sets_temperature_when_given():
    assert ask.make_config(None) is None
    assert ask.make_config(0.0).temperature == 0.0


def test_chat_turn_sends_the_whole_history_each_time():
    client, history = fake_client(), []
    ask.chat_turn(client, history, "What is LoRA?")
    ask.chat_turn(client, history, "How is it different from QLoRA?")
    first, second = client.models.sent
    assert len(first) == 1 and len(second) == 3          # user / model / user
    assert [c.role for c in history] == ["user", "model", "user", "model"]
    assert history[1].parts[0].text == "answer 1"         # the model's earlier answer is kept
    assert history[2].parts[0].text == "How is it different from QLoRA?"


def test_chat_turn_drops_the_question_when_the_call_fails():
    client, history = fake_client(fail_with=errors.APIError(429, {"error": {"message": "slow down"}})), []
    try:
        ask.chat_turn(client, history, "hello")
    except errors.APIError:
        pass
    assert history == []


def test_chat_loop_handles_reset_and_exit(monkeypatch, capsys):
    client = fake_client()
    monkeypatch.setattr(ask.genai, "Client", lambda api_key: client)
    monkeypatch.setattr(ask, "get_api_key", lambda: "test")
    inputs = iter(["second question", "/reset", "after reset", "exit"])
    ask.chat("first question", None, input_fn=lambda prompt: next(inputs))
    sent = client.models.sent
    assert [len(s) for s in sent] == [1, 3, 1]            # history grew, then /reset cleared it
    assert "turns in history: 2" in capsys.readouterr().out


def test_experiments_record_timing_tokens_and_summary(tmp_path, monkeypatch):
    client = fake_client()
    monkeypatch.setattr(exp.genai, "Client", lambda api_key: client)
    monkeypatch.setattr(exp, "get_api_key", lambda: "test")
    out = tmp_path / "results"
    monkeypatch.setattr(sys, "argv", ["x", "--models", "m1", "m2", "--temperatures", "0", "1",
                                      "--questions", "q1", "--runs", "2", "--sleep", "0", "--out", str(out)])
    exp.main()
    csv_text = out.with_suffix(".csv").read_text(encoding="utf-8")
    md = out.with_suffix(".md").read_text(encoding="utf-8")
    assert csv_text.count("\n") == 1 + 2 * 2 * 1 * 2      # header + 8 calls
    assert "| m2 | 1.0 | q1 | 2/2 |" in md
    assert "Calls: 8 (8 succeeded, 0 failed)" in md
    assert "thinking tokens" in md


def test_experiments_retry_once_on_rate_limit(monkeypatch):
    calls = {"n": 0}

    class Flaky:
        def generate_content(self, model, contents, config=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise errors.APIError(429, {"error": {"message": "rate limit"}})
            return SimpleNamespace(text="ok", usage_metadata=usage())

    monkeypatch.setattr(exp.time, "sleep", lambda s: None)
    row = exp.call_once(SimpleNamespace(models=Flaky()), "m", "q", None, retry_wait=0)
    assert row["ok"] and calls["n"] == 2
