"""Creates the Claude model used by every agent."""
from langchain_anthropic import ChatAnthropic

from gym_ai import config


def get_llm() -> ChatAnthropic:
    """Needs the ANTHROPIC_API_KEY environment variable (see .env.example)."""
    return ChatAnthropic(model=config.MODEL_NAME)
