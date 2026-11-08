# Lecture 03 Answers


## Exercises

- Differences between the Lecture 01 (bare LLM) and agent answers: In Lecture 01, `app.ask` answered confidently with three invented tiers ("Level 1: Core / Fundamentals", "Level 2: Intermediate / Application", "Level 3: Advanced / Research & Challenge") and said nothing about how many levels to do. The agent looked the term up in the glossary and answered correctly: Basic (review the lecture content), Implementation (write your own code) and Advanced (research and experimentation). It added that completing **any one level** finishes the homework and that homework is not graded as a rule, the two facts the bare LLM missed. It ended with "(Lecture 01)", as INSTRUCTIONS require. Both runs used the same model, `gemini-3.5-flash-lite`, so the difference comes from the tool, not the model.
- Tool calls shown by `--trace` (tool names and arguments): for "What is the difference between LoRA and QLoRA?", `search_glossary({'query': 'LoRA'})`, then `search_glossary({'query': 'QLoRA'})`. Both returned their Lecture 02 glossary entries. The model searched the two terms separately because the `search_glossary` docstring says "Put only one term to look up in query", and INSTRUCTIONS say to check the glossary before answering about terms. The answer quoted both definitions ("Based on the course glossary"), explained the difference (QLoRA adds 4-bit quantization of the base weights to save memory) and ended with "(Lecture 02)".
- Number of LLM calls for one question (`requests`): `requests=2, tool_calls=2` for LoRA vs QLoRA, with 1,633 input tokens and 225 output tokens. The first LLM call decided which tools to call; both tool calls were made in that one turn; the second LLM call wrote the answer from the tool results. So one agent question took 2 LLM calls against 1 for `app.ask` in Lecture 01. Its input was 1,633 tokens against 6–19 for a bare question: the instructions, the tool descriptions and the tool results are all sent with every call. The agent therefore uses up the free tier's request and token limits much faster than a bare call.
- Tool added and the description in its docstring: `make_quiz(lecture: int)` in `app/tools.py`, registered with `agent.tool_plain(tools.make_quiz)` in `app/agent.py`. It picks a random term from that lecture in the glossary and returns `{"lecture", "question": "What does “X” mean?", "answer": definition}` as JSON. If the lecture has no terms (for example `lecture=0`), it returns a message listing the lectures that do. Docstring: "Pick one term covered in the given session and return a review question with its answer. Use when the learner asks for a review question or a quiz about a session, such as "Give me one review question from Lecture 02". lecture is the session number (an integer starting at 1). Ask the learner the question first and reveal the answer only after they have tried." `--list-tools` showed it as one of 4 tools. For "Give me one review question from Lecture 02" the trace showed `[tool call] make_quiz({'lecture': 2})` (requests=2, tool_calls=1), and the agent asked "What does “Quantization” mean?" without revealing the answer, as the docstring instructs. I did not need to add anything to INSTRUCTIONS for the tool to be called.

## Homework

- Level attempted: Advanced (a)
- What you did: created `adk_agent/glossary_agent/agent.py` and `__init__.py`. It imports `INSTRUCTIONS` and the tool functions unchanged from `app/` and passes `search_glossary`, `get_lecture_summary` and `make_quiz` to ADK's `Agent` (`save_learning_log` left out, as the level allows). Run: `PYTHONPATH=. uv run --with google-adk adk run adk_agent/glossary_agent` (ADK 2.14).
- Results — code:

| | Pydantic AI (`app/agent.py`) | ADK (`adk_agent/glossary_agent/agent.py`) |
|---|---|---|
| Instructions | `Agent(instructions=INSTRUCTIONS)` | `Agent(instruction=INSTRUCTIONS)` (singular) |
| Tools | `agent.tool_plain(func)` one at a time, after creating the agent | `tools=[func, …]` list in the constructor |
| Tool description | Function name, type hints and docstring | The same; ADK builds the same JSON schema from them |
| Model | Passed at run time (`run_sync(model=…)`), so tests can swap in `TestModel` | Fixed in the constructor (`model=MODEL`) |
| Running it | Our own CLI (`app.agent`, `--trace`, `--list-tools`) | `adk run` gives a chat loop; `adk web` gives a browser UI with event traces |
| Agent name | Not needed | Required `name`, plus an optional `description` used when agents hand off to each other |

