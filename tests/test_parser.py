"""Unit tests for parser.py."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from dkbparsing.models import (
    Category,
    ParsedTransaction,
    ParsingResult,
    Transaction,
    TransactionType,
)
from dkbparsing.parser import DKBParser


class TestDKBParserInitialization:
    """Tests for DKBParser initialization."""

    def test_init_creates_components(self):
        """Test that initialization creates all required components."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            assert parser.csv_parser is not None
            assert parser.category_manager is not None
            assert parser.excel_formatter is not None
            assert parser.summary_formatter is not None

    def test_init_passes_files_to_category_manager(self):
        """Test that files are passed to CategoryManager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            with patch("dkbparsing.parser.CategoryManager") as mock_cm:
                DKBParser(category_file, manual_file)

                mock_cm.assert_called_once_with(category_file, manual_file)


class TestDKBParserParseFile:
    """Tests for parse_file method."""

    def test_parse_file_basic(self):
        """Test basic parsing without date filters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            # Mock CSV parser
            mock_transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Test",
                recipient="Supermarket",
                purpose="Grocery shopping",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            parser.csv_parser.parse_file = Mock(return_value=[mock_transaction])
            parser.csv_parser.filter_by_date_range = Mock()

            # Mock category manager
            mock_category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )

            mock_parsed = ParsedTransaction(
                transaction=mock_transaction,
                category=mock_category,
                search_matches=["supermarket"],
            )

            parser.category_manager.categorize_transactions = Mock(
                return_value=[mock_parsed],
            )

            result = parser.parse_file("test.csv")

            assert isinstance(result, ParsingResult)
            assert len(result.parsed_transactions) == 1
            assert result.parsed_transactions[0] == mock_parsed
            parser.csv_parser.parse_file.assert_called_once_with("test.csv")
            parser.csv_parser.filter_by_date_range.assert_not_called()

    def test_parse_file_with_date_filter(self):
        """Test parsing with date filters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            mock_transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Test",
                recipient="Supermarket",
                purpose="Grocery shopping",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            filtered_transaction = Transaction(
                booking_date=datetime(2024, 1, 20),
                value_date=datetime(2024, 1, 21),
                status="Buchung",
                payer="Test",
                recipient="Test",
                purpose="Test",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-25.00,
            )

            parser.csv_parser.parse_file = Mock(return_value=[mock_transaction])
            parser.csv_parser.filter_by_date_range = Mock(
                return_value=[filtered_transaction],
            )

            mock_category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )

            mock_parsed = ParsedTransaction(
                transaction=filtered_transaction,
                category=mock_category,
            )

            parser.category_manager.categorize_transactions = Mock(
                return_value=[mock_parsed],
            )

            start_date = datetime(2024, 1, 1)
            end_date = datetime(2024, 1, 31)

            parser.parse_file("test.csv", start_date, end_date)

            parser.csv_parser.filter_by_date_range.assert_called_once_with(
                [mock_transaction],
                start_date,
                end_date,
            )
            parser.category_manager.categorize_transactions.assert_called_once_with(
                [filtered_transaction],
            )

    def test_parse_file_calculates_category_totals(self):
        """Test that category totals are calculated correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            transaction1 = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Test",
                recipient="Supermarket",
                purpose="Grocery shopping",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            transaction2 = Transaction(
                booking_date=datetime(2024, 1, 20),
                value_date=datetime(2024, 1, 21),
                status="Buchung",
                payer="Test",
                recipient="Supermarket",
                purpose="More groceries",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-30.00,
            )

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )

            parsed1 = ParsedTransaction(transaction=transaction1, category=category)
            parsed2 = ParsedTransaction(transaction=transaction2, category=category)

            parser.csv_parser.parse_file = Mock(
                return_value=[transaction1, transaction2],
            )
            parser.csv_parser.filter_by_date_range = Mock()
            parser.category_manager.categorize_transactions = Mock(
                return_value=[parsed1, parsed2],
            )

            result = parser.parse_file("test.csv")

            assert result.category_totals["Groceries"] == -80.25

    def test_parse_file_calculates_income_expenses(self):
        """Test that income and expenses are calculated correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            income_transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Employer",
                recipient="Test",
                purpose="Salary",
                transaction_type=TransactionType.INCOME,
                iban="DE89370400440532013000",
                amount=2000.00,
            )

            expense_transaction = Transaction(
                booking_date=datetime(2024, 1, 20),
                value_date=datetime(2024, 1, 21),
                status="Buchung",
                payer="Test",
                recipient="Supermarket",
                purpose="Grocery shopping",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )

            parsed_income = ParsedTransaction(
                transaction=income_transaction,
                category=None,
            )
            parsed_expense = ParsedTransaction(
                transaction=expense_transaction,
                category=category,
            )

            parser.csv_parser.parse_file = Mock(
                return_value=[income_transaction, expense_transaction],
            )
            parser.csv_parser.filter_by_date_range = Mock()
            parser.category_manager.categorize_transactions = Mock(
                return_value=[parsed_income, parsed_expense],
            )

            result = parser.parse_file("test.csv")

            assert result.total_income == 2000.00
            assert result.total_expenses == -50.25

    def test_parse_file_separates_uncategorized(self):
        """Test that uncategorized transactions are separated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            categorized_transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Test",
                recipient="Supermarket",
                purpose="Grocery shopping",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            uncategorized_transaction = Transaction(
                booking_date=datetime(2024, 1, 20),
                value_date=datetime(2024, 1, 21),
                status="Buchung",
                payer="Test",
                recipient="Unknown",
                purpose="Unknown",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-25.00,
            )

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )

            parsed_categorized = ParsedTransaction(
                transaction=categorized_transaction,
                category=category,
            )
            parsed_uncategorized = ParsedTransaction(
                transaction=uncategorized_transaction,
                category=None,
            )

            parser.csv_parser.parse_file = Mock(
                return_value=[categorized_transaction, uncategorized_transaction],
            )
            parser.csv_parser.filter_by_date_range = Mock()
            parser.category_manager.categorize_transactions = Mock(
                return_value=[parsed_categorized, parsed_uncategorized],
            )

            result = parser.parse_file("test.csv")

            assert len(result.uncategorized_transactions) == 1
            assert result.uncategorized_transactions[0] == uncategorized_transaction
            assert len(result.parsed_transactions) == 2

    def test_parse_file_empty_transactions(self):
        """Test parsing with empty transaction list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            parser.csv_parser.parse_file = Mock(return_value=[])
            parser.csv_parser.filter_by_date_range = Mock()
            parser.category_manager.categorize_transactions = Mock(return_value=[])

            result = parser.parse_file("test.csv")

            assert len(result.parsed_transactions) == 0
            assert len(result.uncategorized_transactions) == 0
            assert result.category_totals == {}
            assert result.total_income == 0.0
            assert result.total_expenses == 0.0

    def test_parse_file_only_start_date_no_filter(self):
        """Test that only start_date without end_date doesn't filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            mock_transaction = Transaction(
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

            parser.csv_parser.parse_file = Mock(return_value=[mock_transaction])
            parser.csv_parser.filter_by_date_range = Mock()

            parser.category_manager.categorize_transactions = Mock(return_value=[])

            parser.parse_file("test.csv", start_date=datetime(2024, 1, 1))

            # Should not call filter_by_date_range if end_date is missing
            parser.csv_parser.filter_by_date_range.assert_not_called()

    def test_parse_file_only_end_date_no_filter(self):
        """Test that only end_date without start_date doesn't filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            mock_transaction = Transaction(
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

            parser.csv_parser.parse_file = Mock(return_value=[mock_transaction])
            parser.csv_parser.filter_by_date_range = Mock()

            parser.category_manager.categorize_transactions = Mock(return_value=[])

            _ = parser.parse_file("test.csv", end_date=datetime(2024, 1, 31))

            # Should not call filter_by_date_range if start_date is missing
            parser.csv_parser.filter_by_date_range.assert_not_called()


class TestDKBParserCategoryManagement:
    """Tests for category management delegation methods."""

    def test_add_category(self):
        """Test that add_category delegates to CategoryManager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            parser.category_manager.add_category = Mock()

            parser.add_category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
                regex_patterns=[r"^GROCERY"],
            )

            parser.category_manager.add_category.assert_called_once()
            call_args = parser.category_manager.add_category.call_args[0][0]
            assert call_args.name == "groceries"
            assert call_args.display_name == "Groceries"
            assert call_args.search_strings == ["supermarket"]
            assert call_args.regex_patterns == [r"^GROCERY"]

    def test_add_category_with_none_values(self):
        """Test that add_category handles None values correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            parser.category_manager.add_category = Mock()

            parser.add_category(
                name="test",
                display_name="Test",
                search_strings=None,
                regex_patterns=None,
            )

            parser.category_manager.add_category.assert_called_once()
            call_args = parser.category_manager.add_category.call_args[0][0]
            assert call_args.search_strings == []
            assert call_args.regex_patterns == []

    def test_add_search_string(self):
        """Test that add_search_string delegates to CategoryManager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            parser.category_manager.add_search_string = Mock()

            parser.add_search_string("groceries", "supermarket")

            parser.category_manager.add_search_string.assert_called_once_with(
                "groceries",
                "supermarket",
            )

    def test_remove_search_string(self):
        """Test that remove_search_string delegates to CategoryManager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            parser.category_manager.remove_search_string = Mock()

            parser.remove_search_string("groceries", "supermarket")

            parser.category_manager.remove_search_string.assert_called_once_with(
                "groceries",
                "supermarket",
            )


class TestDKBParserManualAssignments:
    """Tests for manual assignment delegation methods."""

    def test_add_manual_assignment(self):
        """Test that add_manual_assignment delegates to CategoryManager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            parser.category_manager.add_manual_assignment = Mock()

            parser.add_manual_assignment(
                date="16.01.24",
                recipient="Test",
                purpose="Test",
                category_name="test",
                amount=100.50,
            )

            parser.category_manager.add_manual_assignment.assert_called_once_with(
                "16.01.24",
                "Test",
                "Test",
                "test",
                100.50,
            )

    def test_add_manual_assignment_without_amount(self):
        """Test that add_manual_assignment works without amount."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            parser.category_manager.add_manual_assignment = Mock()

            parser.add_manual_assignment(
                date="16.01.24",
                recipient="Test",
                purpose="Test",
                category_name="test",
            )

            parser.category_manager.add_manual_assignment.assert_called_once_with(
                "16.01.24",
                "Test",
                "Test",
                "test",
                None,
            )

    def test_remove_manual_assignment(self):
        """Test that remove_manual_assignment delegates to CategoryManager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            parser.category_manager.remove_manual_assignment = Mock()

            parser.remove_manual_assignment("16.01.24", "Test", "Test")

            parser.category_manager.remove_manual_assignment.assert_called_once_with(
                "16.01.24",
                "Test",
                "Test",
            )


