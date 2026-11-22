"""Lecture 05 homework (Advanced) tests: Graph + re-ranking. No API key needed.

The question embedding is replaced by the stored embedding of a real page, so retrieval runs on the real
index and graph without calling the embedding API.
"""

import json
import sqlite3
import struct
import sys
from pathlib import Path

import pytest
import sqlite_vec
from pydantic_ai.models.test import TestModel

from app import agent as agent_module
from app import retrieval
from app.config import GRAPH_HOPS, GRAPH_MAX_RESULTS, GRAPH_START_K, RAG_DB

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import lec05_compare as compare  # noqa: E402


def stored_vector(page_id: str) -> list[float]:
    db = sqlite3.connect(str(RAG_DB))
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    blob = db.execute("SELECT embedding FROM chunks WHERE page_id = ?", (page_id,)).fetchone()[0]
    db.close()
    return list(struct.unpack(f"{len(blob) // 4}f", blob))


@pytest.fixture
def question_like(monkeypatch):
    """Make every query embed to the stored vector of the given page."""
    def use(page_id):
        vector = stored_vector(page_id)
        monkeypatch.setattr(retrieval, "embed_text", lambda text, task_type: vector)
    return use


def test_ranked_graph_keeps_seeds_and_respects_limits(question_like):
    question_like("lec03-main-p039")
    ranked = retrieval.search_graph_ranked("memory")
    plain = retrieval.search("memory")
    assert [s["page_id"] for s in ranked["seeds"]] == [p["page_id"] for p in plain[:GRAPH_START_K]]
    ids = [p["page_id"] for p in ranked["seeds"] + ranked["expanded"]]
    assert len(ids) == len(set(ids)) <= GRAPH_MAX_RESULTS
    distances = [p["distance"] for p in ranked["expanded"]]
    assert distances == sorted(distances)
    assert all(d <= ranked["distance_threshold"] for d in distances)
    assert all(1 <= p["hops"] <= GRAPH_HOPS and p["path"][-1]["id"] == p["page_id"] for p in ranked["expanded"])
    assert 0 <= ranked["dropped_as_too_far"] <= ranked["candidates_scored"]


def test_ranked_graph_reaches_evidence_the_others_miss(question_like):
    """With a memory question, p.13 (2 hops via a shared term) is found only after re-ranking, with fewer pages."""
    question_like("lec03-main-p039")
    evidence = set(compare.QUESTIONS["memory"]["evidence"])
    ranked = {p["page_id"] for p in compare.pages_of(retrieval.search_graph_ranked("q"))}
    graph = {p["page_id"] for p in compare.pages_of(retrieval.search_graph("q"))}
    vector = {p["page_id"] for p in retrieval.search("q")}
    assert len(evidence & ranked) > len(evidence & graph)
    assert len(evidence & ranked) > len(evidence & vector)
    assert len(ranked) < len(graph)


def test_empty_query_is_rejected():
    with pytest.raises(ValueError):
        retrieval.search_graph_ranked("  ")


def test_agent_mode_calls_the_ranked_tool_and_trace_lists_pages(question_like, capsys):
    question_like("lec02-main-p052")
    with agent_module.agent.override(instructions=agent_module.GRAPH_RERANK_INSTRUCTIONS,
                                     tools=[agent_module.tools.search_graph_ranked]):
        result = agent_module.agent.run_sync("LoRA", model=TestModel(call_tools=["search_graph_ranked"]))
    agent_module.print_trace(result, 0.1)
    out = capsys.readouterr().out
    assert "search_graph_ranked" in out and "seed" in out and "re-ranking: scored" in out
    assert "lec02-main-p052" in out


def test_summarize_pages_handles_every_tool_shape():
    page = {"page_id": "lec02-main-p052", "citation": "Lecture 2 · p.52", "title": "LoRA", "distance": 0.1, "hops": 1}
    assert "result" in agent_module.summarize_pages(json.dumps({"results": [page]}))[0]
    lines = agent_module.summarize_pages(json.dumps({"seeds": [page], "expanded": [page]}))
    assert lines[0].startswith("seed") and "1 hops" in lines[1]
    assert agent_module.summarize_pages(json.dumps({"error": "boom"})) == ["error: boom"]


def test_cited_evidence_matches_page_or_translated_number():
    answer = "Compaction summarises history (Lecture 3 · translated PDF p.39); see also p. 40."
    assert compare.cited_evidence(answer, ["lec03-main-p039", "lec03-main-p040", "lec03-main-p013"]) == \
        ["lec03-main-p039", "lec03-main-p040"]
    assert compare.cited_evidence("translated PDF p.79", ["lec02-main-p047"]) == ["lec02-main-p047"]


def test_retrieval_only_report(question_like, tmp_path, monkeypatch):
    question_like("lec03-main-p039")
    out = tmp_path / "r.md"
    monkeypatch.setattr(sys, "argv", ["x", "--retrieval-only", "--questions", "memory", "--out", str(out)])
    compare.main()
    text = out.read_text(encoding="utf-8")
    assert "Graph + re-ranking (mine)" in text and "| memory |" in text
