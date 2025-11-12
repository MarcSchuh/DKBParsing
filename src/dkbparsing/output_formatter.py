"""
Output formatting for Excel-compatible results.
"""

import logging

from .models import ParsingResult

logger = logging.getLogger(__name__)


class TransactionHiddenError(Exception):
    """Exception raised when a category with transactions is not in the output template."""


class ExcelFormatter:
    """Formats parsing results for Excel output."""

    def __init__(self, category_order: list[str] | None = None):
        self.category_order = category_order or []

    def format_for_excel(
        self,
        result: ParsingResult,
        show_uncategorized: bool = True,
        show_totals: bool = True,
    ) -> str:
        """
        Format parsing result for Excel output.

        Args:
            result: ParsingResult object
            show_uncategorized: Whether to show uncategorized transactions
            show_totals: Whether to show category totals

        Returns:
            Formatted string ready for Excel
        """
        lines = []

        # Format categorized transactions
        lines.append("All catagorized transactions:")
        if show_totals:
            lines.extend(self._format_category_totals(result))

        # Format uncategorized transactions
        if show_uncategorized and result.uncategorized_transactions:
            lines.extend(self._format_uncategorized(result.uncategorized_transactions))

        return "\n".join(lines)

    def _format_category_totals(self, result: ParsingResult) -> list[str]:
        """Format category totals for Excel."""
        lines = []

        # Sort categories by order or alphabetically
        sorted_categories = self._sort_categories(result.category_totals)

        for category_name in sorted_categories:
            amount = result.category_totals[category_name]
            if amount != 0:
                formatted_amount = self._format_amount(amount)
                lines.append(f"{category_name}: {formatted_amount}")
            else:
                lines.append("")

        return lines

    def _format_uncategorized(self, transactions: list) -> list[str]:
        """Format uncategorized transactions."""
        lines = []
        lines.append("")  # Empty line separator
        lines.append("Uncategorized transactions:")

        for transaction in transactions:
            line = f"{transaction.value_date.strftime('%d.%m.%y')} | {transaction.recipient} | {transaction.purpose} | {self._format_amount(transaction.amount)}"
            lines.append(line)

        return lines

    def _sort_categories(self, category_totals: dict[str, float]) -> list[str]:
        """Sort categories by predefined order or alphabetically."""
        categories = list(category_totals.keys())

        # First, add categories in predefined order
        sorted_categories = []
        for category in self.category_order:
            if category in categories:
                sorted_categories.append(category)

        # Then add remaining categories alphabetically
        remaining = [cat for cat in categories if cat not in sorted_categories]
        sorted_categories.extend(sorted(remaining))

        return sorted_categories

    def _format_amount(self, amount: float) -> str:
        """Format amount for German Excel (comma as decimal separator)."""
        return str(round(amount, 2)).replace(".", ",")


class HouseholdFormatter:
    """Formats output for household budget integration."""

    def __init__(self, template_file: str):
        self.template_file = template_file
        self.template_lines = self._load_template()

    def _load_template(self) -> list[str]:
        """Load the template file."""
        try:
            with open(self.template_file, encoding="utf-8") as f:
                return f.readlines()
        except FileNotFoundError as e:
            raise ValueError(f"Template file not found: {self.template_file}") from e

    def format_household_output(
        self,
        result: ParsingResult,
        category_mapping: dict[str, str] | None = None,
    ) -> str:
        """
        Format output according to household template.

        Template lines should contain category display names directly.

        Args:
            result: ParsingResult object
            category_mapping: Ignored (kept for backwards compatibility)

        Raises:
            TransactionHiddenError: If a category with transactions is not in the template
        """
        # Create mapping from category display names to amounts (case-insensitive lookup)
        category_amounts = {}
        category_lookup = {}  # Lowercase -> original name mapping
        for category_name, amount in result.category_totals.items():
            category_amounts[category_name] = amount
            category_lookup[category_name.lower()] = category_name

        # Get categories with non-zero amounts (transactions)
        categories_with_transactions = {
            name for name, amount in category_amounts.items() if amount != 0
        }

        # Create set of template category names (case-insensitive)
        template_categories_lower = {
            line.strip().lower() for line in self.template_lines if line.strip()
        }

        # Check if all categories with transactions are in the template
        missing_categories = []
        for category_name in categories_with_transactions:
            if category_name.lower() not in template_categories_lower:
                missing_categories.append(category_name)

        if missing_categories:
            raise TransactionHiddenError(
                f"Categories with transactions are not in the output template: {', '.join(missing_categories)}. "
                f"Template categories: {[line.strip() for line in self.template_lines if line.strip()]}",
            )

        # Debug: Print available categories and amounts
        logger.debug(f"Available category amounts: {category_amounts}")
        logger.debug(
            f"Template lines: {[line.strip() for line in self.template_lines]}",
        )

        output_lines = []

        for line in self.template_lines:
            line = line.strip()
            if not line:  # Empty line
                output_lines.append("")
                continue

            line_lower = line.lower()

            # Try exact match first
            if line in category_amounts:
                amount = category_amounts[line]
                output_lines.append(self._format_amount(amount))
            # Try case-insensitive match
            elif line_lower in category_lookup:
                original_name = category_lookup[line_lower]
                amount = category_amounts[original_name]
                output_lines.append(self._format_amount(amount))
            else:
                logger.debug(f"Category '{line}' not found in category_amounts")
                output_lines.append("")

        return "The lines below are for your excel sheet\n" + "\n".join(output_lines)

    def _format_amount(self, amount: float) -> str:
        """Format amount for German Excel (comma as decimal separator)."""
        if amount == 0:
            return ""
        return str(round(amount, 2)).replace(".", ",")


class SummaryFormatter:
    """Formats summary information."""

    @staticmethod
    def format_summary(result: ParsingResult, warnings: list[str] | None = None) -> str:
        """Format a summary of the parsing result.

        Args:
            result: ParsingResult object
            warnings: Optional list of warning messages to display at the end
        """
        lines = []
        lines.append("=== DKB Parsing Summary ===")
        lines.append(f"Total transactions processed: {len(result.parsed_transactions)}")
        lines.append(
            f"Categorized transactions: {len([t for t in result.parsed_transactions if t.category])}",
        )
        lines.append(
            f"Uncategorized transactions: {len(result.uncategorized_transactions)}",
        )
        lines.append(f"Total income: {result.total_income:.2f} €")
        lines.append(f"Total expenses: {abs(result.total_expenses):.2f} €")
        lines.append(
            f"Net balance: {result.total_income + result.total_expenses:.2f} €",
        )
        lines.append("")

        if result.category_totals:
            lines.append("Category totals:")
            for category, total in sorted(result.category_totals.items()):
                if total != 0:
                    lines.append(f"  {category}: {total:.2f} €")

        if warnings:
            lines.append("")
            lines.append("⚠️  Warnung: Ungewöhnliche Umsätze detektiert:")
            for warning in warnings:
                lines.append(f"  • {warning}")

        return "\n".join(lines)
