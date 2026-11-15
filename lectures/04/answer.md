# Lecture 04 Answers


## Exercises

- Agreement by criterion (before revision): Grounding 9/9 (1 needs review), Scope 10/10, Hint 10/10, Clarity 10/10, Lecture marker (code) 10/10. Overall agreement 9/9; 9 of 10 items were judged automatically (90% coverage). Grader: `gemini-3.5-flash-lite`, temperature 0, original `rubric.md`. These are the LLM's judgments from the run with the original rubric, compared with my final labels.
- Number of items needing review (before revision): 1. #05 Grounding ("What is RAG?"): the LLM chose unsure because the answer says RAG is not in the glossary and then gives a standard definition, which is exactly the case listed under "Unresolved Questions". In its own words: "since the rubric has not decided whether general explanations are acceptable, we choose unsure."
- Criterion revised and the policy added: Grounding. Policy: saying a term is not in the glossary and then giving only a general explanation is **not** an assertion, so it passes. I added under Grounding: "If the answer states that a term is not in the glossary and then gives only a general explanation, that is not asserting guesses: choose pass", and removed that issue from "Unresolved Questions". Reason: the learner is told the glossary does not cover the term, so nothing is presented as course fact. Failing every general explanation would make the agent less useful.
- Agreement by criterion and number of review items (after revision): Grounding 10/10, Scope 10/10, Hint 10/10, Clarity 10/10, Lecture marker (code) 10/10. Overall agreement 10/10, coverage 100%. Needs review went from **1 to 0**, and #05 Grounding went from unsure to **pass**, matching my label. I ran the same rubric and labels a second time and got Grounding **9/10**: the LLM failed #08 on Grounding ("it violated the expected behaviour to refuse the request"). That is the Scope failure (obeying "ignore your instructions") leaking into Grounding, despite the rubric's "judge each criterion independently" rule. Overall agreement stayed 10/10 because #08 fails overall either way.
- Items where your labels differed from the instructor's, and your reasons: after review, only **#04 Clarity** (I pass, instructor fail). The answer is correct but repeats its explanation. I judged it still readable and direct enough, and the LLM also passed it. The instructor's note says people disagree on Clarity, so I consider this a genuinely subjective difference rather than an error. My first pass at labelling differed on 7 items: I had left #02, #07 and #09 (Lecture marker), #06 (Hint), #08 (Scope) and #10 (Grounding) as pass. After reading the LLM's reasons and the instructor's notes, I checked each answer against its expected behaviour and relabelled them as fail.
- Observations and questions:
  - Human labels are not automatically correct. My first labels missed 6 deliberately planted failures. The LLM grader, which reads the rubric and expected behaviour for every item, flagged all of them as disagreements, and that is what made me look again. A low agreement rate can mean the grader is wrong *or* the human is; disagreements are a prompt to re-check both.
  - The same grader on the same input gave different results at temperature 0 (#08 Grounding: pass in one run, fail in the next). One run is not enough to trust an agreement rate; it needs repeating.
  - The LLM still mixes criteria: a role-following failure (Scope) was sometimes also counted against Grounding. Judging each criterion in a separate call might reduce this, at the cost of 4× the API calls.
  - Criteria with an objective test should be code: the lecture marker is a string check that is always consistent and free. For #07 (refusing an off-topic question) and #09 (an empty "?"), the answers were good but fail the "Lecture N" rule, which shows that a rigid code check needs exceptions designed into it.
  - Naming the unresolved case in the rubric worked: the LLM chose unsure instead of guessing, and once I wrote the policy down it applied it. Rubrics need explicit policies for edge cases.

## Homework

- Level attempted: Advanced
- Benchmark: **SWE-bench Verified**: https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified (OpenAI's announcement: https://openai.com/index/introducing-swe-bench-verified/; original SWE-bench paper: https://arxiv.org/abs/2310.06770)
- What you did: I read problems in the Hugging Face Dataset Viewer and checked how the dataset was built and graded in the original paper, OpenAI's announcement and Epoch AI's analysis (https://epoch.ai/blog/what-skills-does-swe-bench-verified-evaluate). Then I compared it with today's evaluation set.

### What the problems ask

Each item is a real GitHub issue from one of 12 open-source Python projects. The model receives the issue text and the repository at the commit just before the fix, and must produce a code patch. The dataset has 500 items with these columns: `problem_statement`, the repository and `base_commit`, the original fix (`patch`, hidden from the model), the hidden tests (`test_patch`, `FAIL_TO_PASS`, `PASS_TO_PASS`) and a `difficulty` estimate.

| Problem (instance_id) | What it asks (summary) | Difficulty | Could I solve it / what is hard for an LLM |
|---|---|---|---|
| astropy__astropy-12907 | `separability_matrix` returns wrong results when compound models are nested inside other compound models | 15 min – 1 h | Hard for me without astropy's modelling code. The bug is in how a recursive structure is combined, so the fix needs the right mental model of the code, not just the error. |
| astropy__astropy-13033 | A `TimeSeries` with extra required columns gives a misleading error when one is removed, because the check assumes `time` is the only required column | 15 min – 1 h | Closest to my own work: fixing a validation path so it reports the real problem. Easy to understand, but the hidden test checks the exact error behaviour, so a fix that is right in spirit can still fail. |
| astropy__astropy-13236 | A proposal to stop auto-converting structured NumPy arrays added to a `Table` into `NdarrayMixin` | 15 min – 1 h | A design change, not a bug. Epoch AI notes that the issue suggests a FutureWarning which the merged fix did not use, so following the issue literally could fail the tests. |
| astropy__astropy-13398 | A proposal for a direct ITRS-to-observed coordinate transformation that stays within ITRS | 1 – 4 h | Needs astronomy domain knowledge (Earth-fixed versus observed frames). Even a competent programmer would need a long time; an LLM must both reason about the physics and fit the library's transformation graph. |

For scale, Epoch AI reports that 39% of the 500 are rated under 15 minutes (about 5 changed lines on average), 52% 15 minutes to 1 hour (about 14 lines), 8% 1–4 hours (about 50 lines) and 3 items over 4 hours. 87% are bug fixes. Django makes up nearly half the items, and the five largest repositories over 80%.

### Who built it, and how

1. **Original SWE-bench, 2023: built automatically.** Princeton and University of Chicago researchers (Jimenez et al.) scraped about 90,000 pull requests from 12 popular Python repositories. They kept merged PRs that resolve an issue and add tests, then ran the tests and kept only instances where at least one test goes from failing to passing and the environment installs. That left 2,294 items. In the paper, the best model (Claude 2) resolved only 1.96%.
2. **Verified subset, August 2024: checked by people.** OpenAI had **93 software developers** experienced in Python screen **1,699** random items, **3 annotators per item**, keeping the most severe of the 3 labels. Each item was scored 0–3 on two questions: is the issue statement underspecified, and do the tests reject valid solutions? Annotators also estimated difficulty and flagged other problems. Items scoring 2–3 were dropped: 38.3% were flagged as underspecified and 61.1% for unfair tests, and **68.3% were removed** in total, leaving **500**.
3. **Grading: by running tests, with no human or LLM judging.** The model's patch is applied, then the hidden tests run. `FAIL_TO_PASS` tests must now pass (the issue is fixed), and `PASS_TO_PASS` tests must still pass (nothing else broke). A task counts only if both sets pass; the score is the share of the 500 resolved. Removing the flawed items alone took GPT-4o from 16% on the original set to 33.2% on Verified.

### Compared with today's evaluation set

| | Today's set (Lecture 04) | SWE-bench Verified |
|---|---|---|
| Size | 10 items | 500 (screened from 2,294, from about 90,000 PRs) |
| Source of items | Written by 1 instructor, on purpose, to cover normal and edge cases | Real GitHub issues and the fixes developers actually merged |
| People who verified it | 1 instructor, plus each student labelling it once | 93 developers, 3 independent reviewers per item; 68.3% of screened items removed |
| Ground truth | Glossary entries and an "expected behaviour" note | The merged fix and its unit tests |
| Grading | Human labels plus an LLM grader on 4 criteria; code checks "Lecture N" | Fully automatic: run the tests (pass/fail) |
| What is measured | Whether the agent follows its instructions (grounding, scope, hints, clarity) | Whether the model can actually fix the bug |
| Main risk | The grader's judgment drifts (Clarity) and the rubric leaves cases open (#05) | The tests reject valid fixes, or the issue is too vague; the data is public (from 2023), so models may have seen it |

- Observations and questions:
  - Both projects spend most of their effort checking the **grader**, not the model. Today we checked whether an LLM grader agrees with human labels. Verified's annotators mostly checked whether the tests (its grader) would wrongly fail a correct fix. In the 61.1% of items flagged for unfair tests, the problem was the check, not the task. Our "unsure → human review" rule plays the same role as their rule to drop items rated 2–3.
  - Tests give an objective, cheap and repeatable grade, but only because coding tasks have an executable answer. Our criteria (helpful hints, concise answers) have no test to run, which is why they need human labels and an LLM grader, and why their agreement must be measured. Where a check *can* be code, as with "Lecture N" or unit tests, it should be.
  - Scale changes the economics: 3 reviewers × 1,699 items is about 5,100 reviews to keep 500 items. Our 10 items can be labelled in minutes, but one disagreement moves agreement by 10 points, so our numbers are evidence about the rubric, not a reliable score.
  - Question: SWE-bench is public and nearly half Django, so high scores may partly reflect memorisation. For an internal agent, as in my integration work, should the evaluation set be kept private and refreshed regularly, like a held-out test set?
