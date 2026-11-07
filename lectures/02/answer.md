# Lecture 02 Answers

## Exercises

- Model and settings used (from `config` in `result.json`): `Qwen/Qwen3.5-0.8B` (revision `2fc06364`), LoRA without quantization (32-bit), r=16 / alpha=32, lr=2e-4, 20 epochs (14 examples × 20 passes = 40 steps), warmup 6, greedy decoding, max_new_tokens=96. Trainable parameters: 6,389,760 (0.842% of the model).
- Did you run training yourself (`executed_training_myself`): Yes. I ran the whole notebook on a Colab T4: 40 steps of training took 230.1 s, and the final training loss was 0.0138 (average 0.420).
- Before training: `format_rate` = 0.095 / `content_rate` = 0.000
- After training: `format_rate` = 1.000 / `content_rate` = 0.905 (19 of 21 questions fully correct)
- Questions that regressed: none
- Failures remaining after training and their types (assertion without evidence / evasion through a confirmation request despite evidence being present / broken format): 2 questions, both **assertions without evidence**. Both are questions the FAQ does not answer, yet the model returned a sentence from another FAQ item with `needs_review: false`:
  - 「成績はいつ出ますか」 (When are grades released?) → returned the **file format** item: 「提出形式は PDF 1 ファイルで、ファイル名は 学籍番号_課題番号.pdf です。」 It is not even the nearest topic: the instructor's run used the deadline item for the same question, which shows which item gets borrowed varies between runs.
  - 「オフィスアワーは事前予約が必要ですか」 (Do office hours require a reservation?) → returned the **office hours** item: 「質問は毎週火曜 17:00〜18:00 のオフィスアワーで受け付けます。」 The question shares the words "office hours", so the model answered as if the item covered it.
