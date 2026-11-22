# Lecture 05 Answers

<!--
Notes for filling in (delete this comment before submitting)
- Fill every 【 】 from your own Codespace runs. Exercise numbers come from the --trace lines [time], [usage] and [cost]
- Homework tables: paste from lectures/05/advanced_retrieval.md and lectures/05/advanced_results.md (written by scripts/lec05_compare.py)
-->

## Exercises

- Answering model (`[model]` shown during execution): `gemini-3.5-flash-lite`
- Comparison question: "In Lecture 2, what does LoRA freeze and what does it train? What does QLoRA add?" Evidence: Lecture 2 p.52 (LoRA freezes the original weights and trains a small low-rank "delta"; QLoRA also compresses the frozen base weights to 4 bit).
- Target materials (also record the difference in scope between full context and the other methods): full context passes all 9 documents (438 pages) of `lectures.json`; vector search, Tree and Graph cover only the main materials for Lectures 1–3 (214 pages). So full context had a wider scope, and its input was much larger for that reason too.

### Results by Method

| Method | Key points and correctness of the answer | Cited pages and evidence | Time (seconds) | Input/output tokens | Model responses | Estimated generation API cost (USD) |
|---|---|---|---|---|---|---|
| Full context | 【 】 | 【 】 | 【 】 | 【 】 | 【 】 | 【 】 |
| Vector search | 【 】 | 【 】 | 【 】 | 【 】 | 【 】 | 【 】 |
| Tree | 【 】 | 【 】 | 【 】 | 【 】 | 【 】 | 【 】 |
| Graph | 【 】 | 【 】 | 【 】 | 【 】 | 【 】 | 【 】 |

- Pages found by running search alone, and what their text confirmed: `uv run python -m app.retrieval "LoRA QLoRA difference"` returned 【the 5 pages, e.g. Lecture 2 p.52, p.51, …】. p.52's text states 【 】, which supports the answer; 【the other pages were related topics (PEFT overview, the exercise) but did not answer the question on their own】.
- Tool calls shown by `--trace` (names, arguments, counts, table-of-contents paths followed by Tree, etc.): Vector search: 【`search_materials({'query': '…'})` × N】. Tree: 【path, e.g. lecture list → Lecture 2 → "When and how to adapt the selected model" → p.52, N calls】. Graph: 【`search_graph({'query': '…'})` × N; seeds …, expanded …】.
- Examples where retrieved information was insufficient, or was retrieved but not used in the answer: 【e.g. Graph returned 10 pages, but the answer used only p.51–52; the other 8 pages added input tokens without being used】.
- Method you would adopt for this use case, your reasons, and limitations of the comparison conditions: 【e.g. Vector search: for a single-page question it found p.52 with the fewest tokens and lowest cost. Full context also answered, but used about 【 】× the input tokens. Limitation: one question, one run each, and full context covered a wider scope】.
- Observations and questions: 【 】

## Homework

- Level attempted: Advanced

- What you did (files, settings, or processing changed, or retrieval method designed): I designed **Graph + re-ranking** (`--graph-rerank`): the graph is used to *find* candidates, and similarity to the question decides which ones to *keep*.
  - **Problem with the current Graph.** `search_graph` starts from the top 3 vector hits and walks adjacent pages and shared terms for up to 2 hops. It then returns up to 10 pages ordered by hop count and term rarity, without checking whether each page relates to the question. Graph neighbours are often off-topic ("related ≠ contains the answer"), so they add input tokens, and a relevant page two hops away can lose its slot to an irrelevant one-hop neighbour.
  - **Method** (`search_graph_ranked` in `app/retrieval.py`):
    1. Embed the question once and take the 3 nearest pages as seeds, exactly as Graph does.
    2. Collect *every* page within 2 hops of any seed along `next_page` and `mentions` edges, keeping the shortest path to each.
    3. Score each candidate by cosine distance to the question, using the page embeddings already stored in `index.sqlite3`. This is one SQL query and needs no extra API call.
    4. Drop candidates farther than the weakest seed's distance + 0.05 (`GRAPH_RERANK_MARGIN`). Return the closest ones, so that seeds + expanded ≤ 10 pages.
  - **Data structure and storage:** no new data. It reuses `graph.json` (pages and terms as nodes; `next_page` and `mentions` edges) and the 768-dimensional page vectors in the SQLite index (sqlite-vec). The only new settings are `GRAPH_RERANK_POOL` and `GRAPH_RERANK_MARGIN` in `app/config.py`.
  - **Why this design:** the graph supplies *recall*, because it can reach pages that vector top-k misses but that share a term with a good match. Similarity supplies *precision*, because only candidates about as close to the question as the seeds survive. The graph also restricts the pool: from 3 seeds, 2 hops reach 84–99 of the 214 pages, so candidates are a connected neighbourhood, not the whole corpus. Reusing stored vectors keeps the cost at one embedding call per search, the same as Graph.
  - I first capped the candidate pool at 60 pages, but every search reached more than 60. The cap was cutting candidates by page ID order rather than relevance, so I raised it to score every reachable page.
  - **Other files:**
    - `app/tools.py`: a new tool, `search_graph_ranked`.
    - `app/agent.py`: the `--graph-rerank` mode with `GRAPH_RERANK_INSTRUCTIONS`, the same rules as Graph. `--trace` now lists every page a search tool returned, with its role, citation, distance and hops.
    - `scripts/lec05_compare.py`: runs the comparison.
    - `tests/test_lec05_advanced.py`: 7 tests with no API key needed (28 passed in total).

