"""Unit tests for output_formatter.py."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from dkbparsing.models import (
    Category,
    ParsedTransaction,
    ParsingResult,
    Transaction,
    TransactionType,
)
from dkbparsing.output_formatter import (
    ExcelFormatter,
    HouseholdFormatter,
    SummaryFormatter,
    TransactionHiddenError,
)


class TestExcelFormatter:
    """Tests for ExcelFormatter class."""

    def test_init_without_category_order(self):
        """Test ExcelFormatter initialization without category order."""
        formatter = ExcelFormatter()
        assert formatter.category_order == []

    def test_init_with_category_order(self):
        """Test ExcelFormatter initialization with category order."""
        order = ["Groceries", "Salary", "Rent"]
        formatter = ExcelFormatter(category_order=order)
        assert formatter.category_order == order

    def test_format_for_excel_basic(self):
        """Test basic Excel formatting."""
        booking_date = datetime(2024, 1, 15)
        value_date = datetime(2024, 1, 16)

        transaction = Transaction(
            booking_date=booking_date,
            value_date=value_date,
            status="Buchung",
            payer="Max Mustermann",
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

        parsed_transaction = ParsedTransaction(
            transaction=transaction,
            category=category,
        )

        result = ParsingResult(
            parsed_transactions=[parsed_transaction],
            uncategorized_transactions=[],
            category_totals={"Groceries": -50.25},
            total_income=0.0,
            total_expenses=-50.25,
        )

        formatter = ExcelFormatter()
        output = formatter.format_for_excel(result)

        assert "All catagorized transactions:" in output
        assert "Groceries: -50,25" in output

    def test_format_for_excel_with_uncategorized(self):
        """Test Excel formatting with uncategorized transactions."""
        booking_date = datetime(2024, 1, 15)
        value_date = datetime(2024, 1, 16)

        uncategorized = Transaction(
            booking_date=booking_date,
            value_date=value_date,
            status="Buchung",
            payer="Max Mustermann",
            recipient="Unknown",
            purpose="Unknown transaction",
            transaction_type=TransactionType.EXPENSE,
            iban="DE89370400440532013000",
            amount=-25.00,
        )

        result = ParsingResult(
            parsed_transactions=[],
            uncategorized_transactions=[uncategorized],
            category_totals={},
            total_income=0.0,
            total_expenses=-25.00,
        )

        formatter = ExcelFormatter()
        output = formatter.format_for_excel(result, show_uncategorized=True)

        assert "Uncategorized transactions:" in output
        assert "16.01.24" in output
        assert "Unknown" in output
        assert "Unknown transaction" in output
        assert "-25,0" in output

    def test_format_for_excel_hide_uncategorized(self):
        """Test Excel formatting with uncategorized transactions hidden."""
        booking_date = datetime(2024, 1, 15)
        value_date = datetime(2024, 1, 16)

        uncategorized = Transaction(
            booking_date=booking_date,
            value_date=value_date,
            status="Buchung",
            payer="Max Mustermann",
            recipient="Unknown",
            purpose="Unknown transaction",
            transaction_type=TransactionType.EXPENSE,
            iban="DE89370400440532013000",
            amount=-25.00,
        )

        result = ParsingResult(
            parsed_transactions=[],
            uncategorized_transactions=[uncategorized],
            category_totals={},
            total_income=0.0,
            total_expenses=-25.00,
        )

        formatter = ExcelFormatter()
        output = formatter.format_for_excel(result, show_uncategorized=False)

        assert "Uncategorized transactions:" not in output

    def test_format_for_excel_hide_totals(self):
        """Test Excel formatting with totals hidden."""
        booking_date = datetime(2024, 1, 15)
        value_date = datetime(2024, 1, 16)

        transaction = Transaction(
            booking_date=booking_date,
            value_date=value_date,
            status="Buchung",
            payer="Max Mustermann",
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

        parsed_transaction = ParsedTransaction(
            transaction=transaction,
            category=category,
        )

        result = ParsingResult(
            parsed_transactions=[parsed_transaction],
            uncategorized_transactions=[],
            category_totals={"Groceries": -50.25},
            total_income=0.0,
            total_expenses=-50.25,
        )

        formatter = ExcelFormatter()
        output = formatter.format_for_excel(result, show_totals=False)

        assert "All catagorized transactions:" in output
        assert "Groceries: -50,25" not in output

    def test_format_category_totals(self):
        """Test formatting category totals."""
        result = ParsingResult(
            parsed_transactions=[],
            uncategorized_transactions=[],
            category_totals={
                "Groceries": -50.25,
                "Salary": 2000.00,
                "Rent": -800.00,
            },
            total_income=2000.00,
            total_expenses=-850.25,
        )

        formatter = ExcelFormatter()
        lines = formatter._format_category_totals(result)

        assert "Groceries: -50,25" in lines
        assert "Salary: 2000,0" in lines
        assert "Rent: -800,0" in lines

    def test_format_category_totals_with_zero(self):
        """Test formatting category totals with zero amounts."""
        result = ParsingResult(
            parsed_transactions=[],
            uncategorized_transactions=[],
            category_totals={
                "Groceries": -50.25,
                "Empty": 0.0,
            },
            total_income=0.0,
            total_expenses=-50.25,
        )

        formatter = ExcelFormatter()
        lines = formatter._format_category_totals(result)

        assert "Groceries: -50,25" in lines
        assert "" in lines  # Empty line for zero amount

    def test_format_uncategorized(self):
        """Test formatting uncategorized transactions."""
        booking_date = datetime(2024, 1, 15)
        value_date1 = datetime(2024, 1, 16)
        value_date2 = datetime(2024, 1, 17)

        transaction1 = Transaction(
            booking_date=booking_date,
            value_date=value_date1,
            status="Buchung",
            payer="Max Mustermann",
            recipient="Unknown1",
            purpose="Transaction 1",
            transaction_type=TransactionType.EXPENSE,
            iban="DE89370400440532013000",
            amount=-25.00,
        )

        transaction2 = Transaction(
            booking_date=booking_date,
            value_date=value_date2,
            status="Buchung",
            payer="Max Mustermann",
            recipient="Unknown2",
            purpose="Transaction 2",
            transaction_type=TransactionType.INCOME,
            iban="DE89370400440532013000",
            amount=100.50,
        )

        formatter = ExcelFormatter()
        lines = formatter._format_uncategorized([transaction1, transaction2])

        assert lines[0] == ""  # Empty line separator
        assert lines[1] == "Uncategorized transactions:"
        assert "16.01.24" in lines[2]
        assert "Unknown1" in lines[2]
        assert "-25,0" in lines[2]
        assert "17.01.24" in lines[3]
        assert "Unknown2" in lines[3]
        assert "100,5" in lines[3]

    def test_sort_categories_with_order(self):
        """Test sorting categories with predefined order."""
        category_totals = {
            "Rent": -800.00,
            "Groceries": -50.25,
            "Salary": 2000.00,
            "Utilities": -100.00,
        }

        formatter = ExcelFormatter(category_order=["Salary", "Rent", "Groceries"])
        sorted_categories = formatter._sort_categories(category_totals)

        assert sorted_categories[0] == "Salary"
        assert sorted_categories[1] == "Rent"
        assert sorted_categories[2] == "Groceries"
        assert sorted_categories[3] == "Utilities"  # Alphabetically sorted

    def test_sort_categories_without_order(self):
        """Test sorting categories without predefined order (alphabetical)."""
        category_totals = {
            "Rent": -800.00,
            "Groceries": -50.25,
            "Salary": 2000.00,
        }

        formatter = ExcelFormatter()
        sorted_categories = formatter._sort_categories(category_totals)

        assert sorted_categories == ["Groceries", "Rent", "Salary"]

    def test_sort_categories_partial_order(self):
        """Test sorting categories with partial order (some categories not in order)."""
        category_totals = {
            "Rent": -800.00,
            "Groceries": -50.25,
            "Salary": 2000.00,
            "Utilities": -100.00,
        }

        formatter = ExcelFormatter(category_order=["Salary"])
        sorted_categories = formatter._sort_categories(category_totals)

        assert sorted_categories[0] == "Salary"
        # Rest should be alphabetically sorted
        assert "Groceries" in sorted_categories[1:4]
        assert "Rent" in sorted_categories[1:4]
        assert "Utilities" in sorted_categories[1:4]

    def test_format_amount(self):
        """Test formatting amounts for German Excel."""
        formatter = ExcelFormatter()

        assert formatter._format_amount(100.50) == "100,5"
        assert formatter._format_amount(-50.25) == "-50,25"
        assert formatter._format_amount(0.0) == "0,0"
        assert formatter._format_amount(1234.56) == "1234,56"
        assert formatter._format_amount(-0.01) == "-0,01"


class TestHouseholdFormatter:
    """Tests for HouseholdFormatter class."""

    def test_init_with_valid_template(self):
        """Test HouseholdFormatter initialization with valid template file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("Groceries\n")
            f.write("Salary\n")
            f.write("Rent\n")
            template_path = f.name

        try:
            formatter = HouseholdFormatter(template_path)
            assert formatter.template_file == template_path
            assert len(formatter.template_lines) == 3
            assert formatter.template_lines[0].strip() == "Groceries"
        finally:
            Path(template_path).unlink()

    def test_init_with_missing_template(self):
        """Test HouseholdFormatter initialization with missing template file."""
        with pytest.raises(ValueError, match="Template file not found"):
            HouseholdFormatter("/nonexistent/path/template.txt")

    def test_format_household_output_exact_match(self):
        """Test household formatting with exact category name matches."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("Groceries\n")
            f.write("Salary\n")
            f.write("Rent\n")
            template_path = f.name

        try:
            result = ParsingResult(
                parsed_transactions=[],
                uncategorized_transactions=[],
                category_totals={
                    "Groceries": -50.25,
                    "Salary": 2000.00,
                    "Rent": -800.00,
                },
                total_income=2000.00,
                total_expenses=-850.25,
            )

            formatter = HouseholdFormatter(template_path)
            output = formatter.format_household_output(result)

            lines = output.split("\n")
            assert lines[0] == "-50,25"
            assert lines[1] == "2000,0"
            assert lines[2] == "-800,0"
        finally:
            Path(template_path).unlink()

    def test_format_household_output_case_insensitive(self):
        """Test household formatting with case-insensitive matching."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("groceries\n")  # lowercase in template
            f.write("SALARY\n")  # uppercase in template
            template_path = f.name

        try:
            result = ParsingResult(
                parsed_transactions=[],
                uncategorized_transactions=[],
                category_totals={
                    "Groceries": -50.25,  # Title case in result
                    "Salary": 2000.00,  # Title case in result
                },
                total_income=2000.00,
                total_expenses=-50.25,
            )

            formatter = HouseholdFormatter(template_path)
            output = formatter.format_household_output(result)

            lines = output.split("\n")
            assert lines[0] == "-50,25"
            assert lines[1] == "2000,0"
        finally:
            Path(template_path).unlink()

    def test_format_household_output_missing_category(self):
        """Test household formatting with missing categories in result."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("Groceries\n")
            f.write("MissingCategory\n")
            f.write("Salary\n")
            template_path = f.name

        try:
            result = ParsingResult(
                parsed_transactions=[],
                uncategorized_transactions=[],
                category_totals={
                    "Groceries": -50.25,
                    "Salary": 2000.00,
                },
                total_income=2000.00,
                total_expenses=-50.25,
            )

            formatter = HouseholdFormatter(template_path)
            output = formatter.format_household_output(result)

            lines = output.split("\n")
            assert lines[0] == "-50,25"
            assert lines[1] == ""  # Missing category should be empty
            assert lines[2] == "2000,0"
        finally:
            Path(template_path).unlink()

    def test_format_household_output_empty_lines(self):
        """Test household formatting with empty lines in template."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("Groceries\n")
            f.write("\n")  # Empty line
            f.write("Salary\n")
            template_path = f.name

        try:
            result = ParsingResult(
                parsed_transactions=[],
                uncategorized_transactions=[],
                category_totals={
                    "Groceries": -50.25,
                    "Salary": 2000.00,
                },
                total_income=2000.00,
                total_expenses=-50.25,
            )

            formatter = HouseholdFormatter(template_path)
            output = formatter.format_household_output(result)

            lines = output.split("\n")
            assert lines[0] == "-50,25"
            assert lines[1] == ""  # Empty line preserved
            assert lines[2] == "2000,0"
        finally:
            Path(template_path).unlink()

    def test_format_household_output_zero_amounts(self):
        """Test household formatting with zero amounts."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("Groceries\n")
            f.write("ZeroCategory\n")
            template_path = f.name

        try:
            result = ParsingResult(
                parsed_transactions=[],
                uncategorized_transactions=[],
                category_totals={
                    "Groceries": -50.25,
                    "ZeroCategory": 0.0,
                },
                total_income=0.0,
                total_expenses=-50.25,
            )

            formatter = HouseholdFormatter(template_path)
            output = formatter.format_household_output(result)

            lines = output.split("\n")
            assert lines[0] == "-50,25"
            assert lines[1] == ""  # Zero amount should be empty
        finally:
            Path(template_path).unlink()

    def test_format_household_output_category_mapping_ignored(self):
        """Test that category_mapping parameter is ignored (backwards compatibility)."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("Groceries\n")
            template_path = f.name

        try:
            result = ParsingResult(
                parsed_transactions=[],
                uncategorized_transactions=[],
                category_totals={"Groceries": -50.25},
                total_income=0.0,
                total_expenses=-50.25,
            )

            formatter = HouseholdFormatter(template_path)
            # Should not raise error even with category_mapping
            output = formatter.format_household_output(
                result,
                category_mapping={"old": "new"},
            )

            assert "-50,25" in output
        finally:
            Path(template_path).unlink()

    def test_format_amount_zero(self):
        """Test formatting zero amount (should return empty string)."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("Test\n")
            template_path = f.name

        try:
            formatter = HouseholdFormatter(template_path)
            assert formatter._format_amount(0.0) == ""
            assert formatter._format_amount(0) == ""
        finally:
            Path(template_path).unlink()

    def test_format_amount_non_zero(self):
        """Test formatting non-zero amounts."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("Test\n")
            template_path = f.name

        try:
            formatter = HouseholdFormatter(template_path)
            assert formatter._format_amount(100.50) == "100,5"
            assert formatter._format_amount(-50.25) == "-50,25"
            assert formatter._format_amount(1234.56) == "1234,56"
        finally:
            Path(template_path).unlink()

    def test_format_household_output_raises_error_when_category_missing_in_template(
        self,
    ):
        """Test that TransactionHiddenError is raised when a category with transactions is not in template."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("Groceries\n")
            f.write("Salary\n")
            # Missing "Rent" category
            template_path = f.name

        try:
            result = ParsingResult(
                parsed_transactions=[],
                uncategorized_transactions=[],
                category_totals={
                    "Groceries": -50.25,
                    "Salary": 2000.00,
                    "Rent": -800.00,  # This category is not in template
                },
                total_income=2000.00,
                total_expenses=-850.25,
            )

            formatter = HouseholdFormatter(template_path)
            with pytest.raises(TransactionHiddenError) as exc_info:
                formatter.format_household_output(result)

            assert "Rent" in str(exc_info.value)
            assert "Categories with transactions are not in the output template" in str(
                exc_info.value,
            )
        finally:
            Path(template_path).unlink()

    def test_format_household_output_raises_error_with_multiple_missing_categories(
        self,
    ):
        """Test that TransactionHiddenError lists all missing categories."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("Groceries\n")
            # Missing "Rent" and "Utilities" categories
            template_path = f.name

        try:
            result = ParsingResult(
                parsed_transactions=[],
                uncategorized_transactions=[],
                category_totals={
                    "Groceries": -50.25,
                    "Rent": -800.00,  # Not in template
                    "Utilities": -100.00,  # Not in template
                },
                total_income=0.0,
                total_expenses=-950.25,
            )

            formatter = HouseholdFormatter(template_path)
            with pytest.raises(TransactionHiddenError) as exc_info:
                formatter.format_household_output(result)

            error_message = str(exc_info.value)
            assert "Rent" in error_message
            assert "Utilities" in error_message
        finally:
            Path(template_path).unlink()

    def test_format_household_output_ignores_zero_amount_categories(self):
        """Test that categories with zero amounts are ignored in validation."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("Groceries\n")
            f.write("Salary\n")
            # "ZeroCategory" is not in template but has 0 amount, so should not raise error
            template_path = f.name

        try:
            result = ParsingResult(
                parsed_transactions=[],
                uncategorized_transactions=[],
                category_totals={
                    "Groceries": -50.25,
                    "Salary": 2000.00,
                    "ZeroCategory": 0.0,  # Zero amount, should be ignored
                },
                total_income=2000.00,
                total_expenses=-50.25,
            )

            formatter = HouseholdFormatter(template_path)
            # Should not raise error because ZeroCategory has 0 amount
            output = formatter.format_household_output(result)

            lines = output.split("\n")
            assert lines[0] == "-50,25"
            assert lines[1] == "2000,0"
        finally:
            Path(template_path).unlink()

    def test_format_household_output_case_insensitive_validation(self):
        """Test that validation is case-insensitive."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("groceries\n")  # lowercase in template
            f.write("SALARY\n")  # uppercase in template
            template_path = f.name

        try:
            result = ParsingResult(
                parsed_transactions=[],
                uncategorized_transactions=[],
                category_totals={
                    "Groceries": -50.25,  # Title case in result
                    "Salary": 2000.00,  # Title case in result
                },
                total_income=2000.00,
                total_expenses=-50.25,
            )

            formatter = HouseholdFormatter(template_path)
            # Should not raise error because case-insensitive matching works
            output = formatter.format_household_output(result)

            lines = output.split("\n")
            assert lines[0] == "-50,25"
            assert lines[1] == "2000,0"
        finally:
            Path(template_path).unlink()