- Results of knowledge questions (section 6; classification before → after training) and observations:
  - 「この講座の最終課題の締切はいつですか」 (final assignment deadline, not in the FAQ): format_error → **asserted**. After training it answered with the FAQ's assignment deadline (9 月 30 日 23:59), treating "final assignment" as "assignment".
  - 「担当教員の名前は何ですか」 (instructor's name): format_error → needs_review (correct)
  - 「次回の講義のテーマは何ですか」 (next lecture's topic): format_error → needs_review (correct). Before training, it produced a nonsense sentence mixing the portal and PDF items.
  - 「課題の提出期限はいつですか」 (assignment deadline, the control): format_error → asserted. This is correct: the question is in the FAQ (it is a training question, so the notebook's "FAQ にある" column shows False only because it checks the test set).
  - Observation: before training, every answer broke the format, mostly by leaving out the `needs_review` key (for example `{"answer": "9 月 30 日 23:59"}`). After training, every answer was valid JSON. Questions with no word in common with the FAQ (instructor, next lecture) correctly got "確認が必要". But the question sharing the word 締切/課題 with the FAQ was asserted with the deadline sentence. The model decides by "is there a similar word in the FAQ", not by "does the FAQ actually answer this".
- What changed and what stayed the same with training:
  - Changed: the format. Even with the format spelled out in the prompt, the model followed it on only 2 of 21 questions (0.095). After 14 examples and 230 s of LoRA training it followed it on all 21 (1.000), and the answers used the FAQ's exact wording.
  - Stayed the same: judging whether the FAQ supports an answer. Both remaining failures, and the final-deadline knowledge question, assert an answer the FAQ does not contain. A loss of 0.014 only shows that the 14 training examples are reproduced; it says nothing about judgment on unseen questions.
  - Also noted (section 8): loading the same untrained model in 4-bit changed its outputs without any training. Format rate went from 0.095 to 0.667 and content from 0.000 to 0.333, while weight memory dropped from 3.01 GB to 0.76 GB. Quantization changes behavior in either direction, so a before/after comparison must use the same quantization.

## Homework

- Level attempted: Advanced
- What I did: generated Q&A data with `scripts/make_sft_dataset.py` from the course glossary: 58 terms × 2 phrasings = 116 records in `messages` format. I ran the script in Colab instead of Codespaces; it is the same script with the same output. I trained LoRA on it instead of the FAQ, with the same model and LoRA settings as the exercise, 6 epochs and max_new_tokens 200 (section 10 of my notebook).
  - Variant A: the script output as-is (116 records, 90 steps).
  - Variant B: A plus 111 questions that use each term's aliases plus 16 examples answering "not in the glossary" (243 records, 186 steps).
- Evaluation questions and answers (made myself): 10 terms chosen with a fixed seed (Pi, temperature, 評価と改善のサイクル, 宿題の3レベル, ブランチ, Codespaces secret, devcontainer, ハルシネーション, トランスポート, システムプロンプト), each asked three ways: in the training phrasing (seen), in a new phrasing (reworded) and by an alias (alias). Also 10 terms not in the glossary (RAG, 埋め込みベクトル, ベクトルデータベース, RLHF, DPO, MoE, KVキャッシュ, 知識蒸留, plus two invented terms: スパイラル勾配正則化 and クロノ・トークナイザ) and 5 reverse-lookup questions that describe a term and ask for its name. 45 questions in total.
  - A glossary answer is correct when its character-bigram F1 against the glossary definition is ≥ 0.5.
  - An unknown term is correct when the answer says it is not in the glossary.
  - A reverse question is correct when the answer names the term.
- Baseline for comparison: no model at all, just a search that finds a term name or alias in the question and returns that glossary entry (`retrieval`).
- Results (accuracy per question type):

| System | seen | reworded | alias | unknown (said "not in glossary") | reverse | over-refusal | seen F1 | training |
|---|---|---|---|---|---|---|---|---|
| before (base model) | 0.00 | 0.00 | 0.00 | 0.00 | 0.20 | 0.00 | 0.07 | — |
| after A (script output) | 0.90 | 0.60 | 0.20 | 0.00 | 0.00 | 0.00 | 0.88 | 216.5 s, 90 steps, final loss 0.171 |
| after B (+ aliases + refusals) | 1.00 | 0.90 | 1.00 | 0.20 | 0.00 | 0.00 | 1.00 | 444.8 s, 186 steps, final loss 0.115 |
| retrieval (keyword search) | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 0.95 | none |

Side-effect check: three questions unrelated to the glossary, not scored.

| Question | before | after A | after B |
|---|---|---|---|
| 日本の首都はどこですか？ | 東京 (correct) | 「東京。2026年10月、法案で…本講座では…」 (invented course details) | 「東京。第3回の首都連盟の演習で…」 (invented course details) |
| 1 から 10 までの和はいくつですか？ | **55** (correct) | nonsense about "10^10" | **9** (wrong) |
| おはようございます。今日の気分はどうですか？ | A normal greeting | A glossary-style definition | 「AIE2026の演習と宿題の進捗を…ツール。」 |

- Observations:
  - **A memorized phrasings, not terms.** It reproduced definitions for the exact training phrasing (0.90, F1 0.88), but dropped to 0.60 for a new phrasing and 0.20 for an alias. For 「温度パラメータ」, an alias of temperature, it invented a definition about "学習データ…調整値" even though it answered 「temperature」 correctly.
  - **A never said "not in the glossary" (0/10), and invented definitions in the course's style.** It described the invented term 「クロノ・トークナイザ」 as a Claude Desktop tool, and said DPO is 「本講座の第3回で扱う」. The base model at least explained real terms like RAG and RLHF from general knowledge; after training, those answers became confident course-flavored fiction. A's data has no refusal examples, so it learned "every question has a glossary-style answer".
  - **B's extra data fixed known terms but barely fixed refusals.** Adding alias questions raised alias accuracy from 0.20 to 1.00. But this is not a fair held-out test for B, because those aliases were in its training data; reworded (0.90) is the fair measure. With 16 refusal examples, B refused only 2 of 10 unknown terms (MoE and the invented スパイラル勾配正則化) and invented the other 8. It also refused 2 of the 5 reverse-lookup questions, so it learned the refusal sentence without learning when to use it.
  - **Reverse lookup failed for everything after training.** The base model named 過学習 correctly (1/5); A and B got 0/5, and so did the keyword search. The search matched other words in the question (量子化, ランク（LoRAのr）, LLM, トークン) or nothing at all.
  - **Training damaged unrelated abilities.** After training on 116 glossary records, the model gave 9 or nonsense for "1 to 10" (the base model said 55), and answered a greeting with a glossary-style definition. Its answers drifted into the training data's style and topics: a small model fine-tuned on a narrow dataset over many passes loses general behavior (catastrophic forgetting).
  - Base model, before training: it answered every question at length from general knowledge, often wrongly (ハルシネーション explained as a phenomenon of light in physics). It also gave a confident definition of the invented term スパイラル勾配正則化, and evaluating it took 459 s against about 155 s after training.
- Pros and cons of training the model compared with searching the glossary:
  - Pros: after training, a short prompt returns the glossary's exact wording in a consistent style, with no search step at question time (B: seen F1 1.00). Paraphrases can work if the training data covers them (B: reworded 0.90).
  - Cons, all seen in my results:
    - It only knows what was trained, in the phrasings that were trained (A: alias 0.20 against search's 1.00). Every new term or correction needs retraining (217–445 s here) and re-evaluation; with search, editing `glossary.json` takes effect immediately.
    - It cannot reliably say "I don't know" (A 0/10, B 2/10 on unknown terms against the search's 10/10). It invents course-styled definitions instead, which is worse than the base model's general answers because they look authoritative.
    - It cannot show where an answer came from. The search returns the entry it matched, so a wrong match is visible; the trained model's invented definitions look exactly like the real ones.
    - It damages unrelated abilities ("1 to 10" = 9), and checking for that needs a separate evaluation.
  - Where search is weak: questions that do not contain the term's name (reverse lookup 0/5: keyword matching hit other words). Embedding (semantic) search or an LLM-written search query would address this better than training.
  - Conclusion: for definitions that live in a document and change, search wins on every measure except reverse lookup. The better design is to retrieve the entry and let the model write the answer from it, which is what Lecture 03's agent does with a `search_glossary` tool. Fine-tuning is better for how answers are written than for what they contain.
- Discussion of when fine-tuning is and is not suitable:
  - Suitable: making output format, structure and tone reliable. In the exercise, 14 examples and 230 s of training on a free T4, adapting 0.842% of the parameters, took format compliance from 0.095 to 1.000. It also suits narrow, high-volume tasks where long prompts are costly, and specializing a small model with a swappable adapter.
  - Not suitable: adding or updating knowledge. The glossary model needed retraining for every change, could not cite its source, invented answers for anything it did not know, and lost general abilities. Facts that change (FAQs, glossaries, specifications) belong in retrieval. Also not suitable where judgment matters: the format reached 100%, but the model still asserted answers the FAQ did not contain, in both the exercise and the glossary. That judgment needs evaluation on confusable questions, rules, or human review.
  - Data design matters more than settings. With 5 FAQ items the model learned "a similar word appears, so reuse that item's sentence". With no refusal examples in the glossary data it never refused; with 16 it refused rarely, and sometimes where it should not have. What the training data says about questions it cannot answer decides what the model learns to do with them.
