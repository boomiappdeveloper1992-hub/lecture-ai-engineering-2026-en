"""Lecture 03: tools for the agent.

Function docstrings and type hints here become the "tool descriptions" presented to the model.
Rewriting descriptions changes whether the model uses a tool and which arguments it supplies.
"""

import json
import random
import re
from datetime import datetime
from functools import cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
# Lecture 03 homework (Implementation): where save_learning_log writes its records
LOG_DIR = Path(__file__).resolve().parent.parent / "learning_log"
MAX_RESULTS = 3


@cache
def load_glossary() -> list[dict]:
    with open(DATA_DIR / "glossary.json", encoding="utf-8") as f:
        return json.load(f)["terms"]


def _normalize(text: str) -> str:
    return text.casefold().replace(" ", "").replace("　", "")


def _names(entry: dict) -> list[str]:
    return [_normalize(entry["term"]), _normalize(entry["id"])] + [
        _normalize(a) for a in entry["aliases"]
    ]


def search_glossary(query: str) -> str:
    """Search the course glossary and return definitions and the sessions that cover the terms.

    Use before answering about AI engineering terms or words specific to this course (AIE2026).
    Put only one term to look up in query (for example, "LoRA").
    """
    q = _normalize(query)
    if not q:
        return "The search query is empty. Specify one term to look up."
    glossary = load_glossary()

    exact = [e for e in glossary if q in _names(e)]
    # Exclude short names so aliases such as "r" do not match everything
    partial = [
        e for e in glossary
        if e not in exact and any(q in n or (len(n) >= 3 and n in q) for n in _names(e))
    ]
    in_definition = [
        e for e in glossary
        if e not in exact and e not in partial and q in _normalize(e["definition"])
    ]
    hits = (exact + partial + in_definition)[:MAX_RESULTS]

    if not hits:
        return f"The term '{query}' was not found in the glossary."
    return json.dumps(
        [
            {
                "term": e["term"],
                "lecture": e["lecture"],
                "definition": e["definition"],
                "related": e["related"],
            }
            for e in hits
        ],
        ensure_ascii=False,
    )


def get_lecture_summary(lecture: int) -> str:
    """Return key points from the specified session (an integer starting at 1).

    Use when asked about session content or relationships, such as "What will we learn in Lecture 03?".
    """
    path = DATA_DIR / "lectures" / f"{lecture:02d}.md"
    if not path.exists():
        available = sorted(p.stem for p in (DATA_DIR / "lectures").glob("*.md"))
        return f"Key points for Lecture {lecture:02d} are not available yet. Available sessions: {', '.join(available)}"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------- Lecture 03 exercise
def make_quiz(lecture: int) -> str:
    """Pick one term covered in the given session and return a review question with its answer.

    Use when the learner asks for a review question or a quiz about a session,
    such as "Give me one review question from Lecture 02". lecture is the session number (an integer starting at 1).
    Ask the learner the question first and reveal the answer only after they have tried.
    """
    terms = [e for e in load_glossary() if e["lecture"] == lecture]
    if not terms:
        available = sorted({e["lecture"] for e in load_glossary()})
        return (f"There are no glossary terms for Lecture {lecture:02d}. "
                f"Sessions with terms: {', '.join(f'{n:02d}' for n in available)}")
    entry = random.choice(terms)
    return json.dumps(
        {"lecture": lecture, "question": f"What does \u201c{entry['term']}\u201d mean?", "answer": entry["definition"]},
        ensure_ascii=False,
    )


# ---------------------------------------------------------------- Lecture 03 homework (Implementation)
def _slug(text: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z]+", "-", text).strip("-").lower()
    return slug[:40] or "note"


def save_learning_log(title: str, content: str) -> str:
    """Save a learning record (what the learner studied, understood or wants to review) as a Markdown file in learning_log/.

    Use only when the learner explicitly asks to save, record or log something, such as
    "Save what I learned about LoRA today". title is a short heading; content is the text of the record.
    Saving writes a file, so the learner is asked to approve each save before it runs.
    """
    if not title.strip() or not content.strip():
        return "Nothing was saved: both title and content are required."
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    path = LOG_DIR / f"{now:%Y-%m-%d_%H%M%S}_{_slug(title)}.md"
    n = 2
    while path.exists():  # never overwrite an existing record
        path = LOG_DIR / f"{now:%Y-%m-%d_%H%M%S}_{_slug(title)}-{n}.md"
        n += 1
    path.write_text(f"# {title.strip()}\n\n_Saved: {now:%Y-%m-%d %H:%M}_\n\n{content.strip()}\n", encoding="utf-8")
    return f"Saved the learning record to {path.relative_to(LOG_DIR.parent)}"