- Comparison question and conditions held fixed (model, target materials, etc.): `gemini-3.5-flash-lite`, the main materials for Lectures 1–3 (214 pages), the same index and graph, and the same answering rules. Only the retrieval tool differs. Four questions, with evidence pages identified in `lectures.json` before running anything:

| Key | Question | Type | Evidence pages |
|---|---|---|---|
| memory | In Lecture 3, how does compaction differ from memory that carries across sessions? Do all daily notes become long-term memory? | multi-page | Lecture 3 p.13, 39, 40 |
| ft_vs_rag | According to Lecture 2, why is RAG often preferred over fine-tuning for adding knowledge, and what is fine-tuning good at instead? | spans sections | Lecture 2 p.46, 47, 53 |
| lora | In Lecture 2, what does LoRA freeze and what does it train? What does QLoRA add? | single page (control) | Lecture 2 p.52 |
| not_in_materials | What are the measured average response time and accuracy of our RAG system? | not in materials (control) | none: should say it cannot verify |

- Results (answers and evidence before/after, `--trace` output, time, token counts, estimated generation API cost, etc.):

  **Offline check of retrieval only.** I used the stored vector of p.39 (the memory example page) in place of a question embedding, which needs no API:

| Method | Pages returned | Memory evidence (p.13, 39, 40) found |
|---|---|---|
| Basic RAG (top 5) | p.39, 40, 38, 65, 41 | 2/3: p.13 missing |
| Graph (course) | seeds p.39, 40, 38 + expanded p.41, 37, 42, 36, 19, 58, 51 (10 pages) | 2/3: p.13 missing; p.58 (RSI) and p.51 (trust boundaries) are off-topic |
| Graph + re-ranking | seeds p.39, 40, 38 + expanded p.65, 41, 13, 37 (7 pages) | **3/3**: p.13 reached in 2 hops via a shared term; 95 of 99 candidates dropped |

  **Real questions, retrieval only** (`uv run python scripts/lec05_compare.py --retrieval-only`):

【Paste the table from lectures/05/advanced_retrieval.md】

  **Real questions, full agent runs** (`uv run python scripts/lec05_compare.py`):

【Paste the first two tables from lectures/05/advanced_results.md】

- Examples of improvements and remaining failures or limitations:
  - Improvement (offline check): for the memory question, re-ranking found all three evidence pages where both other methods found two, and returned 7 pages instead of Graph's 10, removing the off-topic ones. It also surfaced p.65 (the appendix on compaction), which is relevant but outside the fixed evidence set. 【Confirm or correct with the real-question results】
  - 【Real-question improvement or failure, e.g. "ft_vs_rag: all methods found p.46 and p.47; only … found p.53"】
  - Limitation: with 2 hops through shared terms, almost half the corpus is reachable, so for broad questions re-ranking behaves much like a vector top-10 restricted to that half. Its advantage shows when the evidence sits in a different part of the materials but shares a specific term (p.13 and p.39 are 26 pages apart and linked through "memory"), and the threshold cuts the rest.
  - Limitation: the margin of 0.05 was set by inspecting three stand-in questions, not tuned. A larger margin keeps more pages (more recall, more tokens); a smaller one may drop needed evidence.
  - Limitation: it is still similarity, not proof. A close page can still be about a neighbouring topic, so the answer must check the text, which the instructions require.
- Observations and questions:
  - Would I adopt it? 【e.g. "Yes for multi-page questions such as the memory one, where it found more evidence with fewer pages, at the same embedding cost as Graph. For single-page questions, basic RAG is enough and cheaper."】 In my integration work, specifications are cross-referenced (an API page mentions error codes defined elsewhere), which is exactly the "shared term in another section" case this targets.
  - Question: could the graph edges themselves be weighted by similarity at index time, so that candidate selection does not need a threshold chosen by hand?