- Results — answers: in `adk run` I asked "What are the 3 homework levels in the AIE2026 course?". The ADK agent answered with the same content as the Pydantic AI agent: Basic (review lecture content), Implementation (write your own code) and Advanced (research and experimentation). It also noted that completing any one level fulfils the homework and that homework is not graded as a rule, and it ended with "(Lecture 01)". Those course-specific facts and the "(Lecture NN)" ending come only from the glossary entry and INSTRUCTIONS; the bare model in Lecture 01 invented different levels for the same question. So the ADK agent used the same `search_glossary` tool and followed the same instructions. Only the wording differed slightly (a bulleted note instead of an opening sentence). ADK's terminal log (`/tmp/agents_log/agent.latest.log`) did not print the function calls at its default log level, so to see them as a trace I would use `adk web`, which shows each event, including tool calls and their arguments.
- Observations and questions:
  - The instructions and tool functions carried over without any change, and the answer kept the same facts and the same ending. The agent's behaviour comes from those two things (the prompt and the tool descriptions built from docstrings), not from the framework. Switching frameworks changed only the assembly code, about 10 lines.
  - Pydantic AI suits small scripts and testing: the model is passed at run time, so `TestModel` checks the tools with no API key, and `--trace` comes with it. ADK gives more out of the box: a chat loop that keeps the conversation (`adk run`), a web UI with event traces (`adk web`), and agent names and descriptions for handing work between several agents. In exchange, the model is fixed when the agent is created and the code is shaped around its directory layout.
  - Question: how would the approval step from the Implementation level (`requires_approval=True` in Pydantic AI) be done in ADK, and does ADK have an equivalent of `TestModel` for testing without an API key?

@boomiappdeveloper1992-hub ➜ /workspaces/lecture-ai-engineering-2026-en (lec03) $ uv run pytest -q
.............................                                                                                  [100%]
================================================== warnings summary ==================================================
.venv/lib/python3.14/site-packages/google/genai/types.py:42
  /workspaces/lecture-ai-engineering-2026-en/.venv/lib/python3.14/site-packages/google/genai/types.py:42: DeprecationWarning: '_UnionGenericAlias' is deprecated and slated for removal in Python 3.17
    VersionedUnionType = Union[builtin_types.UnionType, _UnionGenericAlias]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
29 passed, 1 warning in 6.12s
@boomiappdeveloper1992-hub ➜ /workspaces/lecture-ai-engineering-2026-en (lec03) $ uv run python -m app.agent --list-tools
                 pydantic-ai v2.57.0 • Python 3.14.2
      / \
     /   \       agent: target • model: test:test • output: str | DeferredToolRequests • tools: 4 • capabilities: 0
   /___.___\
  /    |    \    observability: off — see every model and tool call live, with cost