class TestSummaryFormatter:
    """Tests for SummaryFormatter class."""

    def test_format_summary_basic(self):
        """Test basic summary formatting."""
        booking_date = datetime(2024, 1, 15)
        value_date = datetime(2024, 1, 16)

        transaction1 = Transaction(
            booking_date=booking_date,
            value_date=value_date,
            status="Buchung",
            payer="Max Mustermann",
            recipient="Supermarket",
            purpose="Grocery shopping",
            transaction_type=TransactionType.EXPENSE,
            iban="DE89370400440532013000",
            amount=-50.25,
        )

        transaction2 = Transaction(
            booking_date=booking_date,
            value_date=value_date,
            status="Buchung",
            payer="Employer",
            recipient="Max Mustermann",
            purpose="Salary",
            transaction_type=TransactionType.INCOME,
            iban="DE89370400440532013000",
            amount=2000.00,
        )

        category = Category(
            name="groceries",
            display_name="Groceries",
            search_strings=["supermarket"],
        )

        parsed_transaction = ParsedTransaction(
            transaction=transaction1,
            category=category,
        )

        result = ParsingResult(
            parsed_transactions=[parsed_transaction],
            uncategorized_transactions=[transaction2],
            category_totals={"Groceries": -50.25},
            total_income=2000.00,
            total_expenses=-50.25,
        )

        output = SummaryFormatter.format_summary(result)

        assert "=== DKB Parsing Summary ===" in output
        assert "Total transactions processed: 1" in output
        assert "Categorized transactions: 1" in output
        assert "Uncategorized transactions: 1" in output
        assert "Total income: 2000.00 €" in output
        assert "Total expenses: 50.25 €" in output
        assert "Net balance: 1949.75 €" in output

    def test_format_summary_empty_result(self):
        """Test summary formatting with empty result."""
        result = ParsingResult(
            parsed_transactions=[],
            uncategorized_transactions=[],
            category_totals={},
            total_income=0.0,
            total_expenses=0.0,
        )

        output = SummaryFormatter.format_summary(result)

        assert "Total transactions processed: 0" in output
        assert "Categorized transactions: 0" in output
        assert "Uncategorized transactions: 0" in output
        assert "Total income: 0.00 €" in output
        assert "Total expenses: 0.00 €" in output
        assert "Net balance: 0.00 €" in output

    def test_format_summary_with_category_totals(self):
        """Test summary formatting with category totals."""
        result = ParsingResult(
            parsed_transactions=[],
            uncategorized_transactions=[],
            category_totals={
                "Groceries": -50.25,
                "Salary": 2000.00,
                "Rent": -800.00,
            },
            total_income=2000.00,
            total_expenses=-850.25,
        )

        output = SummaryFormatter.format_summary(result)

        assert "Category totals:" in output
        assert "Groceries: -50.25 €" in output
        assert "Rent: -800.00 €" in output
        assert "Salary: 2000.00 €" in output

    def test_format_summary_with_zero_category_totals(self):
        """Test summary formatting with zero category totals (should be excluded)."""
        result = ParsingResult(
            parsed_transactions=[],
            uncategorized_transactions=[],
            category_totals={
                "Groceries": -50.25,
                "ZeroCategory": 0.0,
            },
            total_income=0.0,
            total_expenses=-50.25,
        )

        output = SummaryFormatter.format_summary(result)

        assert "Groceries: -50.25 €" in output
        assert "ZeroCategory" not in output  # Zero totals should be excluded

    def test_format_summary_negative_net_balance(self):
        """Test summary formatting with negative net balance."""
        result = ParsingResult(
            parsed_transactions=[],
            uncategorized_transactions=[],
            category_totals={},
            total_income=100.00,
            total_expenses=-200.00,
        )

        output = SummaryFormatter.format_summary(result)

        assert "Total income: 100.00 €" in output
        assert "Total expenses: 200.00 €" in output
        assert "Net balance: -100.00 €" in output

    def test_format_summary_categorized_vs_uncategorized(self):
        """Test summary correctly counts categorized vs uncategorized transactions."""
        booking_date = datetime(2024, 1, 15)
        value_date = datetime(2024, 1, 16)

        transaction1 = Transaction(
            booking_date=booking_date,
            value_date=value_date,
            status="Buchung",
            payer="Max Mustermann",
            recipient="Supermarket",
            purpose="Grocery shopping",
            transaction_type=TransactionType.EXPENSE,
            iban="DE89370400440532013000",
            amount=-50.25,
        )

        transaction2 = Transaction(
            booking_date=booking_date,
            value_date=value_date,
            status="Buchung",
            payer="Max Mustermann",
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

        parsed_with_category = ParsedTransaction(
            transaction=transaction1,
            category=category,
        )

        parsed_without_category = ParsedTransaction(
            transaction=transaction2,
            category=None,
        )

        result = ParsingResult(
            parsed_transactions=[parsed_with_category, parsed_without_category],
            uncategorized_transactions=[],
            category_totals={"Groceries": -50.25},
            total_income=0.0,
            total_expenses=-75.25,
        )

        output = SummaryFormatter.format_summary(result)

        assert "Total transactions processed: 2" in output
        assert "Categorized transactions: 1" in output
        assert "Uncategorized transactions: 0" in output
