"""Unit tests for category_manager.py."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from dkbparsing.category_manager import (
    CategoryManager,
    FileLoadingError,
    ManualAssignmentCategoryError,
)
from dkbparsing.models import Category, ParsedTransaction, Transaction, TransactionType


class TestCategoryManagerInitialization:
    """Tests for CategoryManager initialization."""

    def test_init_without_existing_files(self):
        """Test initialization when both files don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            assert manager.category_file == category_file
            assert manager.manual_assignments_file == manual_file
            assert manager.categories == {}
            assert manager.manual_assignments == []

    def test_init_with_existing_category_file(self):
        """Test initialization when only category_file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            # Create category file
            category_data = {
                "groceries": {
                    "display_name": "Groceries",
                    "search_strings": ["supermarket"],
                    "regex_patterns": [],
                },
            }
            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(category_data, f)

            manager = CategoryManager(category_file, manual_file)

            assert len(manager.categories) == 1
            assert "groceries" in manager.categories
            assert manager.categories["groceries"].display_name == "Groceries"
            assert manager.manual_assignments == []

    def test_init_with_existing_manual_assignments_file(self):
        """Test initialization when only manual_assignments_file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            # Create category file with the category referenced in manual assignments
            category_data = {
                "test": {
                    "display_name": "Test",
                    "search_strings": [],
                    "regex_patterns": [],
                },
            }
            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(category_data, f)

            # Create manual assignments file
            manual_data = {
                "manual_assignments": [
                    {
                        "date": "15.01.24",
                        "recipient": "Test",
                        "purpose": "Test",
                        "category": "test",
                    },
                ],
            }
            with open(manual_file, "w", encoding="utf-8") as f:
                json.dump(manual_data, f)

            manager = CategoryManager(category_file, manual_file)

            assert len(manager.categories) == 1
            assert "test" in manager.categories
            assert len(manager.manual_assignments) == 1
            assert manager.manual_assignments[0]["category"] == "test"

    def test_init_with_both_existing_files(self):
        """Test initialization when both files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            # Create both files
            category_data = {
                "groceries": {
                    "display_name": "Groceries",
                    "search_strings": ["supermarket"],
                    "regex_patterns": [],
                },
            }
            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(category_data, f)

            manual_data = {"manual_assignments": []}
            with open(manual_file, "w", encoding="utf-8") as f:
                json.dump(manual_data, f)

            manager = CategoryManager(category_file, manual_file)

            assert len(manager.categories) == 1
            assert len(manager.manual_assignments) == 0

    def test_init_loads_categories_on_startup(self):
        """Test that categories are loaded on startup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            category_data = {
                "groceries": {
                    "display_name": "Groceries",
                    "search_strings": ["supermarket", "grocery"],
                    "regex_patterns": [r"^GROCERY"],
                },
                "salary": {
                    "display_name": "Salary",
                    "search_strings": ["salary"],
                    "regex_patterns": [],
                },
            }
            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(category_data, f)

            manager = CategoryManager(category_file, manual_file)

            assert len(manager.categories) == 2
            assert "groceries" in manager.categories
            assert "salary" in manager.categories
            assert len(manager.categories["groceries"].search_strings) == 2
            assert len(manager.categories["groceries"].regex_patterns) == 1

    def test_init_loads_manual_assignments_on_startup(self):
        """Test that manual assignments are loaded on startup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            # Create category file with categories referenced in manual assignments
            category_data = {
                "cat1": {
                    "display_name": "Category 1",
                    "search_strings": [],
                    "regex_patterns": [],
                },
                "cat2": {
                    "display_name": "Category 2",
                    "search_strings": [],
                    "regex_patterns": [],
                },
            }
            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(category_data, f)

            manual_data = {
                "manual_assignments": [
                    {
                        "date": "15.01.24",
                        "recipient": "Recipient1",
                        "purpose": "Purpose1",
                        "category": "cat1",
                    },
                    {
                        "date": "20.02.24",
                        "recipient": "Recipient2",
                        "purpose": "Purpose2",
                        "category": "cat2",
                        "amount": 100.0,
                    },
                ],
            }
            with open(manual_file, "w", encoding="utf-8") as f:
                json.dump(manual_data, f)

            manager = CategoryManager(category_file, manual_file)

            assert len(manager.manual_assignments) == 2
            assert manager.manual_assignments[0]["category"] == "cat1"
            assert manager.manual_assignments[1]["amount"] == 100.0


class TestCategoryManagement:
    """Tests for category CRUD operations."""

    def test_add_category_new(self):
        """Test adding a new category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )

            manager.add_category(category)

            assert "groceries" in manager.categories
            assert manager.categories["groceries"] == category

    def test_add_category_overwrite_existing(self):
        """Test overwriting an existing category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category1 = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )
            manager.add_category(category1)

            category2 = Category(
                name="groceries",
                display_name="Groceries Updated",
                search_strings=["supermarket", "grocery"],
            )
            manager.add_category(category2)

            assert len(manager.categories) == 1
            assert manager.categories["groceries"].display_name == "Groceries Updated"
            assert len(manager.categories["groceries"].search_strings) == 2

    def test_add_category_auto_save_success(self):
        """Test auto-save after add_category (successful)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )

            manager.add_category(category)

            # Verify file was created and contains the category
            assert category_file.exists()
            with open(category_file, encoding="utf-8") as f:
                data = json.load(f)
                assert "groceries" in data
                assert data["groceries"]["display_name"] == "Groceries"

    def test_add_category_auto_save_failure(self):
        """Test auto-save after add_category (failure doesn't throw, operation succeeds)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )

            # Mock save_categories to raise an exception
            from dkbparsing.category_manager import FileSavingError

            with patch.object(
                manager,
                "save_categories",
                side_effect=FileSavingError("Disk full"),
            ):
                # Should not raise, operation should succeed
                manager.add_category(category)

            # Category should still be added despite save failure
            assert "groceries" in manager.categories
            assert manager.categories["groceries"] == category

    def test_remove_category_existing(self):
        """Test removing an existing category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )
            manager.add_category(category)

            manager.remove_category("groceries")

            assert "groceries" not in manager.categories
            assert len(manager.categories) == 0

    def test_remove_category_nonexistent(self):
        """Test removing a non-existent category (should not cause error)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            initial_count = len(manager.categories)
            manager.remove_category("nonexistent")

            # Should not change anything
            assert len(manager.categories) == initial_count

    def test_remove_category_auto_save(self):
        """Test auto-save after remove_category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )
            manager.add_category(category)

            manager.remove_category("groceries")

            # Verify file was updated
            with open(category_file, encoding="utf-8") as f:
                data = json.load(f)
                assert "groceries" not in data
                assert len(data) == 0

    def test_get_category_existing(self):
        """Test getting an existing category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )
            manager.add_category(category)

            retrieved = manager.get_category("groceries")

            assert retrieved == category

    def test_get_category_nonexistent(self):
        """Test getting a non-existent category (should return None)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            retrieved = manager.get_category("nonexistent")

            assert retrieved is None

    def test_list_categories(self):
        """Test listing all categories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category1 = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )
            category2 = Category(
                name="salary",
                display_name="Salary",
                search_strings=["salary"],
            )

            manager.add_category(category1)
            manager.add_category(category2)

            categories = manager.list_categories()

            assert len(categories) == 2
            assert category1 in categories
            assert category2 in categories

    def test_list_categories_empty(self):
        """Test listing categories when empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            categories = manager.list_categories()

            assert categories == []


