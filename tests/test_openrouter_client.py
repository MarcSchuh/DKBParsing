"""Unit tests for openrouter_client.py."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dkbparsing.openrouter_client import OpenRouterError, call_openrouter


class TestCallOpenRouter:
    """Tests for call_openrouter function."""

    def test_call_openrouter_success(self):
        """Test successful OpenRouter API call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            system_prompt_file = Path(tmpdir) / "system_prompt.txt"
            system_prompt_file.write_text(
                "You are a helpful assistant.",
                encoding="utf-8",
            )

            manual_assignments = [
                {
                    "date": "01.08.25",
                    "recipient": "Test Recipient",
                    "purpose": "Test Purpose",
                    "category": "test",
                },
            ]

            uncategorized_transactions = [
                {
                    "booking_date": "01.08.25",
                    "value_date": "01.08.25",
                    "status": "Gebucht",
                    "payer": "Test",
                    "recipient": "Unknown",
                    "purpose": "Unknown",
                    "transaction_type": "Ausgang",
                    "iban": "DE123456789",
                    "amount": -10.0,
                },
            ]

            # Mock OpenAI response
            mock_message = Mock()
            mock_message.content = "Suggested category: test"
            mock_choice = Mock()
            mock_choice.message = mock_message
            mock_response = Mock()
            mock_response.choices = [mock_choice]

            with patch("dkbparsing.openrouter_client.OpenAI") as mock_openai_class:
                mock_client = Mock()
                mock_openai_class.return_value = mock_client
                mock_client.chat.completions.create.return_value = mock_response

                result = call_openrouter(
                    api_key="test-api-key",
                    system_prompt_file=system_prompt_file,
                    manual_assignments=manual_assignments,
                    uncategorized_transactions=uncategorized_transactions,
                )

                assert result == "Suggested category: test"
                mock_openai_class.assert_called_once_with(
                    api_key="test-api-key",
                    base_url="https://openrouter.ai/api/v1",
                    default_headers={
                        "HTTP-Referer": "https://github.com/marc-schuh/dkbparsing",
                        "X-Title": "DKB Parsing",
                    },
                )
                mock_client.chat.completions.create.assert_called_once()
                call_args = mock_client.chat.completions.create.call_args
                assert call_args[1]["model"] == "openrouter/auto"

    def test_call_openrouter_missing_system_prompt_file(self):
        """Test error when system prompt file doesn't exist."""
        system_prompt_file = Path("/nonexistent/path/system_prompt.txt")

        with pytest.raises(OpenRouterError) as exc_info:
            call_openrouter(
                api_key="test-api-key",
                system_prompt_file=system_prompt_file,
                manual_assignments=[],
                uncategorized_transactions=[],
            )

        assert "Failed to read system prompt file" in str(exc_info.value)

    def test_call_openrouter_api_error(self):
        """Test error handling when API call fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            system_prompt_file = Path(tmpdir) / "system_prompt.txt"
            system_prompt_file.write_text(
                "You are a helpful assistant.",
                encoding="utf-8",
            )

            with patch("dkbparsing.openrouter_client.OpenAI") as mock_openai_class:
                mock_client = Mock()
                mock_openai_class.return_value = mock_client
                mock_client.chat.completions.create.side_effect = Exception("API Error")

                with pytest.raises(OpenRouterError) as exc_info:
                    call_openrouter(
                        api_key="test-api-key",
                        system_prompt_file=system_prompt_file,
                        manual_assignments=[],
                        uncategorized_transactions=[],
                    )

                assert "OpenRouter API request failed" in str(exc_info.value)

    def test_call_openrouter_invalid_response(self):
        """Test error handling when API returns invalid response."""
        with tempfile.TemporaryDirectory() as tmpdir:
            system_prompt_file = Path(tmpdir) / "system_prompt.txt"
            system_prompt_file.write_text(
                "You are a helpful assistant.",
                encoding="utf-8",
            )

            # Mock OpenAI response with empty choices
            mock_response = Mock()
            mock_response.choices = []

            with patch("dkbparsing.openrouter_client.OpenAI") as mock_openai_class:
                mock_client = Mock()
                mock_openai_class.return_value = mock_client
                mock_client.chat.completions.create.return_value = mock_response

                with pytest.raises(OpenRouterError) as exc_info:
                    call_openrouter(
                        api_key="test-api-key",
                        system_prompt_file=system_prompt_file,
                        manual_assignments=[],
                        uncategorized_transactions=[],
                    )

                assert "Invalid response from OpenRouter API" in str(exc_info.value)

    def test_call_openrouter_empty_content(self):
        """Test error handling when API returns empty content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            system_prompt_file = Path(tmpdir) / "system_prompt.txt"
            system_prompt_file.write_text(
                "You are a helpful assistant.",
                encoding="utf-8",
            )

            # Mock OpenAI response with empty content
            mock_message = Mock()
            mock_message.content = ""
            mock_choice = Mock()
            mock_choice.message = mock_message
            mock_response = Mock()
            mock_response.choices = [mock_choice]

            with patch("dkbparsing.openrouter_client.OpenAI") as mock_openai_class:
                mock_client = Mock()
                mock_openai_class.return_value = mock_client
                mock_client.chat.completions.create.return_value = mock_response

                with pytest.raises(OpenRouterError) as exc_info:
                    call_openrouter(
                        api_key="test-api-key",
                        system_prompt_file=system_prompt_file,
                        manual_assignments=[],
                        uncategorized_transactions=[],
                    )

                assert "Invalid response from OpenRouter API: empty content" in str(
                    exc_info.value,
                )

    def test_call_openrouter_with_manual_assignments(self):
        """Test that manual assignments are included in the request."""
        with tempfile.TemporaryDirectory() as tmpdir:
            system_prompt_file = Path(tmpdir) / "system_prompt.txt"
            system_prompt_file.write_text(
                "You are a helpful assistant.",
                encoding="utf-8",
            )

            manual_assignments = [
                {
                    "date": "01.08.25",
                    "recipient": "Test Recipient",
                    "purpose": "Test Purpose",
                    "category": "test",
                },
            ]

            # Mock OpenAI response
            mock_message = Mock()
            mock_message.content = "Response"
            mock_choice = Mock()
            mock_choice.message = mock_message
            mock_response = Mock()
            mock_response.choices = [mock_choice]

            with patch("dkbparsing.openrouter_client.OpenAI") as mock_openai_class:
                mock_client = Mock()
                mock_openai_class.return_value = mock_client
                mock_client.chat.completions.create.return_value = mock_response

                call_openrouter(
                    api_key="test-api-key",
                    system_prompt_file=system_prompt_file,
                    manual_assignments=manual_assignments,
                    uncategorized_transactions=[],
                )

                # Verify that manual assignments are in the user message
                call_args = mock_client.chat.completions.create.call_args
                messages = call_args[1]["messages"]
                user_message = messages[1]["content"]
                assert "Existing Manual Assignments" in user_message
                assert "Test Recipient" in user_message

    def test_call_openrouter_with_uncategorized_transactions(self):
        """Test that uncategorized transactions are included in the request."""
        with tempfile.TemporaryDirectory() as tmpdir:
            system_prompt_file = Path(tmpdir) / "system_prompt.txt"
            system_prompt_file.write_text(
                "You are a helpful assistant.",
                encoding="utf-8",
            )

            uncategorized_transactions = [
                {
                    "booking_date": "01.08.25",
                    "value_date": "01.08.25",
                    "status": "Gebucht",
                    "payer": "Test",
                    "recipient": "Unknown",
                    "purpose": "Unknown",
                    "transaction_type": "Ausgang",
                    "iban": "DE123456789",
                    "amount": -10.0,
                },
            ]

            # Mock OpenAI response
            mock_message = Mock()
            mock_message.content = "Response"
            mock_choice = Mock()
            mock_choice.message = mock_message
            mock_response = Mock()
            mock_response.choices = [mock_choice]

            with patch("dkbparsing.openrouter_client.OpenAI") as mock_openai_class:
                mock_client = Mock()
                mock_openai_class.return_value = mock_client
                mock_client.chat.completions.create.return_value = mock_response

                call_openrouter(
                    api_key="test-api-key",
                    system_prompt_file=system_prompt_file,
                    manual_assignments=[],
                    uncategorized_transactions=uncategorized_transactions,
                )

                # Verify that uncategorized transactions are in the user message
                call_args = mock_client.chat.completions.create.call_args
                messages = call_args[1]["messages"]
                user_message = messages[1]["content"]
                assert "Uncategorized Transactions" in user_message
                assert "Unknown" in user_message
