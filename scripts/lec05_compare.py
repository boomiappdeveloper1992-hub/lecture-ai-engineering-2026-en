"""Lecture 05 homework (Advanced): compare basic RAG, Graph and Graph + re-ranking on the same questions.

Each question has evidence pages fixed in advance. For each method the script records which pages were
retrieved, how many of the evidence pages they include (recall), and, in a full run, the answer, the
evidence pages it cites, time, tokens, model responses and estimated generation API cost.

    uv run python scripts/lec05_compare.py --retrieval-only   # search only: 1 embedding call per method, no LLM
    uv run python scripts/lec05_compare.py                     # full agent runs (about 12 runs, ~5 minutes)
    uv run python scripts/lec05_compare.py --methods rag graph_rerank --questions memory

Writes lectures/05/advanced_retrieval.md or lectures/05/advanced_results.md.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `app` imports when run as a script

from pydantic_ai.exceptions import ModelHTTPError  # noqa: E402
from pydantic_ai.messages import ToolReturnPart  # noqa: E402

from app import retrieval, tools  # noqa: E402
from app.agent import GRAPH_INSTRUCTIONS, GRAPH_RERANK_INSTRUCTIONS, INSTRUCTIONS, agent, build_model  # noqa: E402
from app.config import MODEL  # noqa: E402

# Evidence pages were checked by reading lectures.json before running anything.
QUESTIONS = {
    "memory": {
        "type": "multi-page",
        "text": "In Lecture 3, how does compaction differ from memory that carries across sessions? "
                "Do all daily notes become long-term memory?",
        "evidence": ["lec03-main-p013", "lec03-main-p039", "lec03-main-p040"],
    },
    "ft_vs_rag": {
        "type": "spans sections",
        "text": "According to Lecture 2, why is RAG often preferred over fine-tuning for adding knowledge, "
                "and what is fine-tuning good at instead?",
        "evidence": ["lec02-main-p046", "lec02-main-p047", "lec02-main-p053"],
    },
    "lora": {
        "type": "single page (control)",
        "text": "In Lecture 2, what does LoRA freeze and what does it train? What does QLoRA add?",
        "evidence": ["lec02-main-p052"],
    },
    "not_in_materials": {
        "type": "not in materials (control)",
        "text": "What are the measured average response time and accuracy of our RAG system?",
        "evidence": [],
    },
}

METHODS = {
    "rag": ("Basic RAG (vector search)", INSTRUCTIONS, tools.search_materials, retrieval.search),
    "graph": ("Graph (course version)", GRAPH_INSTRUCTIONS, tools.search_graph, retrieval.search_graph),
    "graph_rerank": ("Graph + re-ranking (mine)", GRAPH_RERANK_INSTRUCTIONS, tools.search_graph_ranked,
                     retrieval.search_graph_ranked),
}


def pages_of(result) -> list[dict]:
    """Pages in a search result, whatever the method's output shape."""
    if isinstance(result, list):
        return result
    if "results" in result:
        return result["results"]
    return result.get("seeds", []) + result.get("expanded", [])


def cited_evidence(answer: str, evidence: list[str]) -> list[str]:
    """Evidence pages whose page number (or translated-PDF number) appears as "p.N" in the answer."""
    labels = {p["page_id"]: p for p in retrieval.load_pages()}
    found = []
    for pid in evidence:
        page = labels[pid]
        numbers = {str(page["page"])} | set(re.findall(r"p\.(\d+)", page.get("citation", "")))
        if any(re.search(rf"p\.\s?{n}\b", answer) for n in numbers):
            found.append(pid)
    return found


def short(pid: str) -> str:
    return f"L{int(pid[3:5])} p.{int(pid[-3:])}"


def recall(retrieved: list[str], evidence: list[str]) -> str:
    if not evidence:
        return "n/a"
    return f"{sum(pid in retrieved for pid in evidence)}/{len(evidence)}"


def run_retrieval(qkeys, mkeys):
    rows = []
    for q in qkeys:
        for m in mkeys:
            pages = pages_of(METHODS[m][3](QUESTIONS[q]["text"]))
            ids = [p["page_id"] for p in pages]
            rows.append({"question": q, "method": m, "retrieved": ids, "recall": recall(ids, QUESTIONS[q]["evidence"]),
                         "chars": sum(len(p["content"]) for p in pages)})
            print(f"{q:17} {m:13} recall {rows[-1]['recall']:4} pages {len(ids):2} chars {rows[-1]['chars']:6}  {[short(i) for i in ids]}")
    return rows