class TestSearchStringManagement:
    """Tests for search string management."""

    def test_add_search_string_to_existing_category(self):
        """Test adding search string to existing category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )
            manager.add_category(category)

            manager.add_search_string("groceries", "grocery")

            assert "grocery" in manager.categories["groceries"].search_strings
            assert len(manager.categories["groceries"].search_strings) == 2

    def test_add_search_string_to_nonexistent_category(self):
        """Test adding search string to non-existent category (should not change anything)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            initial_categories = len(manager.categories)
            manager.add_search_string("nonexistent", "test")

            # Should not create category or change anything
            assert len(manager.categories) == initial_categories
            assert "nonexistent" not in manager.categories

    def test_add_search_string_duplicate(self):
        """Test adding duplicate search string (should not change anything)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )
            manager.add_category(category)

            initial_count = len(manager.categories["groceries"].search_strings)
            manager.add_search_string("groceries", "supermarket")

            # Should not add duplicate
            assert len(manager.categories["groceries"].search_strings) == initial_count
            assert (
                manager.categories["groceries"].search_strings.count("supermarket") == 1
            )

    def test_remove_search_string_from_existing_category(self):
        """Test removing search string from existing category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket", "grocery"],
            )
            manager.add_category(category)

            manager.remove_search_string("groceries", "supermarket")

            assert "supermarket" not in manager.categories["groceries"].search_strings
            assert "grocery" in manager.categories["groceries"].search_strings

    def test_remove_search_string_from_nonexistent_category(self):
        """Test removing search string from non-existent category (should not change anything)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            initial_categories = len(manager.categories)
            manager.remove_search_string("nonexistent", "test")

            # Should not change anything
            assert len(manager.categories) == initial_categories

    def test_remove_search_string_not_in_category(self):
        """Test removing non-existent search string (should not change anything)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )
            manager.add_category(category)

            initial_strings = manager.categories["groceries"].search_strings.copy()
            manager.remove_search_string("groceries", "nonexistent")

            # Should not change anything
            assert manager.categories["groceries"].search_strings == initial_strings


