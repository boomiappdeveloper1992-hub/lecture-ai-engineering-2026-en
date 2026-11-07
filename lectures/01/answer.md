# Lecture 01 Answers

## Exercises

- Model's answer to the course-specific question (the 3 homework levels; a summary is fine): `gemini-3.5-flash-lite` answered confidently with three invented tiers: "Level 1: Core / Fundamentals", "Level 2: Intermediate / Application" and "Level 3: Advanced / Research & Challenge". It described them as levels for different learning paces, with Level 3 meant to "push top-performing students". It opened with "Based on the structure typically used in the AIE2026 course", as if it knew the course.
- What you noticed when comparing it with the correct meaning in the glossary: The glossary (`homework-levels`) says the levels are Basic (review lecture content), Implementation (write your own code) and Advanced (research and experimentation), that completing any one level finishes the homework, and that homework is not graded as a rule. The model got only the general idea of three increasing levels, and "Advanced / Research" roughly right. Its names and descriptions were invented, and it missed the two most important facts: one level is enough, and there is no grading. Instead it implied a ranking of students. It gave no sign of being unsure, even though it has never seen this course's materials. Asked the same question three more times (homework below), it gave a different answer each time. A bare LLM fills the gap with a plausible, generic answer, which is why Lecture 03 gives an agent a glossary search tool.
- Token counts you displayed (input / output): with the default model `gemini-3.5-flash-lite`, "What is LoRA?" used input 6 / output 697–868 tokens (mean 759) over 3 runs, and the 3-homework-levels question used input 18 / output 47–208 (mean 106). Flash-lite used no thinking tokens. I read them from `response.usage_metadata` (`prompt_token_count` for input, `candidates_token_count` for output, `thoughts_token_count` for reasoning that is counted but not shown) and print them with `format_usage()` in `app/ask.py`. The input is fixed by the question text and is tiny; almost all tokens are output, so the cost of a call depends on how much the model writes.

## Homework

- Level attempted: Advanced
- What you did: `scripts/lec01_experiments.py` asks 3 questions ("What is LoRA?", the 3-homework-levels question and "What is a lecNN-start tag in the AIE2026 course?") 3 times each on two models, `gemini-3.5-flash-lite` and `gemini-3.6-flash`: 18 calls in total, all at the default temperature. For every call it measures the response time (`time.perf_counter`) and records input, output, thinking and total tokens from `usage_metadata`. Calls are spaced 5 seconds apart, and a 429 is retried once after 60 seconds. Every call goes to `lectures/01/results_models.csv`, and a summary to `lectures/01/results_models.md`. Run: `uv run python scripts/lec01_experiments.py --models gemini-3.5-flash-lite gemini-3.6-flash --out lectures/01/results_models`. Tests for the new code run without an API key (`uv run pytest -q`: 22 passed).
- Results (means over 3 runs per row):

| model | question | time mean (min–max) s | input tok | output tok | thinking tok | total tok | distinct answers |
|---|---|---|---|---|---|---|---|
| gemini-3.5-flash-lite | What is LoRA? | 3.14 (2.95–3.46) | 6 | 759 | 0 | 765 | 3 of 3 |
| gemini-3.5-flash-lite | 3 homework levels (course-specific) | 1.09 (0.69–1.68) | 18 | 106 | 0 | 124 | 3 of 3 |
| gemini-3.5-flash-lite | lecNN-start tag (course-specific) | 2.16 (1.86–2.33) | 19 | 406 | 0 | 425 | 3 of 3 |
| gemini-3.6-flash | What is LoRA? | 13.39 (12.97–14.12) | 6 | 877 | 1,076 | 1,959 | 3 of 3 |
| gemini-3.6-flash | 3 homework levels (course-specific) | 10.02 (8.65–11.95) | 18 | 363 | 946 | 1,327 | 3 of 3 |
| gemini-3.6-flash | lecNN-start tag (course-specific) | 9.31 (8.90–10.04) | 19 | 487 | 815 | 1,321 | 3 of 3 |