def run_agent(qkeys, mkeys, sleep):
    rows, total, n = [], len(qkeys) * len(mkeys), 0
    model = build_model()
    for q in qkeys:
        for m in mkeys:
            n += 1
            name, instructions, tool, _ = METHODS[m]
            print(f"[{n}/{total}] {m}: {q}")
            row = {"question": q, "method": m}
            started = time.perf_counter()
            try:
                with agent.override(instructions=instructions, tools=[tool]):
                    result = agent.run_sync(QUESTIONS[q]["text"], model=model)
            except ModelHTTPError as e:
                row["error"] = f"HTTP {e.status_code}"
                print(f"    {row['error']} (429 = rate limit: wait a minute, rerun with --methods/--questions)")
            else:
                seconds = time.perf_counter() - started
                retrieved, calls = [], 0
                for message in result.all_messages():
                    for part in message.parts:
                        if isinstance(part, ToolReturnPart):
                            calls += 1
                            try:
                                retrieved += [p["page_id"] for p in pages_of(json.loads(part.content))]
                            except (TypeError, ValueError, KeyError):
                                pass
                retrieved = list(dict.fromkeys(retrieved))
                usage, answer = result.usage, str(result.output).strip()
                row |= {"answer": answer, "retrieved": retrieved, "tool_calls": calls,
                        "recall": recall(retrieved, QUESTIONS[q]["evidence"]),
                        "cited": cited_evidence(answer, QUESTIONS[q]["evidence"]),
                        "seconds": round(seconds, 2), "input": usage.input_tokens, "output": usage.output_tokens,
                        "requests": usage.requests, "cost": float(usage.cost) if usage.cost is not None else None}
                print(f"    {seconds:.1f}s in {usage.input_tokens} out {usage.output_tokens} retrieved-evidence {row['recall']} "
                      f"cited {len(row['cited'])}/{len(QUESTIONS[q]['evidence'])}")
            rows.append(row)
            if n < total:
                time.sleep(sleep)
    return rows


def to_markdown(rows, full: bool):
    lines = [f"# Lecture 05 Advanced: basic RAG vs Graph vs Graph + re-ranking", "", f"Model: {MODEL}", "",
             "| Question | Type | Evidence pages |", "|---|---|---|"]
    for key in dict.fromkeys(r["question"] for r in rows):
        q = QUESTIONS[key]
        lines.append(f"| {key}: {q['text']} | {q['type']} | {', '.join(short(p) for p in q['evidence']) or 'none'} |")
    lines.append("")
    if full:
        lines += ["| Question | Method | Evidence retrieved | Evidence cited | Pages retrieved | Tool calls | Time (s) | "
                  "Input / output tokens | Model responses | Est. cost (USD) |", "|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            if r.get("error"):
                lines.append(f"| {r['question']} | {METHODS[r['method']][0]} | {r['error']} | | | | | | | |")
                continue
            ev = QUESTIONS[r["question"]]["evidence"]
            cost = f"{r['cost']:.6f}" if r["cost"] is not None else "n/a"
            lines.append(f"| {r['question']} | {METHODS[r['method']][0]} | {r['recall']} | "
                         f"{len(r['cited'])}/{len(ev) if ev else 'n/a'} | {len(r['retrieved'])} | {r['tool_calls']} | "
                         f"{r['seconds']} | {r['input']:,} / {r['output']:,} | {r['requests']} | {cost} |")
        lines += ["", "## Pages retrieved and answers", ""]
        for r in rows:
            if r.get("error"):
                continue
            lines += [f"**{r['question']} · {METHODS[r['method']][0]}**", "",
                      f"Retrieved: {', '.join(short(p) for p in r['retrieved'])}", "",
                      "> " + r["answer"].replace("\n", "\n> "), ""]
    else:
        lines += ["| Question | Method | Evidence retrieved | Pages | Characters of page text | Pages (in order) |",
                  "|---|---|---|---|---|---|"]
        for r in rows:
            lines.append(f"| {r['question']} | {METHODS[r['method']][0]} | {r['recall']} | {len(r['retrieved'])} | "
                         f"{r['chars']:,} | {', '.join(short(p) for p in r['retrieved'])} |")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--questions", nargs="+", default=list(QUESTIONS), choices=list(QUESTIONS))
    p.add_argument("--methods", nargs="+", default=list(METHODS), choices=list(METHODS))
    p.add_argument("--retrieval-only", action="store_true", help="search only, no LLM (embedding calls only)")
    p.add_argument("--sleep", type=float, default=15.0, help="seconds between agent runs")
    p.add_argument("--out", default=None)
    args = p.parse_args()
    if args.retrieval_only:
        rows = run_retrieval(args.questions, args.methods)
        out = Path(args.out or "lectures/05/advanced_retrieval.md")
    else:
        rows = run_agent(args.questions, args.methods, args.sleep)
        out = Path(args.out or "lectures/05/advanced_results.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_markdown(rows, not args.retrieval_only), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