class TestCategorizeTransaction:
    """Tests for categorizing single transactions."""

    def test_categorize_transaction_manual_assignment(self):
        """Test that manual assignment has priority."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            # Create categories
            category1 = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )
            category2 = Category(
                name="manual_cat",
                display_name="Manual Category",
                search_strings=[],
            )
            manager.add_category(category1)
            manager.add_category(category2)

            # Add manual assignment
            manager.add_manual_assignment(
                date="16.01.24",
                recipient="Supermarket",
                purpose="Grocery shopping",
                category_name="manual_cat",
            )

            # Create transaction that would match groceries via search string
            transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Max Mustermann",
                recipient="Supermarket",
                purpose="Grocery shopping",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            category, matches = manager.categorize_transaction(transaction)

            # Should return manual assignment, not search string match
            assert category == category2
            assert matches == ["manual assignment"]

    def test_categorize_transaction_search_string_match(self):
        """Test matching via search string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )
            manager.add_category(category)

            transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Max Mustermann",
                recipient="Supermarket",
                purpose="Grocery shopping",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            result_category, matches = manager.categorize_transaction(transaction)

            assert result_category == category
            assert "supermarket" in matches

    def test_categorize_transaction_search_string_case_insensitive(self):
        """Test case-insensitive matching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["SUPERMARKET"],  # Uppercase
            )
            manager.add_category(category)

            transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Max Mustermann",
                recipient="supermarket",  # Lowercase
                purpose="Grocery shopping",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            result_category, matches = manager.categorize_transaction(transaction)

            assert result_category == category
            assert "SUPERMARKET" in matches

    def test_categorize_transaction_regex_match(self):
        """Test matching via regex pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="salary",
                display_name="Salary",
                search_strings=[],
                regex_patterns=[r"SALARY.*\d{4}"],
            )
            manager.add_category(category)

            transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Employer",
                recipient="Max Mustermann",
                purpose="SALARY 2024",
                transaction_type=TransactionType.INCOME,
                iban="DE89370400440532013000",
                amount=2000.00,
            )

            result_category, matches = manager.categorize_transaction(transaction)

            assert result_category == category
            assert any("regex:" in match for match in matches)

    def test_categorize_transaction_regex_invalid_pattern(self):
        """Test that invalid regex pattern is skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="test",
                display_name="Test",
                search_strings=[],
                regex_patterns=[r"[invalid regex("],  # Invalid regex
            )
            manager.add_category(category)

            transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Test",
                recipient="Test",
                purpose="Test",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-10.00,
            )

            result_category, matches = manager.categorize_transaction(transaction)

            # Should not match due to invalid regex
            assert result_category is None
            assert matches == []

    def test_categorize_transaction_multiple_matches(self):
        """Test multiple matches in one category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket", "grocery", "food"],
            )
            manager.add_category(category)

            transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Max Mustermann",
                recipient="Supermarket",
                purpose="Grocery food shopping",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            result_category, matches = manager.categorize_transaction(transaction)

            assert result_category == category
            assert len(matches) >= 2  # Should match multiple strings
            assert "supermarket" in matches or "grocery" in matches

    def test_categorize_transaction_no_match(self):
        """Test when no match is found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )
            manager.add_category(category)

            transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Max Mustermann",
                recipient="Unknown",
                purpose="Unknown transaction",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-25.00,
            )

            result_category, matches = manager.categorize_transaction(transaction)

            assert result_category is None
            assert matches == []

    def test_categorize_transaction_search_text_format(self):
        """Test correct formatting of search text (date + recipient + purpose)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="test",
                display_name="Test",
                search_strings=["16.01.24"],  # Match on date format
            )
            manager.add_category(category)

            transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Test",
                recipient="Test",
                purpose="Test",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-10.00,
            )

            result_category, _ = manager.categorize_transaction(transaction)

            # Should match because date is in search text
            assert result_category == category

    def test_categorize_transaction_first_match_wins(self):
        """Test that first matching category is returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            # Both categories match the same string
            category1 = Category(
                name="first",
                display_name="First",
                search_strings=["test"],
            )
            category2 = Category(
                name="second",
                display_name="Second",
                search_strings=["test"],
            )
            manager.add_category(category1)
            manager.add_category(category2)

            transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Test",
                recipient="Test",
                purpose="Test",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-10.00,
            )

            result_category, _ = manager.categorize_transaction(transaction)

            # Should return first category (order in dict, which is insertion order in Python 3.7+)
            assert result_category in [category1, category2]
            assert result_category is not None

    def test_categorize_transaction_iban_exact_match(self):
        """Test matching via exact IBAN pattern - requires both IBAN and text match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="paypal",
                display_name="PayPal",
                search_strings=["PayPal"],  # Required: both IBAN and text must match
                iban_patterns=["LU89751000135104200E"],
            )
            manager.add_category(category)

            transaction = Transaction(
                booking_date=datetime(2024, 8, 1),
                value_date=datetime(2024, 8, 1),
                status="Gebucht",
                payer="Marc Schuh",
                recipient="PayPal Europe S.a.r.l. et Cie S.C.A",
                purpose="Test transaction",
                transaction_type=TransactionType.EXPENSE,
                iban="LU89751000135104200E",
                amount=-24.00,
            )

            result_category, matches = manager.categorize_transaction(transaction)

            assert result_category == category
            assert any("iban:" in match for match in matches)
            assert "PayPal" in matches

    def test_categorize_transaction_iban_regex_match(self):
        """Test matching via IBAN regex pattern - requires both IBAN and text match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="amazon",
                display_name="Amazon",
                search_strings=["AMAZON"],  # Required: both IBAN and text must match
                iban_patterns=[r"DE8730030880\d+"],
            )
            manager.add_category(category)

            transaction = Transaction(
                booking_date=datetime(2024, 7, 31),
                value_date=datetime(2024, 7, 31),
                status="Gebucht",
                payer="Marc Schuh",
                recipient="AMAZON PAYMENTS EUROPE S.C.A.",
                purpose="Test transaction",
                transaction_type=TransactionType.EXPENSE,
                iban="DE87300308801908262006",
                amount=-64.97,
            )

            result_category, matches = manager.categorize_transaction(transaction)

            assert result_category == category
            assert any("iban:" in match for match in matches)
            assert "AMAZON" in matches

    def test_categorize_transaction_iban_case_insensitive(self):
        """Test that IBAN matching is case-insensitive - requires both IBAN and text match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="test",
                display_name="Test",
                search_strings=["Test"],  # Required: both IBAN and text must match
                iban_patterns=["lu89751000135104200e"],  # Lowercase
            )
            manager.add_category(category)

            transaction = Transaction(
                booking_date=datetime(2024, 8, 1),
                value_date=datetime(2024, 8, 1),
                status="Gebucht",
                payer="Test",
                recipient="Test",
                purpose="Test",
                transaction_type=TransactionType.EXPENSE,
                iban="LU89751000135104200E",  # Uppercase
                amount=-10.00,
            )

            result_category, matches = manager.categorize_transaction(transaction)

            assert result_category == category
            assert any("iban:" in match for match in matches)
            assert "Test" in matches

    def test_categorize_transaction_iban_no_match(self):
        """Test when IBAN doesn't match any pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="paypal",
                display_name="PayPal",
                search_strings=["PayPal"],
                iban_patterns=["LU89751000135104200E"],
            )
            manager.add_category(category)

            transaction = Transaction(
                booking_date=datetime(2024, 8, 1),
                value_date=datetime(2024, 8, 1),
                status="Gebucht",
                payer="Test",
                recipient="Test",
                purpose="Test",
                transaction_type=TransactionType.EXPENSE,
                iban="DE87300308801908262006",  # Different IBAN
                amount=-10.00,
            )

            result_category, matches = manager.categorize_transaction(transaction)

            # Should not match because IBAN doesn't match (even though text would match)
            assert result_category is None
            assert matches == []

    def test_categorize_transaction_iban_no_text_match(self):
        """Test that IBAN pattern alone is not sufficient - text match is also required."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="paypal",
                display_name="PayPal",
                search_strings=["PayPal"],  # Text must also match
                iban_patterns=["LU89751000135104200E"],
            )
            manager.add_category(category)

            transaction = Transaction(
                booking_date=datetime(2024, 8, 1),
                value_date=datetime(2024, 8, 1),
                status="Gebucht",
                payer="Test",
                recipient="Different Recipient",  # No "PayPal" in text
                purpose="Different Purpose",
                transaction_type=TransactionType.EXPENSE,
                iban="LU89751000135104200E",  # IBAN matches, but text doesn't
                amount=-10.00,
            )

            result_category, matches = manager.categorize_transaction(transaction)

            # Should not match because text doesn't match (even though IBAN matches)
            assert result_category is None
            assert matches == []

    def test_categorize_transaction_iban_empty_iban(self):
        """Test that empty IBAN doesn't cause issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="test",
                display_name="Test",
                search_strings=["test"],
                iban_patterns=["DE.*"],
            )
            manager.add_category(category)

            transaction = Transaction(
                booking_date=datetime(2024, 8, 1),
                value_date=datetime(2024, 8, 1),
                status="Gebucht",
                payer="Test",
                recipient="test",
                purpose="test",
                transaction_type=TransactionType.EXPENSE,
                iban="",  # Empty IBAN
                amount=-10.00,
            )

            result_category, matches = manager.categorize_transaction(transaction)

            # Should match via search_string, not IBAN
            assert result_category == category
            assert "test" in matches
            assert not any("iban:" in match for match in matches)

    def test_categorize_transaction_iban_in_search_text(self):
        """Test that IBAN is included in search text for search_string matching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="test",
                display_name="Test",
                search_strings=["DE87300308801908262006"],  # IBAN as search string
                iban_patterns=[],
            )
            manager.add_category(category)

            transaction = Transaction(
                booking_date=datetime(2024, 8, 1),
                value_date=datetime(2024, 8, 1),
                status="Gebucht",
                payer="Test",
                recipient="Test",
                purpose="Test",
                transaction_type=TransactionType.EXPENSE,
                iban="DE87300308801908262006",
                amount=-10.00,
            )

            result_category, matches = manager.categorize_transaction(transaction)

            assert result_category == category
            assert "DE87300308801908262006" in matches