/      |      \    set it up free with Logfire and a GitHub login: https://pydantic.dev/ai-setup.md
`---.._|_..---'    or use any OpenTelemetry backend: https://pydantic.dev/docs/ai/logfire/#otel

                 goes away once observability is on — or PYDANTIC_AI_NO_BANNER=1
Tools visible to the model: 4

[search_glossary]
  Search the course glossary and return definitions and the sessions that cover the terms.
  
  Use before answering about AI engineering terms or words specific to this course (AIE2026).
  Put only one term to look up in query (for example, "LoRA").
  Arguments: {"query": {"type": "string"}}

[get_lecture_summary]
  Return key points from the specified session (an integer starting at 1).
  
  Use when asked about session content or relationships, such as "What will we learn in Lecture 03?".
  Arguments: {"lecture": {"type": "integer"}}

[make_quiz]
  Pick one term covered in the given session and return a review question with its answer.
  
  Use when the learner asks for a review question or a quiz about a session,
  such as "Give me one review question from Lecture 02". lecture is the session number (an integer starting at 1).
  Ask the learner the question first and reveal the answer only after they have tried.
  Arguments: {"lecture": {"type": "integer"}}

[save_learning_log]
  Save a learning record (what the learner studied, understood or wants to review) as a Markdown file in learning_log/.
  
  Use only when the learner explicitly asks to save, record or log something, such as
  "Save what I learned about LoRA today". title is a short heading; content is the text of the record.
  Saving writes a file, so the learner is asked to approve each save before it runs.
  Arguments: {"title": {"type": "string"}, "content": {"type": "string"}}
@boomiappdeveloper1992-hub ➜ /workspaces/lecture-ai-engineering-2026-en (lec03) $ uv run python -m app.agent "What are the 3 homework levels in the AIE2026 course?"
[model] gemini-3.5-flash-lite
                 pydantic-ai v2.57.0 • Python 3.14.2

      / \        agent: target • model: google:gemini-3.5-flash-lite • output: str | DeferredToolRequests • tools: 4
     /   \         capabilities: 0
   /___.___\
  /    |    \    observability: off — see every model and tool call live, with cost
/      |      \    set it up free with Logfire and a GitHub login: https://pydantic.dev/ai-setup.md
`---.._|_..---'    or use any OpenTelemetry backend: https://pydantic.dev/docs/ai/logfire/#otel

                 goes away once observability is on — or PYDANTIC_AI_NO_BANNER=1
In the AIE2026 course, homework is structured into three distinct levels. You only need to complete **any one level** to consider the homework for that lecture done, and as a rule, they are not graded. 

The 3 homework levels are:

1. **Basic**: Review the lecture content.
2. **Implementation**: Write your own code.
3. **Advanced**: Research and experimentation.

*(Lecture 01)*
@boomiappdeveloper1992-hub ➜ /workspaces/lecture-ai-engineering-2026-en (lec03) $ uv run python -m app.agent --trace"What is the difference between LoRA and QLoRA?"
[model] gemini-3.5-flash-lite
                 pydantic-ai v2.57.0 • Python 3.14.2

      / \        agent: target • model: google:gemini-3.5-flash-lite • output: str | DeferredToolRequests • tools: 4
     /   \         capabilities: 0
   /___.___\
  /    |    \    observability: off — see every model and tool call live, with cost
/      |      \    set it up free with Logfire and a GitHub login: https://pydantic.dev/ai-setup.md
`---.._|_..---'    or use any OpenTelemetry backend: https://pydantic.dev/docs/ai/logfire/#otel

                 goes away once observability is on — or PYDANTIC_AI_NO_BANNER=1
Based on the course glossary:

* **LoRA (Low-Rank Adaptation):** A Parameter-Efficient Fine-Tuning (PEFT) method that freezes the pretrained model weights, represents weight updates as a low-rank product of two small matrices, and trains only those small matrices.This significantly reduces the number of trainable parameters and saves the results as small adapter files.
* **QLoRA (Quantized LoRA):** An extension that saves even more memory by quantizing the base-model weights (for example, down to 4 bits) before applying LoRA training. This allows you to train larger models on smaller GPUs.

To think about how they work together: LoRA focuses on *how* we adapt the model (using low-rank matrices), while QLoRA adds *quantization* to the base weights to drastically reduce memory usage during that training process.

(Lecture 02)

--- trace ---
[tool call]   search_glossary({'query': 'LoRA'})
[tool call]   search_glossary({'query': 'QLoRA'})
[tool return] search_glossary -> [{"term": "LoRA", "lecture": 2, "definition": "A PEFT method that freezes pretrained weights, represents weight updates …
[tool return] search_glossary -> [{"term": "QLoRA", "lecture": 2, "definition": "A method that saves memory by quantizing base-model weights to, for exam…
[usage] RunUsage(cost=Decimal('0.0010524'), details={'text_prompt_tokens': 1633}, input_text_tokens=1633, input_tokens=1633, output_tokens=225, requests=2, tool_calls=2)
@boomiappdeveloper1992-hub ➜ /workspaces/lecture-ai-engineering-2026-en (lec03) $ uv run python -m app.agent --trace"Give me one review question from Lecture 02"
[model] gemini-3.5-flash-lite
                 pydantic-ai v2.57.0 • Python 3.14.2

      / \        agent: target • model: google:gemini-3.5-flash-lite • output: str | DeferredToolRequests • tools: 4
     /   \         capabilities: 0
   /___.___\
  /    |    \    observability: off — see every model and tool call live, with cost
/      |      \    set it up free with Logfire and a GitHub login: https://pydantic.dev/ai-setup.md
`---.._|_..---'    or use any OpenTelemetry backend: https://pydantic.dev/docs/ai/logfire/#otel

                 goes away once observability is on — or PYDANTIC_AI_NO_BANNER=1
