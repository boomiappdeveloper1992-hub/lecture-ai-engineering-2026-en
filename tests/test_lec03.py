"""Lecture 03 exercise and homework tests (no LLM or API key used)."""

import json
import sys
from pathlib import Path

import pytest
from pydantic_ai import DeferredToolRequests
from pydantic_ai.messages import ToolReturnPart
from pydantic_ai.models.test import TestModel

from app import agent as agent_module
from app import tools

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import lec03_compare_prompts as compare  # noqa: E402


def _descriptions(target):
    model = TestModel(call_tools=[])
    target.run_sync("Tool list", model=model)
    return {t.name: t.description for t in model.last_model_request_parameters.function_tools}


# ---------------------------------------------------------------- exercise: make_quiz
def test_make_quiz_returns_a_question_from_that_lecture():
    quiz = json.loads(tools.make_quiz(2))
    lecture2_terms = {e["term"]: e["definition"] for e in tools.load_glossary() if e["lecture"] == 2}
    term = next(t for t in lecture2_terms if f"“{t}”" in quiz["question"])
    assert quiz["answer"] == lecture2_terms[term]


def test_make_quiz_handles_a_lecture_without_terms():
    message = tools.make_quiz(0)
    assert "no glossary terms" in message and "02" in message


def test_make_quiz_is_offered_and_called():
    model = TestModel(call_tools=["make_quiz"])
    result = agent_module.agent.run_sync("Give me one review question from Lecture 02", model=model)
    assert any(isinstance(p, ToolReturnPart) and p.tool_name == "make_quiz" for m in result.all_messages() for p in m.parts)


# ---------------------------------------------------------------- homework (Implementation): save with approval
@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LOG_DIR", tmp_path / "learning_log")
    return tmp_path / "learning_log"


def test_save_learning_log_writes_markdown_and_never_overwrites(log_dir):
    first = tools.save_learning_log("LoRA notes", "Only small adapter matrices are trained.")
    second = tools.save_learning_log("LoRA notes", "Second record, same title.")
    files = sorted(log_dir.glob("*.md"))
    assert len(files) == 2 and "Saved" in first and "Saved" in second
    assert files[0].read_text(encoding="utf-8").startswith("# LoRA notes")
    assert tools.save_learning_log(" ", "x").startswith("Nothing was saved")


def test_save_pauses_for_approval_instead_of_writing(log_dir):
    result = agent_module.agent.run_sync("Save a note", model=TestModel(call_tools=["save_learning_log"]))
    assert isinstance(result.output, DeferredToolRequests)
    assert [c.tool_name for c in result.output.approvals] == ["save_learning_log"]
    assert not log_dir.exists()


@pytest.mark.parametrize("reply, saved", [("y", True), ("yes", True), ("n", False), ("", False)])
def test_cli_saves_only_after_a_yes(log_dir, reply, saved, capsys):
    model = TestModel(call_tools=["save_learning_log"])
    result = agent_module.run_with_approvals(agent_module.agent, "Save a note", model, input_fn=lambda prompt: reply)
    assert isinstance(result.output, str)
    assert log_dir.exists() == saved
    assert "[approval needed] save_learning_log" in capsys.readouterr().out


def test_no_terminal_means_no_save(log_dir):
    def no_terminal(prompt):
        raise EOFError
    agent_module.run_with_approvals(agent_module.agent, "Save a note", TestModel(call_tools=["save_learning_log"]), input_fn=no_terminal)
    assert not log_dir.exists()


# ---------------------------------------------------------------- homework (Basic): variants change one place each
def test_each_variant_changes_exactly_one_place():
    base_desc = _descriptions(agent_module.agent)
    for name, (_, kwargs) in compare.VARIANTS.items():
        variant = agent_module.build_agent(**kwargs)
        changed_instructions = kwargs.get("instructions", agent_module.INSTRUCTIONS) != agent_module.INSTRUCTIONS
        changed_tools = [t for t, d in _descriptions(variant).items() if d != base_desc[t]]
        assert int(changed_instructions) + len(changed_tools) == (0 if name == "baseline" else 1), name


def test_docstring_variant_reaches_the_model_and_keeps_the_function():
    kwargs = compare.VARIANTS["multi_term_docstring"][1]
    desc = _descriptions(agent_module.build_agent(**kwargs))["search_glossary"]
    assert "several terms" in desc and "only one term" not in desc
    copy = agent_module.with_docstring(tools.search_glossary, "doc")
    assert copy("LoRA") == tools.search_glossary("LoRA")


def test_comparison_script_records_calls_without_saving(log_dir):
    row = compare.run_once(agent_module.build_agent(), "What is LoRA?", TestModel())
    assert "search_glossary" in " ".join(row["calls"]) and row["requests"] >= 2
    assert not log_dir.exists()  # save_learning_log is denied automatically


def test_usage_counts_the_whole_question_across_an_approval_pause(log_dir):
    result = agent_module.run_with_approvals(agent_module.agent, "Save a note", TestModel(call_tools=["save_learning_log"]),
                                             input_fn=lambda prompt: "y")
    assert result.usage.requests == 2  # one request that paused + one after approval