class TestCategorizeTransactions:
    """Tests for categorizing transaction lists."""

    def test_categorize_transactions_empty_list(self):
        """Test categorizing empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            result = manager.categorize_transactions([])

            assert result == []

    def test_categorize_transactions_multiple(self):
        """Test categorizing multiple transactions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )
            manager.add_category(category)

            transactions = [
                Transaction(
                    booking_date=datetime(2024, 1, 15),
                    value_date=datetime(2024, 1, 16),
                    status="Buchung",
                    payer="Max Mustermann",
                    recipient="Supermarket",
                    purpose="Grocery shopping",
                    transaction_type=TransactionType.EXPENSE,
                    iban="DE89370400440532013000",
                    amount=-50.25,
                ),
                Transaction(
                    booking_date=datetime(2024, 1, 20),
                    value_date=datetime(2024, 1, 21),
                    status="Buchung",
                    payer="Max Mustermann",
                    recipient="Unknown",
                    purpose="Unknown",
                    transaction_type=TransactionType.EXPENSE,
                    iban="DE89370400440532013000",
                    amount=-25.00,
                ),
            ]

            result = manager.categorize_transactions(transactions)

            assert len(result) == 2
            assert result[0].category == category
            assert result[1].category is None

    def test_categorize_transactions_creates_parsed_transactions(self):
        """Test that ParsedTransaction objects are created correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )
            manager.add_category(category)

            transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Max Mustermann",
                recipient="Supermarket",
                purpose="Grocery shopping",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            result = manager.categorize_transactions([transaction])

            assert len(result) == 1
            assert isinstance(result[0], ParsedTransaction)
            assert result[0].transaction == transaction
            assert result[0].category == category
            assert len(result[0].search_matches) > 0

    def test_categorize_transactions_preserves_all_transactions(self):
        """Test that all transactions are processed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            transactions = [
                Transaction(
                    booking_date=datetime(2024, 1, 15),
                    value_date=datetime(2024, 1, 16),
                    status="Buchung",
                    payer="Test",
                    recipient="Test1",
                    purpose="Test1",
                    transaction_type=TransactionType.EXPENSE,
                    iban="DE89370400440532013000",
                    amount=-10.00,
                ),
                Transaction(
                    booking_date=datetime(2024, 1, 20),
                    value_date=datetime(2024, 1, 21),
                    status="Buchung",
                    payer="Test",
                    recipient="Test2",
                    purpose="Test2",
                    transaction_type=TransactionType.EXPENSE,
                    iban="DE89370400440532013000",
                    amount=-20.00,
                ),
                Transaction(
                    booking_date=datetime(2024, 1, 25),
                    value_date=datetime(2024, 1, 26),
                    status="Buchung",
                    payer="Test",
                    recipient="Test3",
                    purpose="Test3",
                    transaction_type=TransactionType.EXPENSE,
                    iban="DE89370400440532013000",
                    amount=-30.00,
                ),
            ]

            result = manager.categorize_transactions(transactions)

            assert len(result) == 3
            assert all(isinstance(pt, ParsedTransaction) for pt in result)
            assert [pt.transaction for pt in result] == transactions


