"""
Main parser class that orchestrates the parsing process.
"""

from datetime import datetime

from .category_manager import CategoryManager
from .csv_parser import DKBCSVParser
from .models import ParsedTransaction, ParsingResult
from .output_formatter import ExcelFormatter, HouseholdFormatter, SummaryFormatter


class DKBParser:
    """Main parser class for DKB transactions."""

    def __init__(
        self,
        config_file: str | None = None,
        manual_assignments_file: str | None = None,
    ):
        self.csv_parser = DKBCSVParser()
        self.category_manager = CategoryManager(config_file, manual_assignments_file)
        self.excel_formatter = ExcelFormatter()
        self.summary_formatter = SummaryFormatter()

    def parse_file(
        self,
        file_path: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> ParsingResult:
        """
        Parse a DKB CSV file and categorize transactions.

        Args:
            file_path: Path to the CSV file
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            ParsingResult object
        """
        # Parse CSV file
        transactions = self.csv_parser.parse_file(file_path)

        # Apply date filter if provided
        if start_date and end_date:
            transactions = self.csv_parser.filter_by_date_range(
                transactions,
                start_date,
                end_date,
            )

        # Categorize transactions
        parsed_transactions = self.category_manager.categorize_transactions(
            transactions,
        )

        # Calculate totals
        category_totals = self._calculate_category_totals(parsed_transactions)
        total_income, total_expenses = self._calculate_income_expenses(
            parsed_transactions,
        )

        # Separate categorized and uncategorized
        uncategorized = [
            pt.transaction for pt in parsed_transactions if not pt.category
        ]

        return ParsingResult(
            parsed_transactions=parsed_transactions,
            uncategorized_transactions=uncategorized,
            category_totals=category_totals,
            total_income=total_income,
            total_expenses=total_expenses,
        )

    def add_category(
        self,
        name: str,
        display_name: str,
        search_strings: list[str] | None = None,
        regex_patterns: list[str] | None = None,
    ) -> None:
        """Add a new category."""
        from .models import Category

        category = Category(
            name=name,
            display_name=display_name,
            search_strings=search_strings or [],
            regex_patterns=regex_patterns or [],
        )
        self.category_manager.add_category(category)

    def add_search_string(self, category_name: str, search_string: str) -> None:
        """Add a search string to a category."""
        self.category_manager.add_search_string(category_name, search_string)

    def remove_search_string(self, category_name: str, search_string: str) -> None:
        """Remove a search string from a category."""
        self.category_manager.remove_search_string(category_name, search_string)

    def save_config(self, file_path: str) -> None:
        """Save category configuration to file."""
        self.category_manager.save_categories(file_path)

    def load_config(self, file_path: str) -> None:
        """Load category configuration from file."""
        self.category_manager.load_categories(file_path)

    def add_manual_assignment(
        self,
        date: str,
        recipient: str,
        purpose: str,
        category_name: str,
        amount: float | None = None,
    ) -> None:
        """Add a manual assignment for a specific transaction. Amount is optional."""
        self.category_manager.add_manual_assignment(
            date,
            recipient,
            purpose,
            category_name,
            amount,
        )

    def remove_manual_assignment(self, date: str, recipient: str, purpose: str) -> None:
        """Remove a manual assignment."""
        self.category_manager.remove_manual_assignment(date, recipient, purpose)

    def save_manual_assignments(self, file_path: str) -> None:
        """Save manual assignments to file."""
        self.category_manager.save_manual_assignments(file_path)

    def format_for_excel(
        self,
        result: ParsingResult,
        category_order: list[str] | None = None,
    ) -> str:
        """Format result for Excel output."""
        if category_order:
            self.excel_formatter.category_order = category_order
        return self.excel_formatter.format_for_excel(result)

    def format_summary(self, result: ParsingResult) -> str:
        """Format summary information."""
        return self.summary_formatter.format_summary(result)

    def format_household(self, result: ParsingResult, template_file: str) -> str:
        """Format output for household budget integration.

        Template file should contain category display names directly, one per line.
        Income can be specified with 'einkommen' in the template line name.
        """
        household_formatter = HouseholdFormatter(template_file)
        return household_formatter.format_household_output(result)

    def _calculate_category_totals(
        self,
        parsed_transactions: list[ParsedTransaction],
    ) -> dict:
        """Calculate totals for each category."""
        totals = {}

        for parsed_transaction in parsed_transactions:
            if parsed_transaction.category:
                category_name = parsed_transaction.category.display_name
                amount = parsed_transaction.transaction.amount

                if category_name not in totals:
                    totals[category_name] = 0.0
                totals[category_name] += amount

        return totals

    def _calculate_income_expenses(
        self,
        parsed_transactions: list[ParsedTransaction],
    ) -> tuple[float, float]:
        """Calculate total income and expenses."""
        total_income = 0.0
        total_expenses = 0.0

        for parsed_transaction in parsed_transactions:
            amount = parsed_transaction.transaction.amount
            if amount >= 0:
                total_income += amount
            else:
                total_expenses += amount

        return total_income, total_expenses