Here is a review question from Lecture 02:

**What does “Quantization” mean?**

Give it your best shot! Let me know your answer whenever you're ready, and we can discuss it.

(Lecture 02)

--- trace ---
[tool call]   make_quiz({'lecture': 2})
[tool return] make_quiz -> {"lecture": 2, "question": "What does “Quantization” mean?", "answer": "A technique for representing model weights with …
[usage] RunUsage(cost=Decimal('0.0005260'), details={'text_prompt_tokens': 1195}, input_text_tokens=1195, input_tokens=1195, output_tokens=67, requests=2, tool_calls=1)
@boomiappdeveloper1992-hub ➜ /workspaces/lecture-ai-engineering-2026-en (lec03) $ PYTHONPATH=. uv run --with google-adk adk run adk_agent/glossary_agent
Installed 48 packages in 4.33s
Help improve the ADK (CLI and Web UI) by allowing Google to collect pseudonymized usage data?

What is collected: Names of subcommands and flags (no user-provided values or arguments), execution metrics (duration, exit state), environment specs (OS, Python version), and aggregated Web UI feature interactions. No personally identifiable information (PII) is collected.

This is OFF by default. You can opt out at any time using the 'adk telemetry disable' command or Web UI user settings.

Enable telemetry? [Y/n]: y
Log setup complete: /tmp/agents_log/agent.20261108_112142.log
To access latest log: tail -F /tmp/agents_log/agent.latest.log
Running agent glossary_agent, type exit to exit.
[user]: 
[user]: 
[user]: exit
@boomiappdeveloper1992-hub ➜ /workspaces/lecture-ai-engineering-2026-en (lec03) $ ^C
@boomiappdeveloper1992-hub ➜ /workspaces/lecture-ai-engineering-2026-en (lec03) $ ^C
@boomiappdeveloper1992-hub ➜ /workspaces/lecture-ai-engineering-2026-en (lec03) $ PYTHONPATH=. uv run --with google-adk adk run adk_agent/glossary_agent
Log setup complete: /tmp/agents_log/agent.20261108_112348.log
To access latest log: tail -F /tmp/agents_log/agent.latest.log
Running agent glossary_agent, type exit to exit.
[user]: What are the 3 homework levels in the AIE2026 course?
[glossary_agent]: In the AIE2026 course, the three homework levels are:

1. **Basic** — Review lecture content.
2. **Implementation** — Write your own code.
3. **Advanced** — Research and experimentation.

*(Note: Completing any one of these levels fulfills the homework requirement for that lecture, and as a rule, homework is not graded.)*

(Lecture 01)
[user]: exit
@boomiappdeveloper1992-hub ➜ /workspaces/lecture-ai-engineering-2026-en (lec03) $ grep -iE "function_call|functionCall|search_glossary|make_quiz" /tmp/agents_log/agent.latest.log | head -20