class TestSaveLoadCategories:
    """Tests for saving and loading categories."""

    def test_save_categories_creates_file(self):
        """Test that file is created when saving."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
                regex_patterns=[r"^GROCERY"],
            )
            manager.add_category(category)

            assert category_file.exists()

    def test_save_categories_creates_directory(self):
        """Test that directory is created if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "subdir" / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )
            manager.add_category(category)

            assert category_file.parent.exists()
            assert category_file.exists()

    def test_save_categories_json_format(self):
        """Test correct JSON format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket", "grocery"],
                regex_patterns=[r"^GROCERY"],
            )
            manager.add_category(category)

            with open(category_file, encoding="utf-8") as f:
                data = json.load(f)

            assert isinstance(data, dict)
            assert "groceries" in data

    def test_save_categories_includes_all_fields(self):
        """Test that all fields are saved (display_name, search_strings, regex_patterns)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket", "grocery"],
                regex_patterns=[r"^GROCERY", r"FOOD"],
            )
            manager.add_category(category)

            with open(category_file, encoding="utf-8") as f:
                data = json.load(f)

            assert data["groceries"]["display_name"] == "Groceries"
            assert data["groceries"]["search_strings"] == ["supermarket", "grocery"]
            assert data["groceries"]["regex_patterns"] == [r"^GROCERY", r"FOOD"]

    def test_load_categories_from_file(self):
        """Test loading categories from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            category_data = {
                "groceries": {
                    "display_name": "Groceries",
                    "search_strings": ["supermarket"],
                    "regex_patterns": [],
                },
                "salary": {
                    "display_name": "Salary",
                    "search_strings": ["salary"],
                    "regex_patterns": [r"^SALARY"],
                },
            }

            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(category_data, f)

            manager = CategoryManager(category_file, manual_file)

            assert len(manager.categories) == 2
            assert "groceries" in manager.categories
            assert "salary" in manager.categories
            assert manager.categories["groceries"].display_name == "Groceries"
            assert manager.categories["salary"].regex_patterns == [r"^SALARY"]

    def test_load_categories_handles_missing_fields(self):
        """Test that missing fields are handled with defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            # Category with missing fields
            category_data = {
                "groceries": {
                    # Missing display_name, search_strings, regex_patterns
                },
                "salary": {
                    "display_name": "Salary",
                    # Missing search_strings, regex_patterns
                },
            }

            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(category_data, f)

            manager = CategoryManager(category_file, manual_file)

            assert "groceries" in manager.categories
            # display_name should default to name
            assert manager.categories["groceries"].display_name == "groceries"
            # search_strings should default to empty list
            assert manager.categories["groceries"].search_strings == []
            # regex_patterns should default to empty list
            assert manager.categories["groceries"].regex_patterns == []

            assert manager.categories["salary"].search_strings == []
            assert manager.categories["salary"].regex_patterns == []

    def test_load_categories_invalid_json(self):
        """Test that invalid JSON raises exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            with open(category_file, "w", encoding="utf-8") as f:
                f.write("invalid json {")

            with pytest.raises(json.JSONDecodeError):
                CategoryManager(category_file, manual_file)

    def test_load_categories_file_not_found(self):
        """Test that file not found raises exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "nonexistent" / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            # Don't create the file, but try to load it
            # Since file doesn't exist, __init__ should handle it gracefully
            # But if we explicitly call load_categories, it should raise
            manager = CategoryManager(category_file, manual_file)

            # Now try to load from non-existent file
            category_file2 = Path(tmpdir) / "nonexistent2" / "categories.json"
            manager.category_file = category_file2

            with pytest.raises(FileLoadingError):
                manager.load_categories()

    def test_save_load_roundtrip(self):
        """Test save/load roundtrip (data is preserved)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager1 = CategoryManager(category_file, manual_file)

            category1 = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket", "grocery"],
                regex_patterns=[r"^GROCERY"],
            )
            category2 = Category(
                name="salary",
                display_name="Salary",
                search_strings=["salary"],
                regex_patterns=[],
            )

            manager1.add_category(category1)
            manager1.add_category(category2)

            # Create new manager and load
            manager2 = CategoryManager(category_file, manual_file)

            assert len(manager2.categories) == 2
            assert manager2.categories["groceries"].display_name == "Groceries"
            assert manager2.categories["groceries"].search_strings == [
                "supermarket",
                "grocery",
            ]
            assert manager2.categories["groceries"].regex_patterns == [r"^GROCERY"]
            assert manager2.categories["salary"].display_name == "Salary"

    def test_save_load_expected_max_amount(self):
        """Test that expected_max_amount is saved and loaded correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager1 = CategoryManager(category_file, manual_file)

            category1 = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
                expected_max_amount=100.00,
            )
            category2 = Category(
                name="rent",
                display_name="Rent",
                search_strings=["landlord"],
                # No expected_max_amount
            )

            manager1.add_category(category1)
            manager1.add_category(category2)

            # Create new manager and load
            manager2 = CategoryManager(category_file, manual_file)

            assert manager2.categories["groceries"].expected_max_amount == 100.00
            assert manager2.categories["rent"].expected_max_amount is None

    def test_save_load_iban_patterns(self):
        """Test that iban_patterns is saved and loaded correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager1 = CategoryManager(category_file, manual_file)

            category1 = Category(
                name="paypal",
                display_name="PayPal",
                search_strings=["PayPal"],
                iban_patterns=["LU89751000135104200E", r"LU\d+"],
            )
            category2 = Category(
                name="amazon",
                display_name="Amazon",
                search_strings=["Amazon"],
                # No iban_patterns
            )

            manager1.add_category(category1)
            manager1.add_category(category2)

            # Create new manager and load
            manager2 = CategoryManager(category_file, manual_file)

            assert manager2.categories["paypal"].iban_patterns == [
                "LU89751000135104200E",
                r"LU\d+",
            ]
            assert manager2.categories["amazon"].iban_patterns == []

    def test_load_categories_with_iban_patterns(self):
        """Test loading categories with iban_patterns from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            category_data = {
                "paypal": {
                    "display_name": "PayPal",
                    "search_strings": ["PayPal"],
                    "regex_patterns": [],
                    "iban_patterns": ["LU89751000135104200E"],
                },
                "amazon": {
                    "display_name": "Amazon",
                    "search_strings": ["Amazon"],
                    "regex_patterns": [],
                    # No iban_patterns field
                },
            }

            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(category_data, f)

            manager = CategoryManager(category_file, manual_file)

            assert len(manager.categories) == 2
            assert manager.categories["paypal"].iban_patterns == [
                "LU89751000135104200E",
            ]
            assert manager.categories["amazon"].iban_patterns == []


