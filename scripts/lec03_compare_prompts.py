"""Lecture 03 homework (Basic): change ONE instruction or docstring at a time and compare --trace.

Each variant differs from the course agent in exactly one place (INSTRUCTIONS in app/agent.py or one tool
docstring in app/tools.py). The script builds that variant in memory, so app/ is never edited, asks every
question, and records which tools were called (order, count, arguments), the number of LLM calls and the answer.

    uv run python scripts/lec03_compare_prompts.py                       # all variants, default questions
    uv run python scripts/lec03_compare_prompts.py --variants baseline multi_term_docstring
    uv run python scripts/lec03_compare_prompts.py --list                 # show what each variant changes

Writes lectures/03/basic_results.md. Tools that need approval (save_learning_log) are always denied here.
Runs are spaced by --sleep seconds because one agent question already makes several LLM calls.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `app` imports when run as a script

from pydantic_ai import DeferredToolRequests, DeferredToolResults, ToolDenied  # noqa: E402
from pydantic_ai.exceptions import ModelHTTPError  # noqa: E402
from pydantic_ai.messages import ToolCallPart  # noqa: E402

from app import tools  # noqa: E402
from app.agent import INSTRUCTIONS, build_agent, build_model  # noqa: E402
from app.config import MODEL  # noqa: E402

SEARCH_RULE = "- Always check the glossary with search_glossary before answering about terms or course-specific information.\n"
ENDING_RULE = "- End your answer by indicating the relevant session (Lecture NN).\n"
ONE_TERM = 'Put only one term to look up in query (for example, "LoRA").'

# name -> (what changed, agent keyword arguments). Each variant changes exactly one place.
VARIANTS = {
    "baseline": ("Course agent as is", {}),
    "no_search_rule": ("INSTRUCTIONS: deleted the line \"Always check the glossary with search_glossary …\"",
                       {"instructions": INSTRUCTIONS.replace(SEARCH_RULE, "")}),
    "multi_term_docstring": ("search_glossary docstring: \"Put only one term\" → \"Put several terms together\"",
                             {"docstrings": {"search_glossary": tools.search_glossary.__doc__.replace(
                                 ONE_TERM, 'Put several terms to look up together in query (for example, "LoRA QLoRA").')}}),
    "review_question_ending": ("INSTRUCTIONS: \"End your answer by indicating the relevant session\" → \"End with one review question\"",
                               {"instructions": INSTRUCTIONS.replace(ENDING_RULE, "- End your answer with one review question for the learner.\n")}),
}
DEFAULT_QUESTIONS = [
    "What is the difference between LoRA and QLoRA?",            # exercise step 3: two terms
    "What are the 3 homework levels in the AIE2026 course?",     # exercise step 2: course-specific
]


def deny_all(requests: DeferredToolRequests) -> DeferredToolResults:
    results = DeferredToolResults()
    for call in requests.approvals:
        results.approvals[call.tool_call_id] = ToolDenied("Denied automatically in the comparison script.")
    return results


def run_once(agent, question, model):
    result = agent.run_sync(question, model=model)
    while isinstance(result.output, DeferredToolRequests):
        result = agent.run_sync(message_history=result.all_messages(), deferred_tool_results=deny_all(result.output), model=model,
                                usage=result.usage)  # keep counting across the pause
    calls = [f"{p.tool_name}({p.args})" for m in result.all_messages() for p in m.parts if isinstance(p, ToolCallPart)]
    u = result.usage
    return {"calls": calls, "requests": u.requests, "tool_calls": u.tool_calls,
            "input_tokens": u.input_tokens, "output_tokens": u.output_tokens, "answer": str(result.output).strip()}


def to_markdown(rows, names):
    lines = ["# Lecture 03 Basic: one change at a time", "", f"Model: {MODEL}", "",
             "| variant | what changed |", "|---|---|"]
    lines += [f"| {n} | {VARIANTS[n][0]} |" for n in names]
    lines += ["", "| question | variant | tool calls (in order) | LLM calls (requests) | tool calls | tokens in / out |",
              "|---|---|---|---|---|---|"]
    for r in rows:
        if r.get("error"):
            lines.append(f"| {r['question']} | {r['variant']} | error: {r['error']} | - | - | - |")
        else:
            calls = "<br>".join(r["calls"]) or "(none)"
            lines.append(f"| {r['question']} | {r['variant']} | {calls} | {r['requests']} | {r['tool_calls']} | "
                         f"{r['input_tokens']} / {r['output_tokens']} |")
    lines += ["", "## Answers", ""]
    for r in rows:
        lines += [f"**{r['variant']} · {r['question']}**", "", (r.get("answer") or r.get("error", "")).replace("\n", "\n> ").join(["> ", ""]), ""]
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--variants", nargs="+", default=list(VARIANTS), choices=list(VARIANTS))
    p.add_argument("--questions", nargs="+", default=DEFAULT_QUESTIONS)
    p.add_argument("--sleep", type=float, default=10.0)
    p.add_argument("--out", default="lectures/03/basic_results.md")
    p.add_argument("--list", action="store_true", help="show the variants and exit (no API key needed)")
    args = p.parse_args()

    if args.list:
        for name, (what, _) in VARIANTS.items():
            print(f"{name:24} {what}")
        return

    model = build_model()
    rows, total, n = [], len(args.variants) * len(args.questions), 0
    for question in args.questions:
        for name in args.variants:
            n += 1
            print(f"[{n}/{total}] {name}: {question}")
            row = {"variant": name, "question": question}
            try:
                row |= run_once(build_agent(**VARIANTS[name][1]), question, model)
                print(f"    requests={row['requests']} tool calls: {', '.join(row['calls']) or '(none)'}")
            except ModelHTTPError as e:
                row["error"] = f"{e.status_code}"
                print(f"    error {e.status_code} (429 = rate limit: wait a minute and rerun this variant with --variants)")
            rows.append(row)
            if n < total:
                time.sleep(args.sleep)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_markdown(rows, args.variants), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
