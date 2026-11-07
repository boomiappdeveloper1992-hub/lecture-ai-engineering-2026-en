"""Lecture 01 homework (Basic / Advanced): ask the same questions several times per setting and compare.

Each setting (model × temperature) asks every question --runs times. For every call it records
the answer, response time and token counts, then writes:
    <out>.csv  every call (answers in full)
    <out>.md   a summary table per setting and question, plus totals for the rate-limit discussion

Basic (vary temperature, one model):
    uv run python scripts/lec01_experiments.py --models gemini-3.5-flash-lite --temperatures 0 1 2
Basic / Advanced (vary the model):
    uv run python scripts/lec01_experiments.py --models gemini-3.5-flash-lite gemini-3.6-flash

Calls are spaced by --sleep seconds to stay under the free tier's requests-per-minute limit.
A 429 (rate limit) is retried once after --retry-wait seconds; other errors are recorded and skipped.
"""

import argparse
import csv
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `app` imports when run as a script

from google import genai  # noqa: E402
from google.genai import errors  # noqa: E402

from app.ask import DEFAULT_QUESTION, make_config  # noqa: E402
from app.config import get_api_key  # noqa: E402

DEFAULT_QUESTIONS = [
    "What is LoRA?",                                        # general term: the model should know it
    DEFAULT_QUESTION,                                       # course-specific: the model cannot know it
    "What is a lecNN-start tag in the AIE2026 course?",     # course-specific
]
FIELDS = ["model", "temperature", "question", "run", "ok", "error", "seconds",
          "input_tokens", "output_tokens", "thinking_tokens", "total_tokens", "answer"]


def call_once(client, model, question, temperature, retry_wait):
    """One timed call. Returns a result row (without model/temperature/question/run)."""
    for attempt in (1, 2):
        t0 = time.perf_counter()
        try:
            r = client.models.generate_content(model=model, contents=question, config=make_config(temperature))
        except errors.APIError as e:
            if e.code == 429 and attempt == 1:
                print(f"    429 rate limit: waiting {retry_wait}s and retrying once")
                time.sleep(retry_wait)
                continue
            return {"ok": False, "error": f"{e.code}: {(e.message or '')[:120]}", "seconds": round(time.perf_counter() - t0, 2)}
        u = r.usage_metadata
        def n(v): return v or 0
        return {"ok": True, "error": "", "seconds": round(time.perf_counter() - t0, 2),
                "input_tokens": n(u and u.prompt_token_count), "output_tokens": n(u and u.candidates_token_count),
                "thinking_tokens": n(u and u.thoughts_token_count), "total_tokens": n(u and u.total_token_count),
                "answer": (r.text or "").strip()}


def summarize(rows):
    """Group by (model, temperature, question) and compute the numbers the homework asks for."""
    groups = {}
    for r in rows:
        groups.setdefault((r["model"], r["temperature"], r["question"]), []).append(r)
    out = []
    for (model, temp, q), rs in groups.items():
        ok = [r for r in rs if r["ok"]]
        def stat(key, fn): return round(fn([r[key] for r in ok]), 2) if ok else None
        out.append({"model": model, "temperature": temp, "question": q, "calls": len(rs), "ok": len(ok),
                    "sec_mean": stat("seconds", statistics.mean), "sec_min": stat("seconds", min), "sec_max": stat("seconds", max),
                    "in_mean": stat("input_tokens", statistics.mean), "out_mean": stat("output_tokens", statistics.mean),
                    "think_mean": stat("thinking_tokens", statistics.mean), "total_mean": stat("total_tokens", statistics.mean),
                    "distinct_answers": len({r["answer"] for r in ok})})
    return out