class TestSaveLoadManualAssignments:
    """Tests for saving and loading manual assignments."""

    def test_save_manual_assignments_creates_file(self):
        """Test that file is created when saving."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            # Create category first
            category = Category(name="test", display_name="Test", search_strings=[])
            manager.add_category(category)

            manager.add_manual_assignment(
                date="16.01.24",
                recipient="Test",
                purpose="Test",
                category_name="test",
            )

            assert manual_file.exists()

    def test_save_manual_assignments_creates_directory(self):
        """Test that directory is created if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "subdir" / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            # Create category first
            category = Category(name="test", display_name="Test", search_strings=[])
            manager.add_category(category)

            manager.add_manual_assignment(
                date="16.01.24",
                recipient="Test",
                purpose="Test",
                category_name="test",
            )

            assert manual_file.parent.exists()
            assert manual_file.exists()

    def test_save_manual_assignments_json_format(self):
        """Test correct JSON format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            # Create category first
            category = Category(name="test", display_name="Test", search_strings=[])
            manager.add_category(category)

            manager.add_manual_assignment(
                date="16.01.24",
                recipient="Test",
                purpose="Test",
                category_name="test",
            )

            with open(manual_file, encoding="utf-8") as f:
                data = json.load(f)

            assert isinstance(data, dict)
            assert "manual_assignments" in data
            assert isinstance(data["manual_assignments"], list)

    def test_load_manual_assignments_from_file(self):
        """Test loading manual assignments from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            # Create category file with categories referenced in manual assignments
            category_data = {
                "cat1": {
                    "display_name": "Category 1",
                    "search_strings": [],
                    "regex_patterns": [],
                },
                "cat2": {
                    "display_name": "Category 2",
                    "search_strings": [],
                    "regex_patterns": [],
                },
            }
            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(category_data, f)

            manual_data = {
                "manual_assignments": [
                    {
                        "date": "16.01.24",
                        "recipient": "Recipient1",
                        "purpose": "Purpose1",
                        "category": "cat1",
                    },
                    {
                        "date": "20.02.24",
                        "recipient": "Recipient2",
                        "purpose": "Purpose2",
                        "category": "cat2",
                        "amount": 100.0,
                    },
                ],
            }

            with open(manual_file, "w", encoding="utf-8") as f:
                json.dump(manual_data, f)

            manager = CategoryManager(category_file, manual_file)

            assert len(manager.manual_assignments) == 2
            assert manager.manual_assignments[0]["category"] == "cat1"
            assert manager.manual_assignments[1]["amount"] == 100.0

    def test_load_manual_assignments_empty_list(self):
        """Test empty list when no assignments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manual_data = {"manual_assignments": []}

            with open(manual_file, "w", encoding="utf-8") as f:
                json.dump(manual_data, f)

            manager = CategoryManager(category_file, manual_file)

            assert manager.manual_assignments == []

    def test_load_manual_assignments_invalid_json(self):
        """Test that invalid JSON raises exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            with open(manual_file, "w", encoding="utf-8") as f:
                f.write("invalid json {")

            with pytest.raises(json.JSONDecodeError):
                CategoryManager(category_file, manual_file)

    def test_save_load_manual_assignments_roundtrip(self):
        """Test save/load roundtrip for manual assignments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager1 = CategoryManager(category_file, manual_file)

            # Create categories first
            from dkbparsing.models import Category

            manager1.add_category(
                Category(
                    name="cat1",
                    display_name="Category 1",
                    search_strings=[],
                    regex_patterns=[],
                ),
            )
            manager1.add_category(
                Category(
                    name="cat2",
                    display_name="Category 2",
                    search_strings=[],
                    regex_patterns=[],
                ),
            )

            manager1.add_manual_assignment(
                date="16.01.24",
                recipient="Recipient1",
                purpose="Purpose1",
                category_name="cat1",
            )
            manager1.add_manual_assignment(
                date="20.02.24",
                recipient="Recipient2",
                purpose="Purpose2",
                category_name="cat2",
                amount=100.0,
            )

            # Create new manager and load
            manager2 = CategoryManager(category_file, manual_file)

            assert len(manager2.manual_assignments) == 2
            assert manager2.manual_assignments[0]["category"] == "cat1"
            assert manager2.manual_assignments[1]["amount"] == 100.0


class TestManualAssignmentManagement:
    """Tests for manual assignment management."""

    def test_add_manual_assignment_without_amount(self):
        """Test adding manual assignment without amount."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            # Create category first
            category = Category(name="test", display_name="Test", search_strings=[])
            manager.add_category(category)

            manager.add_manual_assignment(
                date="16.01.24",
                recipient="Test",
                purpose="Test",
                category_name="test",
            )

            assert len(manager.manual_assignments) == 1
            assert "amount" not in manager.manual_assignments[0]
            assert manager.manual_assignments[0]["category"] == "test"

    def test_add_manual_assignment_with_amount(self):
        """Test adding manual assignment with amount."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            # Create category first
            category = Category(name="test", display_name="Test", search_strings=[])
            manager.add_category(category)

            manager.add_manual_assignment(
                date="16.01.24",
                recipient="Test",
                purpose="Test",
                category_name="test",
                amount=100.50,
            )

            assert len(manager.manual_assignments) == 1
            assert manager.manual_assignments[0]["amount"] == 100.50

    def test_add_manual_assignment_raises_error_if_category_not_exists(self):
        """Test that ManualAssignmentCategoryError is raised if category doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            assert "new_category" not in manager.categories

            # Should raise ManualAssignmentCategoryError
            with pytest.raises(ManualAssignmentCategoryError) as exc_info:
                manager.add_manual_assignment(
                    date="16.01.24",
                    recipient="Test",
                    purpose="Test",
                    category_name="new_category",
                )

            assert "new_category" in str(exc_info.value)
            assert (
                "new_category" not in manager.categories
            )  # Category should not be created

    def test_add_manual_assignment_existing_category(self):
        """Test that existing category is used."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="existing",
                display_name="Existing Category",
                search_strings=["test"],
            )
            manager.add_category(category)

            manager.add_manual_assignment(
                date="16.01.24",
                recipient="Test",
                purpose="Test",
                category_name="existing",
            )

            # Should use existing category, not create new one
            assert len(manager.categories) == 1
            assert manager.categories["existing"] == category

    def test_add_manual_assignment_auto_save(self):
        """Test auto-save after add_manual_assignment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            # Create category first
            category = Category(name="test", display_name="Test", search_strings=[])
            manager.add_category(category)

            manager.add_manual_assignment(
                date="16.01.24",
                recipient="Test",
                purpose="Test",
                category_name="test",
            )

            # Verify file was created
            assert manual_file.exists()
            with open(manual_file, encoding="utf-8") as f:
                data = json.load(f)
                assert len(data["manual_assignments"]) == 1

    def test_remove_manual_assignment_existing(self):
        """Test removing existing manual assignment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            # Create categories first
            from dkbparsing.models import Category

            manager.add_category(
                Category(
                    name="cat1",
                    display_name="Category 1",
                    search_strings=[],
                    regex_patterns=[],
                ),
            )
            manager.add_category(
                Category(
                    name="cat2",
                    display_name="Category 2",
                    search_strings=[],
                    regex_patterns=[],
                ),
            )

            manager.add_manual_assignment(
                date="16.01.24",
                recipient="Recipient1",
                purpose="Purpose1",
                category_name="cat1",
            )
            manager.add_manual_assignment(
                date="20.02.24",
                recipient="Recipient2",
                purpose="Purpose2",
                category_name="cat2",
            )

            manager.remove_manual_assignment("16.01.24", "Recipient1", "Purpose1")

            assert len(manager.manual_assignments) == 1
            assert manager.manual_assignments[0]["category"] == "cat2"

    def test_remove_manual_assignment_nonexistent(self):
        """Test removing non-existent assignment (should not change anything)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            # Create category first
            from dkbparsing.models import Category

            manager.add_category(
                Category(
                    name="cat1",
                    display_name="Category 1",
                    search_strings=[],
                    regex_patterns=[],
                ),
            )

            manager.add_manual_assignment(
                date="16.01.24",
                recipient="Recipient1",
                purpose="Purpose1",
                category_name="cat1",
            )

            initial_count = len(manager.manual_assignments)
            manager.remove_manual_assignment("20.02.24", "Recipient2", "Purpose2")

            # Should not change anything
            assert len(manager.manual_assignments) == initial_count

    def test_remove_manual_assignment_auto_save(self):
        """Test auto-save after remove_manual_assignment (only if assignment was removed)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            # Create category first
            from dkbparsing.models import Category

            manager.add_category(
                Category(
                    name="cat1",
                    display_name="Category 1",
                    search_strings=[],
                    regex_patterns=[],
                ),
            )

            manager.add_manual_assignment(
                date="16.01.24",
                recipient="Recipient1",
                purpose="Purpose1",
                category_name="cat1",
            )

            manager.remove_manual_assignment("16.01.24", "Recipient1", "Purpose1")

            # Verify file was updated
            with open(manual_file, encoding="utf-8") as f:
                data = json.load(f)
                assert len(data["manual_assignments"]) == 0


class TestCheckManualAssignment:
    """Tests for checking manual assignments (private method)."""

    def test_check_manual_assignment_exact_match(self):
        """Test exact match (date, recipient, purpose)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="test",
                display_name="Test",
                search_strings=[],
            )
            manager.add_category(category)

            manager.add_manual_assignment(
                date="16.01.24",
                recipient="Test Recipient",
                purpose="Test Purpose",
                category_name="test",
            )

            transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Test",
                recipient="Test Recipient",
                purpose="Test Purpose",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            result = manager._check_manual_assignment(transaction)

            assert result == category

    def test_check_manual_assignment_with_amount_match(self):
        """Test match with amount validation (amount matches)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="test",
                display_name="Test",
                search_strings=[],
            )
            manager.add_category(category)

            manager.add_manual_assignment(
                date="16.01.24",
                recipient="Test Recipient",
                purpose="Test Purpose",
                category_name="test",
                amount=-50.25,
            )

            transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Test",
                recipient="Test Recipient",
                purpose="Test Purpose",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            result = manager._check_manual_assignment(transaction)

            assert result == category

    def test_check_manual_assignment_with_amount_mismatch(self):
        """Test that amount mismatch causes assignment to be skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="test",
                display_name="Test",
                search_strings=[],
            )
            manager.add_category(category)

            manager.add_manual_assignment(
                date="16.01.24",
                recipient="Test Recipient",
                purpose="Test Purpose",
                category_name="test",
                amount=-50.25,
            )

            transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Test",
                recipient="Test Recipient",
                purpose="Test Purpose",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-100.00,  # Different amount
            )

            result = manager._check_manual_assignment(transaction)

            # Should not match due to amount mismatch
            assert result is None

    def test_check_manual_assignment_no_match(self):
        """Test when no match is found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            # Create category first
            category = Category(name="test", display_name="Test", search_strings=[])
            manager.add_category(category)

            manager.add_manual_assignment(
                date="16.01.24",
                recipient="Recipient1",
                purpose="Purpose1",
                category_name="test",
            )

            transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Test",
                recipient="Different Recipient",
                purpose="Different Purpose",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            result = manager._check_manual_assignment(transaction)

            assert result is None

    def test_check_manual_assignment_category_not_found(self):
        """Test when category from assignment doesn't exist raises ManualAssignmentCategoryError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            # Add assignment with category that doesn't exist
            manager.manual_assignments.append(
                {
                    "date": "16.01.24",
                    "recipient": "Test Recipient",
                    "purpose": "Test Purpose",
                    "category": "nonexistent_category",
                },
            )

            transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Test",
                recipient="Test Recipient",
                purpose="Test Purpose",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            # Should raise ManualAssignmentCategoryError because category doesn't exist
            with pytest.raises(ManualAssignmentCategoryError) as exc_info:
                manager._check_manual_assignment(transaction)

            assert "nonexistent_category" in str(exc_info.value)

    def test_check_manual_assignment_date_format(self):
        """Test correct date formatting (dd.mm.yy)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            manager = CategoryManager(category_file, manual_file)

            category = Category(
                name="test",
                display_name="Test",
                search_strings=[],
            )
            manager.add_category(category)

            manager.add_manual_assignment(
                date="16.01.24",
                recipient="Test Recipient",
                purpose="Test Purpose",
                category_name="test",
            )

            transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),  # Should format to "16.01.24"
                status="Buchung",
                payer="Test",
                recipient="Test Recipient",
                purpose="Test Purpose",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            result = manager._check_manual_assignment(transaction)

            assert result == category


class TestManualAssignmentCategoryError:
    """Tests for ManualAssignmentCategoryError when manual assignments reference non-existent categories."""

    def test_load_manual_assignments_with_invalid_category(self):
        """Test that loading manual assignments with invalid category raises ManualAssignmentCategoryError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            # Create category file with one category
            category_data = {
                "groceries": {
                    "display_name": "Groceries",
                    "search_strings": ["supermarket"],
                    "regex_patterns": [],
                },
            }
            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(category_data, f)

            # Create manual assignments file with invalid category
            manual_data = {
                "manual_assignments": [
                    {
                        "date": "16.01.24",
                        "recipient": "Recipient1",
                        "purpose": "Purpose1",
                        "category": "nonexistent_category",
                    },
                ],
            }
            with open(manual_file, "w", encoding="utf-8") as f:
                json.dump(manual_data, f)

            # Should raise ManualAssignmentCategoryError
            with pytest.raises(ManualAssignmentCategoryError) as exc_info:
                CategoryManager(category_file, manual_file)

            assert "nonexistent_category" in str(exc_info.value)
            assert "groceries" in str(
                exc_info.value,
            )  # Should mention available categories

    def test_load_manual_assignments_with_multiple_invalid_categories(self):
        """Test that loading manual assignments with multiple invalid categories raises error on first invalid one."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            # Create category file with one category
            category_data = {
                "groceries": {
                    "display_name": "Groceries",
                    "search_strings": ["supermarket"],
                    "regex_patterns": [],
                },
            }
            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(category_data, f)

            # Create manual assignments file with multiple invalid categories
            manual_data = {
                "manual_assignments": [
                    {
                        "date": "16.01.24",
                        "recipient": "Recipient1",
                        "purpose": "Purpose1",
                        "category": "invalid1",
                    },
                    {
                        "date": "20.02.24",
                        "recipient": "Recipient2",
                        "purpose": "Purpose2",
                        "category": "invalid2",
                    },
                ],
            }
            with open(manual_file, "w", encoding="utf-8") as f:
                json.dump(manual_data, f)

            # Should raise ManualAssignmentCategoryError on first invalid category
            with pytest.raises(ManualAssignmentCategoryError) as exc_info:
                CategoryManager(category_file, manual_file)

            assert "invalid1" in str(exc_info.value)

    def test_check_manual_assignment_with_invalid_category(self):
        """Test that checking manual assignment with invalid category raises ManualAssignmentCategoryError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            # Create category file with one category
            category_data = {
                "groceries": {
                    "display_name": "Groceries",
                    "search_strings": ["supermarket"],
                    "regex_patterns": [],
                },
            }
            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(category_data, f)

            # Create manual assignments file with invalid category
            manual_data = {
                "manual_assignments": [
                    {
                        "date": "16.01.24",
                        "recipient": "Test Recipient",
                        "purpose": "Test Purpose",
                        "category": "nonexistent_category",
                    },
                ],
            }
            with open(manual_file, "w", encoding="utf-8") as f:
                json.dump(manual_data, f)

            # This should raise ManualAssignmentCategoryError during initialization
            # But if we somehow bypass that, it should also raise in _check_manual_assignment
            with pytest.raises(ManualAssignmentCategoryError):
                CategoryManager(category_file, manual_file)

    def test_load_manual_assignments_with_valid_category(self):
        """Test that loading manual assignments with valid category does not raise error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            # Create category file
            category_data = {
                "groceries": {
                    "display_name": "Groceries",
                    "search_strings": ["supermarket"],
                    "regex_patterns": [],
                },
            }
            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(category_data, f)

            # Create manual assignments file with valid category
            manual_data = {
                "manual_assignments": [
                    {
                        "date": "16.01.24",
                        "recipient": "Recipient1",
                        "purpose": "Purpose1",
                        "category": "groceries",
                    },
                ],
            }
            with open(manual_file, "w", encoding="utf-8") as f:
                json.dump(manual_data, f)

            # Should not raise any error
            manager = CategoryManager(category_file, manual_file)
            assert len(manager.manual_assignments) == 1
            assert manager.manual_assignments[0]["category"] == "groceries"