class TestDKBParserFormatting:
    """Tests for formatting delegation methods."""

    def test_format_for_excel(self):
        """Test that format_for_excel delegates to ExcelFormatter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            mock_result = ParsingResult(
                parsed_transactions=[],
                uncategorized_transactions=[],
                category_totals={},
                total_income=0.0,
                total_expenses=0.0,
            )

            parser.excel_formatter.format_for_excel = Mock(return_value="formatted")

            result = parser.format_for_excel(mock_result)

            parser.excel_formatter.format_for_excel.assert_called_once_with(mock_result)
            assert result == "formatted"

    def test_format_for_excel_with_category_order(self):
        """Test that format_for_excel sets category_order if provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            mock_result = ParsingResult(
                parsed_transactions=[],
                uncategorized_transactions=[],
                category_totals={},
                total_income=0.0,
                total_expenses=0.0,
            )

            category_order = ["Groceries", "Salary"]
            parser.excel_formatter.format_for_excel = Mock(return_value="formatted")

            parser.format_for_excel(mock_result, category_order)

            assert parser.excel_formatter.category_order == category_order
            parser.excel_formatter.format_for_excel.assert_called_once_with(mock_result)

    def test_format_summary(self):
        """Test that format_summary delegates to SummaryFormatter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            mock_result = ParsingResult(
                parsed_transactions=[],
                uncategorized_transactions=[],
                category_totals={},
                total_income=0.0,
                total_expenses=0.0,
            )

            parser.summary_formatter.format_summary = Mock(return_value="summary")

            result = parser.format_summary(mock_result)

            parser.summary_formatter.format_summary.assert_called_once_with(mock_result)
            assert result == "summary"

    def test_format_household(self):
        """Test that format_household delegates to HouseholdFormatter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            mock_result = ParsingResult(
                parsed_transactions=[],
                uncategorized_transactions=[],
                category_totals={},
                total_income=0.0,
                total_expenses=0.0,
            )

            template_file = str(Path(tmpdir) / "template.txt")

            with patch("dkbparsing.parser.HouseholdFormatter") as mock_hf_class:
                mock_formatter = Mock()
                mock_formatter.format_household_output = Mock(return_value="household")
                mock_hf_class.return_value = mock_formatter

                result = parser.format_household(mock_result, template_file)

                mock_hf_class.assert_called_once_with(template_file)
                mock_formatter.format_household_output.assert_called_once_with(
                    mock_result,
                )
                assert result == "household"