| Totals | gemini-3.5-flash-lite | gemini-3.6-flash | Both |
|---|---|---|---|
| Calls (all succeeded) | 9 | 9 | 18 |
| Mean time per call | 2.1 s | 10.9 s | — |
| Tokens | 3,940 | 13,820 (8,511 thinking, 62%) | 17,760 |
| Tokens per call | 438 | 1,536 | — |

Wall time 202 s for 18 calls (117 s waiting for the API + 85 s of deliberate spacing) = 5.3 requests per minute and about 5,300 tokens per minute on average. No 429 errors.

(aie2026-exercises) @boomiappdeveloper1992-hub ➜ /workspaces/lecture-ai-engineering-2026-en (lec01) $  uv run pytest -q
......................                                                                                         [100%]
================================================== warnings summary ==================================================
.venv/lib/python3.14/site-packages/google/genai/types.py:42
  /workspaces/lecture-ai-engineering-2026-en/.venv/lib/python3.14/site-packages/google/genai/types.py:42: DeprecationWarning: '_UnionGenericAlias' is deprecated and slated for removal in Python 3.17
    VersionedUnionType = Union[builtin_types.UnionType, _UnionGenericAlias]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
22 passed, 1 warning in 5.39s
(aie2026-exercises) @boomiappdeveloper1992-hub ➜ /workspaces/lecture-ai-engineering-2026-en (lec01) $ uv run python scripts/lec01_experiments.py --models gemini-3.5-flash-lite gemini-3.6-flash --out lectures/01/results_models
18 calls, about 1.5 min at 5.0s spacing
[1/18] gemini-3.5-flash-lite t=default run 1: What is LoRA?
    ok | 2.95 s | in 6 out 697 think 0
[2/18] gemini-3.5-flash-lite t=default run 2: What is LoRA?
    ok | 3.0 s | in 6 out 712 think 0
[3/18] gemini-3.5-flash-lite t=default run 3: What is LoRA?
    ok | 3.46 s | in 6 out 868 think 0
[4/18] gemini-3.5-flash-lite t=default run 1: What are the 3 homework levels in the AIE2026 course?
    ok | 0.91 s | in 18 out 62 think 0
[5/18] gemini-3.5-flash-lite t=default run 2: What are the 3 homework levels in the AIE2026 course?
    ok | 0.69 s | in 18 out 47 think 0
[6/18] gemini-3.5-flash-lite t=default run 3: What are the 3 homework levels in the AIE2026 course?
    ok | 1.68 s | in 18 out 208 think 0
[7/18] gemini-3.5-flash-lite t=default run 1: What is a lecNN-start tag in the AIE2026 course?
    ok | 1.86 s | in 19 out 398 think 0
[8/18] gemini-3.5-flash-lite t=default run 2: What is a lecNN-start tag in the AIE2026 course?
    ok | 2.33 s | in 19 out 455 think 0
[9/18] gemini-3.5-flash-lite t=default run 3: What is a lecNN-start tag in the AIE2026 course?
    ok | 2.3 s | in 19 out 364 think 0
[10/18] gemini-3.6-flash t=default run 1: What is LoRA?
    ok | 12.97 s | in 6 out 762 think 925
[11/18] gemini-3.6-flash t=default run 2: What is LoRA?
    ok | 14.12 s | in 6 out 954 think 1129
[12/18] gemini-3.6-flash t=default run 3: What is LoRA?
    ok | 13.09 s | in 6 out 915 think 1173
[13/18] gemini-3.6-flash t=default run 1: What are the 3 homework levels in the AIE2026 course?
    ok | 8.65 s | in 18 out 422 think 615
[14/18] gemini-3.6-flash t=default run 2: What are the 3 homework levels in the AIE2026 course?
    ok | 9.45 s | in 18 out 368 think 1074
[15/18] gemini-3.6-flash t=default run 3: What are the 3 homework levels in the AIE2026 course?
    ok | 11.95 s | in 18 out 299 think 1150
[16/18] gemini-3.6-flash t=default run 1: What is a lecNN-start tag in the AIE2026 course?
    ok | 10.04 s | in 19 out 463 think 819
[17/18] gemini-3.6-flash t=default run 2: What is a lecNN-start tag in the AIE2026 course?
    ok | 9.0 s | in 19 out 486 think 785
