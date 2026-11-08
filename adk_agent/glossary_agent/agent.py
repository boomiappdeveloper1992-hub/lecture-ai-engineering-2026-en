"""Lecture 03 homework (Advanced a): the exercise agent rebuilt with Google's ADK.

Only the agent-building part is new. INSTRUCTIONS and the tool functions are imported unchanged from app/.

Run from the repository root:
    PYTHONPATH=. uv run --with google-adk adk run adk_agent/glossary_agent
Type a question and press Enter; type exit to quit. The API key comes from the GEMINI_API_KEY Codespaces secret.
"""

from google.adk.agents import Agent

from app import tools
from app.agent import INSTRUCTIONS
from app.config import MODEL  # same model as the Pydantic AI agent (AIE_MODEL overrides it in both)

root_agent = Agent(
    model=MODEL,
    name="glossary_agent",
    description="Learning support agent for the AIE2026 course that answers from the course glossary.",
    instruction=INSTRUCTIONS,
    # Plain functions: ADK reads each function's name, type hints and docstring, as Pydantic AI does.
    # save_learning_log is left out: tools with approval are not part of this level.
    tools=[tools.search_glossary, tools.get_lecture_summary, tools.make_quiz],
)
