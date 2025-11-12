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
    user_prompt_file: Path,
) -> str:
    """
    Call OpenRouter API with auto-routing to get categorization suggestions.

    Args:
        api_key: OpenRouter API key
        system_prompt_file: Path to file containing system prompt
        manual_assignments: List of manual assignments (for context)
        uncategorized_transactions: List of uncategorized transactions to categorize
        user_prompt_file: Path to file containing user prompt template.
            The template should contain placeholders {manual_assignments} and
            {uncategorized_transactions} which will be replaced with JSON data.

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

    # Read user prompt template from file (required)
    try:
        with open(user_prompt_file, encoding="utf-8") as f:
            user_prompt_template = f.read()
    except OSError as e:
        raise OpenRouterError(
            f"Failed to read user prompt file {user_prompt_file}: {e}",
        ) from e

    # Replace placeholders in template
    manual_assignments_json = (
        json.dumps(manual_assignments, indent=2, ensure_ascii=False)
        if manual_assignments
        else "[]"
    )
    uncategorized_transactions_json = (
        json.dumps(uncategorized_transactions, indent=2, ensure_ascii=False)
        if uncategorized_transactions
        else "[]"
    )

    user_message = user_prompt_template.replace(
        "{manual_assignments}",
        manual_assignments_json,
    ).replace("{uncategorized_transactions}", uncategorized_transactions_json)

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
            timeout=120.0,
        )

        if not response.choices or not response.choices[0].message.content:
            raise OpenRouterError("Invalid response from OpenRouter API: empty content")

        logger.info("OpenRouter API call successful")
        return response.choices[0].message.content

    except Exception as e:
        if isinstance(e, OpenRouterError):
            raise
        raise OpenRouterError(f"OpenRouter API request failed: {e}") from e