class TestDKBParserCalculateCategoryTotals:
    """Tests for _calculate_category_totals private method."""

    def test_calculate_category_totals_single_category(self):
        """Test calculating totals for a single category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            transaction1 = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Test",
                recipient="Supermarket",
                purpose="Grocery shopping",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            transaction2 = Transaction(
                booking_date=datetime(2024, 1, 20),
                value_date=datetime(2024, 1, 21),
                status="Buchung",
                payer="Test",
                recipient="Supermarket",
                purpose="More groceries",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-30.00,
            )

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )

            parsed1 = ParsedTransaction(transaction=transaction1, category=category)
            parsed2 = ParsedTransaction(transaction=transaction2, category=category)

            totals = parser._calculate_category_totals([parsed1, parsed2])

            assert totals == {"Groceries": -80.25}

    def test_calculate_category_totals_multiple_categories(self):
        """Test calculating totals for multiple categories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            transaction1 = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Test",
                recipient="Supermarket",
                purpose="Grocery shopping",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            transaction2 = Transaction(
                booking_date=datetime(2024, 1, 20),
                value_date=datetime(2024, 1, 21),
                status="Buchung",
                payer="Employer",
                recipient="Test",
                purpose="Salary",
                transaction_type=TransactionType.INCOME,
                iban="DE89370400440532013000",
                amount=2000.00,
            )

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

            parsed1 = ParsedTransaction(transaction=transaction1, category=category1)
            parsed2 = ParsedTransaction(transaction=transaction2, category=category2)

            totals = parser._calculate_category_totals([parsed1, parsed2])

            assert totals == {"Groceries": -50.25, "Salary": 2000.00}

    def test_calculate_category_totals_ignores_uncategorized(self):
        """Test that uncategorized transactions are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            categorized_transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Test",
                recipient="Supermarket",
                purpose="Grocery shopping",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            uncategorized_transaction = Transaction(
                booking_date=datetime(2024, 1, 20),
                value_date=datetime(2024, 1, 21),
                status="Buchung",
                payer="Test",
                recipient="Unknown",
                purpose="Unknown",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-25.00,
            )

            category = Category(
                name="groceries",
                display_name="Groceries",
                search_strings=["supermarket"],
            )

            parsed1 = ParsedTransaction(
                transaction=categorized_transaction,
                category=category,
            )
            parsed2 = ParsedTransaction(
                transaction=uncategorized_transaction,
                category=None,
            )

            totals = parser._calculate_category_totals([parsed1, parsed2])

            assert totals == {"Groceries": -50.25}
            assert len(totals) == 1

    def test_calculate_category_totals_empty_list(self):
        """Test calculating totals for empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            totals = parser._calculate_category_totals([])

            assert totals == {}


