"""
OpenRouter API client for AI-powered transaction categorization suggestions.
"""

import json
import logging
from pathlib import Path
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenRouterError(Exception):
    """Exception raised when OpenRouter API call fails."""


def call_openrouter(
    api_key: str,
    system_prompt_file: Path,
    manual_assignments: list[dict[str, Any]],
    uncategorized_transactions: list[dict[str, Any]],
) -> str:
    """
    Call OpenRouter API with auto-routing to get categorization suggestions.

    Args:
        api_key: OpenRouter API key
        system_prompt_file: Path to file containing system prompt
        manual_assignments: List of manual assignments (for context)
        uncategorized_transactions: List of uncategorized transactions to categorize

    Returns:
        Response text from OpenRouter API

    Raises:
        OpenRouterError: If API call fails
    """
    # Read system prompt from file
    try:
        with open(system_prompt_file, encoding="utf-8") as f:
            system_prompt = f.read().strip()
    except OSError as e:
        raise OpenRouterError(
            f"Failed to read system prompt file {system_prompt_file}: {e}",
        ) from e

    # Prepare user message with context
    user_message_parts = []

    if manual_assignments:
        user_message_parts.append("## Existing Manual Assignments:")
        user_message_parts.append(
            json.dumps(manual_assignments, indent=2, ensure_ascii=False),
        )
        user_message_parts.append("")

    if uncategorized_transactions:
        user_message_parts.append("## Uncategorized Transactions:")
        user_message_parts.append(
            json.dumps(uncategorized_transactions, indent=2, ensure_ascii=False),
        )
        user_message_parts.append("")

    user_message_parts.append(
        "Please suggest categories for the uncategorized transactions based on the "
        "existing manual assignments as context. Return your suggestions in a clear format.",
    )

    user_message = "\n".join(user_message_parts)

    # Initialize OpenAI client with OpenRouter base URL
    try:
        logger.info("Calling OpenRouter API with auto-routing...")
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/marc-schuh/dkbparsing",
                "X-Title": "DKB Parsing",
            },
        )

        response = client.chat.completions.create(
            model="openrouter/auto",  # Auto-routing - OpenRouter selects best model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            timeout=60.0,
        )

        if not response.choices or not response.choices[0].message.content:
            raise OpenRouterError("Invalid response from OpenRouter API: empty content")

        logger.info("OpenRouter API call successful")
        return response.choices[0].message.content

    except Exception as e:
        if isinstance(e, OpenRouterError):
            raise
        raise OpenRouterError(f"OpenRouter API request failed: {e}") from e