def to_markdown(rows, summary, args):
    def cell(v): return "-" if v is None else str(v)
    temp = lambda t: "default" if t is None else t  # noqa: E731
    lines = ["# Lecture 01 experiment results", "",
             f"Settings: models = {', '.join(args.models)}; temperatures = {', '.join(str(temp(t)) for t in args.temperatures)}; "
             f"{args.runs} runs per question; {args.sleep}s between calls.", "",
             "| model | temperature | question | ok/calls | time mean (min–max) s | input tok | output tok | thinking tok | total tok | distinct answers |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for s in summary:
        lines.append(f"| {s['model']} | {temp(s['temperature'])} | {s['question']} | {s['ok']}/{s['calls']} | "
                     f"{cell(s['sec_mean'])} ({cell(s['sec_min'])}–{cell(s['sec_max'])}) | {cell(s['in_mean'])} | {cell(s['out_mean'])} | "
                     f"{cell(s['think_mean'])} | {cell(s['total_mean'])} | {s['distinct_answers']} of {s['ok']} |")
    ok = [r for r in rows if r["ok"]]
    elapsed = getattr(args, "elapsed", None)
    lines += ["", "## Totals (for the rate-limit discussion)", "",
              f"- Calls: {len(rows)} ({len(ok)} succeeded, {len(rows) - len(ok)} failed)",
              f"- Tokens used: {sum(r['total_tokens'] for r in ok)} total "
              f"({sum(r['thinking_tokens'] for r in ok)} of them thinking tokens)"]
    if elapsed:
        lines.append(f"- Wall time: {elapsed:.0f} s → {len(rows) / (elapsed / 60):.1f} requests per minute on average")
    errs = sorted({r['error'] for r in rows if not r['ok']})
    if errs:
        lines.append(f"- Errors seen: {'; '.join(errs)}")
    lines += ["", "## Answers (first 150 characters of each run)", ""]
    for s in summary:
        lines.append(f"**{s['model']} · temperature {temp(s['temperature'])} · {s['question']}**")
        for r in rows:
            if (r["model"], r["temperature"], r["question"]) == (s["model"], s["temperature"], s["question"]):
                text = (r["answer"] or r["error"]).replace("\n", " ")
                lines.append(f"- run {r['run']}: {text[:150]}{'…' if len(text) > 150 else ''}")
        lines.append("")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--models", nargs="+", default=["gemini-3.5-flash-lite", "gemini-3.6-flash"])
    p.add_argument("--temperatures", nargs="+", type=float, default=[None],
                   help="e.g. 0 1 2 (Gemini accepts 0.0–2.0). Default: the model's own default")
    p.add_argument("--questions", nargs="+", default=DEFAULT_QUESTIONS)
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--sleep", type=float, default=5.0, help="seconds between calls (5 s ≈ 12 requests per minute)")
    p.add_argument("--retry-wait", type=float, default=60.0)
    p.add_argument("--out", default="lectures/01/results", help="output path without extension")
    args = p.parse_args()

    client = genai.Client(api_key=get_api_key())
    total = len(args.models) * len(args.temperatures) * len(args.questions) * args.runs
    print(f"{total} calls, about {total * args.sleep / 60:.1f} min at {args.sleep}s spacing")
    rows, n, t_start = [], 0, time.perf_counter()
    for model in args.models:
        for temp in args.temperatures:
            for q in args.questions:
                for run in range(1, args.runs + 1):
                    n += 1
                    print(f"[{n}/{total}] {model} t={'default' if temp is None else temp} run {run}: {q}")
                    res = call_once(client, model, q, temp, args.retry_wait)
                    row = {k: "" for k in FIELDS} | {"input_tokens": 0, "output_tokens": 0, "thinking_tokens": 0, "total_tokens": 0}
                    row |= {"model": model, "temperature": temp, "question": q, "run": run} | res
                    rows.append(row)
                    print(f"    {'ok' if row['ok'] else 'ERROR ' + row['error']} | {row['seconds']} s | "
                          f"in {row['input_tokens']} out {row['output_tokens']} think {row['thinking_tokens']}")
                    if n < total:
                        time.sleep(args.sleep)
    args.elapsed = time.perf_counter() - t_start

    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    with open(out.with_suffix(".csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    md = to_markdown(rows, summarize(rows), args)
    out.with_suffix(".md").write_text(md, encoding="utf-8")
    print(f"\nWrote {out.with_suffix('.csv')} and {out.with_suffix('.md')}\n")
    print(md.split("## Answers")[0])


if __name__ == "__main__":
    main()