[18/18] gemini-3.6-flash t=default run 3: What is a lecNN-start tag in the AIE2026 course?
    ok | 8.9 s | in 19 out 511 think 841

Wrote lectures/01/results_models.csv and lectures/01/results_models.md

# Lecture 01 experiment results

Settings: models = gemini-3.5-flash-lite, gemini-3.6-flash; temperatures = default; 3 runs per question; 5.0s between calls.

| model | temperature | question | ok/calls | time mean (min–max) s | input tok | output tok | thinking tok | total tok | distinct answers |
|---|---|---|---|---|---|---|---|---|---|
| gemini-3.5-flash-lite | default | What is LoRA? | 3/3 | 3.14 (2.95–3.46) | 6 | 759 | 0 | 765 | 3 of 3 |
| gemini-3.5-flash-lite | default | What are the 3 homework levels in the AIE2026 course? | 3/3 | 1.09 (0.69–1.68) | 18 | 105.67 | 0 | 123.67 | 3 of 3 |
| gemini-3.5-flash-lite | default | What is a lecNN-start tag in the AIE2026 course? | 3/3 | 2.16 (1.86–2.33) | 19 | 405.67 | 0 | 424.67 | 3 of 3 |
| gemini-3.6-flash | default | What is LoRA? | 3/3 | 13.39 (12.97–14.12) | 6 | 877 | 1075.67 | 1958.67 | 3 of 3 |
| gemini-3.6-flash | default | What are the 3 homework levels in the AIE2026 course? | 3/3 | 10.02 (8.65–11.95) | 18 | 363 | 946.33 | 1327.33 | 3 of 3 |
| gemini-3.6-flash | default | What is a lecNN-start tag in the AIE2026 course? | 3/3 | 9.31 (8.9–10.04) | 19 | 486.67 | 815 | 1320.67 | 3 of 3 |

## Totals (for the rate-limit discussion)

- Calls: 18 (18 succeeded, 0 failed)
- Tokens used: 17760 total (8511 of them thinking tokens)
- Wall time: 202 s → 5.3 requests per minute on average

- Observations and questions:
  - Response time follows the number of tokens generated, not the input. Input was only 6–19 tokens everywhere. Flash-lite took 1.1 s for the short homework-levels answers (106 tokens) but 3.1 s for "What is LoRA?" (759 tokens). 3.6 Flash was about 5× slower on average (10.9 s vs 2.1 s), because before answering it generated 815–1,076 thinking tokens per call that never appear in the answer.
  - Thinking tokens dominate the cost of 3.6 Flash. They were 62% of its tokens, and it used 3.5× as many tokens as flash-lite for the same 9 questions (13,820 vs 3,940). Thinking is counted and billed like output, so a reasoning model spends far more of the token budget per question even when its answers are similar in length.
  - Same question, different answer: every row has 3 distinct answers out of 3, so at the default temperature no two runs were identical. On the course questions this means both models guess, and guess differently each time. Flash-lite's homework-levels answers varied from 47 to 208 output tokens 【check the "Answers" section of results_models.md: were the short ones "I don't know" and the long one an invented list?】. Thinking longer did not make 3.6 Flash know the course: it still answered course-specific questions it cannot know.
  - Relationship to the free-tier rate limits: the free tier limits each model by requests per minute (RPM), tokens per minute (TPM) and requests per day (RPD); the current values are in AI Studio and on the Gemini API rate-limits page. This run averaged 5.3 RPM and about 5,300 TPM and hit no 429, partly because of the 5-second spacing. Without spacing, flash-lite's 2.1 s calls would allow about 28 requests per minute, so RPM is the limit it would hit first. 3.6 Flash's 10.9 s calls cap it near 5–6 RPM, but at 1,536 tokens per call TPM and the daily request quota matter more. An agent (Lecture 03) makes several calls per question and re-sends growing context, multiplying both. The practical levers are spacing calls, retrying after a 429, choosing flash-lite unless the task needs reasoning, and limiting answer length.
  - Question: if thinking makes 3.6 Flash 5× slower and 3.5× more expensive here without making it know the course, which tasks actually justify a thinking model? And can the thinking budget be lowered per call?