class TestDKBParserCalculateIncomeExpenses:
    """Tests for _calculate_income_expenses private method."""

    def test_calculate_income_expenses_positive_amounts(self):
        """Test calculating income from positive amounts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            transaction1 = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Employer",
                recipient="Test",
                purpose="Salary",
                transaction_type=TransactionType.INCOME,
                iban="DE89370400440532013000",
                amount=2000.00,
            )

            transaction2 = Transaction(
                booking_date=datetime(2024, 1, 20),
                value_date=datetime(2024, 1, 21),
                status="Buchung",
                payer="Client",
                recipient="Test",
                purpose="Payment",
                transaction_type=TransactionType.INCOME,
                iban="DE89370400440532013000",
                amount=500.00,
            )

            parsed1 = ParsedTransaction(transaction=transaction1, category=None)
            parsed2 = ParsedTransaction(transaction=transaction2, category=None)

            income, expenses = parser._calculate_income_expenses([parsed1, parsed2])

            assert income == 2500.00
            assert expenses == 0.0

    def test_calculate_income_expenses_negative_amounts(self):
        """Test calculating expenses from negative amounts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            transaction1 = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Test",
                recipient="Supermarket",
                purpose="Grocery shopping",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            transaction2 = Transaction(
                booking_date=datetime(2024, 1, 20),
                value_date=datetime(2024, 1, 21),
                status="Buchung",
                payer="Test",
                recipient="Store",
                purpose="Purchase",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-30.00,
            )

            parsed1 = ParsedTransaction(transaction=transaction1, category=None)
            parsed2 = ParsedTransaction(transaction=transaction2, category=None)

            income, expenses = parser._calculate_income_expenses([parsed1, parsed2])

            assert income == 0.0
            assert expenses == -80.25

    def test_calculate_income_expenses_mixed(self):
        """Test calculating income and expenses from mixed amounts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            income_transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Employer",
                recipient="Test",
                purpose="Salary",
                transaction_type=TransactionType.INCOME,
                iban="DE89370400440532013000",
                amount=2000.00,
            )

            expense_transaction = Transaction(
                booking_date=datetime(2024, 1, 20),
                value_date=datetime(2024, 1, 21),
                status="Buchung",
                payer="Test",
                recipient="Supermarket",
                purpose="Grocery shopping",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            )

            parsed1 = ParsedTransaction(transaction=income_transaction, category=None)
            parsed2 = ParsedTransaction(transaction=expense_transaction, category=None)

            income, expenses = parser._calculate_income_expenses([parsed1, parsed2])

            assert income == 2000.00
            assert expenses == -50.25

    def test_calculate_income_expenses_zero_amount(self):
        """Test that zero amount is treated as income."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            transaction = Transaction(
                booking_date=datetime(2024, 1, 15),
                value_date=datetime(2024, 1, 16),
                status="Buchung",
                payer="Test",
                recipient="Test",
                purpose="Test",
                transaction_type=TransactionType.INCOME,
                iban="DE89370400440532013000",
                amount=0.0,
            )

            parsed = ParsedTransaction(transaction=transaction, category=None)

            income, expenses = parser._calculate_income_expenses([parsed])

            assert income == 0.0
            assert expenses == 0.0

    def test_calculate_income_expenses_empty_list(self):
        """Test calculating income/expenses for empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"

            parser = DKBParser(category_file, manual_file)

            income, expenses = parser._calculate_income_expenses([])

            assert income == 0.0
            assert expenses == 0.0
