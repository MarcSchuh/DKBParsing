"""
Category management system for transaction categorization.
"""

import json
import logging
import re
from pathlib import Path

from .models import Category, ParsedTransaction, Transaction

logger = logging.getLogger(__name__)


class FileLoadingError(Exception):
    """Exception raised when a file cannot be loaded."""


class FileSavingError(Exception):
    """Exception raised when a file cannot be saved."""


class TransactionParsingError(Exception):
    """Exception raised when a transaction cannot be parsed."""


class ManualAssignmentCategoryError(Exception):
    """Exception raised when a manual assignment references a category that doesn't exist."""


class CategoryManager:
    """Manages transaction categories and their search patterns."""

    def __init__(
        self,
        category_file: Path,
        manual_assignments_file: Path,
    ):
        self.categories: dict[str, Category] = {}
        self.category_file = category_file
        self.manual_assignments_file = manual_assignments_file
        self.manual_assignments: list[dict[str, str | float]] = []

        if category_file.exists():
            logger.info(f"Loading categories from {category_file}")
            self.load_categories()
            logger.info(f"Loaded {len(self.categories)} categories")
        else:
            logger.debug(
                f"Category config file {category_file} does not exist, will be created on first save",
            )

        if manual_assignments_file.exists():
            logger.info(f"Loading manual assignments from {manual_assignments_file}")
            self.load_manual_assignments()
            logger.info(f"Loaded {len(self.manual_assignments)} manual assignments")
        else:
            logger.debug(
                f"Manual assignments file {manual_assignments_file} does not exist, will be created on first save",
            )

    def add_category(self, category: Category) -> None:
        """Add a new category."""
        if category.name in self.categories:
            logger.warning(f"Category '{category.name}' already exists, overwriting")
        else:
            logger.info(f"Adding new category '{category.name}'")
        self.categories[category.name] = category

        # Auto-save
        try:
            self.save_categories()
        except FileSavingError as e:
            logger.warning(
                f"Failed to auto-save categories after adding '{category.name}': {e}. "
                f"Please save manually using save_categories().",
            )

    def remove_category(self, name: str) -> None:
        """Remove a category."""
        if name in self.categories:
            logger.info(f"Removing category '{name}'")
            del self.categories[name]

            # Auto-save
            try:
                self.save_categories()
            except FileSavingError as e:
                logger.warning(
                    f"Failed to auto-save categories after removing '{name}': {e}. "
                    f"Please save manually using save_categories().",
                )
        else:
            logger.warning(f"Category '{name}' does not exist, cannot remove")

    def get_category(self, name: str) -> Category | None:
        """Get a category by name."""
        return self.categories.get(name)

    def list_categories(self) -> list[Category]:
        """Get all categories."""
        return list(self.categories.values())

    def add_search_string(self, category_name: str, search_string: str) -> None:
        """Add a search string to a category."""
        if category_name not in self.categories:
            logger.warning(
                f"Category '{category_name}' does not exist. Cannot add search string '{search_string}'. "
                f"Available categories: {list(self.categories.keys())}",
            )
            return

        if search_string in self.categories[category_name].search_strings:
            logger.debug(
                f"Search string '{search_string}' already exists in category '{category_name}'",
            )
            return

        self.categories[category_name].search_strings.append(search_string)
        logger.info(
            f"Added search string '{search_string}' to category '{category_name}'",
        )

    def remove_search_string(self, category_name: str, search_string: str) -> None:
        """Remove a search string from a category."""
        if category_name not in self.categories:
            logger.warning(
                f"Category '{category_name}' does not exist. Cannot remove search string '{search_string}'. "
                f"Available categories: {list(self.categories.keys())}",
            )
            return

        if search_string not in self.categories[category_name].search_strings:
            logger.warning(
                f"Search string '{search_string}' does not exist in category '{category_name}'. "
                f"Available search strings: {self.categories[category_name].search_strings}",
            )
            return

        self.categories[category_name].search_strings.remove(search_string)
        logger.info(
            f"Removed search string '{search_string}' from category '{category_name}'",
        )

    def categorize_transaction(
        self,
        transaction: Transaction,
    ) -> tuple[Category | None, list[str]]:
        """
        Categorize a single transaction.

        Returns:
            Tuple of (category, list_of_matches)
        """
        # First check manual assignments
        manual_category = self._check_manual_assignment(transaction)
        if manual_category:
            return manual_category, ["manual assignment"]

        search_text = f"{transaction.value_date.strftime('%d.%m.%y')} {transaction.recipient} {transaction.purpose}"
        # Include IBAN in search text if present
        if transaction.iban and transaction.iban.strip():
            search_text = f"{search_text} {transaction.iban}"
        search_text = search_text.lower()

        for category in self.categories.values():
            matches = []
            iban_matches = []
            text_matches = []

            # Check IBAN patterns (if IBAN is present and category has IBAN patterns)
            if transaction.iban and transaction.iban.strip() and category.iban_patterns:
                for iban_pattern in category.iban_patterns:
                    # IBAN patterns can be exact matches or regex patterns
                    # Try exact match first (case-insensitive)
                    if iban_pattern.upper() == transaction.iban.upper():
                        iban_matches.append(f"iban: {iban_pattern}")
                    # Try regex match
                    else:
                        try:
                            if re.search(iban_pattern, transaction.iban, re.IGNORECASE):
                                iban_matches.append(f"iban: {iban_pattern}")
                        except re.error:
                            continue

            # Check search strings
            for search_string in category.search_strings:
                if search_string.lower() in search_text:
                    text_matches.append(search_string)

            # Check regex patterns
            if category.regex_patterns:
                for pattern in category.regex_patterns:
                    try:
                        if re.search(pattern, search_text, re.IGNORECASE):
                            text_matches.append(f"regex: {pattern}")
                    except re.error:
                        continue

            # If category has IBAN patterns, both IBAN and text matches are required
            # But if transaction has no IBAN, ignore IBAN patterns (backward compatibility)
            if category.iban_patterns and transaction.iban and transaction.iban.strip():
                if iban_matches and text_matches:
                    matches = iban_matches + text_matches
                    return category, matches
            # If no IBAN patterns OR transaction has no IBAN, text matches are sufficient
            else:
                if text_matches:
                    matches = text_matches
                    return category, matches

        return None, []

    def categorize_transactions(
        self,
        transactions: list[Transaction],
    ) -> list[ParsedTransaction]:
        """
        Categorize a list of transactions.

        Returns:
            List of ParsedTransaction objects
        """
        parsed_transactions = []

        for transaction in transactions:
            category, matches = self.categorize_transaction(transaction)
            parsed_transaction = ParsedTransaction(
                transaction=transaction,
                category=category,
                search_matches=matches,
            )
            parsed_transactions.append(parsed_transaction)

        return parsed_transactions

    def save_categories(self) -> None:
        """Save categories to JSON file."""

        logger.info(f"Saving {len(self.categories)} categories to {self.category_file}")
        data: dict[str, dict[str, str | list[str] | float | None]] = {}
        for name, category in self.categories.items():
            category_data: dict[str, str | list[str] | float | None] = {
                "display_name": category.display_name,
                "search_strings": category.search_strings,
                "regex_patterns": category.regex_patterns,
            }
            if category.iban_patterns:
                category_data["iban_patterns"] = category.iban_patterns
            if category.expected_max_amount is not None:
                category_data["expected_max_amount"] = category.expected_max_amount
            data[name] = category_data

        try:
            self.category_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.category_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Successfully saved categories to {self.category_file}")
        except OSError as e:
            logger.error(f"Failed to save categories to {self.category_file}: {e}")
            raise FileSavingError(
                f"Failed to save categories to {self.category_file}: {e}",
            ) from e

    def load_categories(self) -> None:
        """Load categories from JSON file."""
        try:
            with open(self.category_file, encoding="utf-8") as f:
                data = json.load(f)

            self.categories = {}
            for name, category_data in data.items():
                category = Category(
                    name=name,
                    display_name=category_data.get("display_name", name),
                    search_strings=category_data.get("search_strings", []),
                    regex_patterns=category_data.get("regex_patterns", []),
                    iban_patterns=category_data.get("iban_patterns", []),
                    expected_max_amount=category_data.get("expected_max_amount"),
                )
                self.categories[name] = category
            logger.debug(
                f"Loaded {len(self.categories)} categories from {self.category_file}",
            )
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in category file {self.category_file}: {e}")
            raise
        except OSError as e:
            logger.error(f"Failed to load categories from {self.category_file}: {e}")
            raise FileLoadingError(
                f"Failed to load categories from {self.category_file}: {e}",
            ) from e

    def load_manual_assignments(self) -> None:
        """Load manual assignments from JSON file."""

        try:
            with open(self.manual_assignments_file, encoding="utf-8") as f:
                data = json.load(f)

            self.manual_assignments = data.get("manual_assignments", [])

            # Validate that all categories in manual assignments exist
            for assignment in self.manual_assignments:
                category_name = assignment.get("category")
                if (
                    isinstance(category_name, str)
                    and category_name not in self.categories
                ):
                    raise ManualAssignmentCategoryError(
                        f"Manual assignment references category '{category_name}' which does not exist. "
                        f"Available categories: {list(self.categories.keys())}",
                    )

            logger.debug(
                f"Loaded {len(self.manual_assignments)} manual assignments from {self.manual_assignments_file}",
            )
        except json.JSONDecodeError as e:
            logger.error(
                f"Invalid JSON in manual assignments file {self.manual_assignments_file}: {e}",
            )
            raise
        except OSError as e:
            logger.error(
                f"Failed to load manual assignments from {self.manual_assignments_file}: {e}",
            )
            raise FileLoadingError(
                f"Failed to load manual assignments from {self.manual_assignments_file}: {e}",
            ) from e

    def save_manual_assignments(self) -> None:
        """Save manual assignments to JSON file."""
        logger.info(
            f"Saving {len(self.manual_assignments)} manual assignments to {self.manual_assignments_file}",
        )
        data = {"manual_assignments": self.manual_assignments}
        try:
            self.manual_assignments_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.manual_assignments_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(
                f"Successfully saved manual assignments to {self.manual_assignments_file}",
            )
        except OSError as e:
            logger.error(
                f"Failed to save manual assignments to {self.manual_assignments_file}: {e}",
            )
            raise FileSavingError(
                f"Failed to save manual assignments to {self.manual_assignments_file}: {e}",
            ) from e

    def add_manual_assignment(
        self,
        date: str,
        recipient: str,
        purpose: str,
        category_name: str,
        amount: float | None = None,
    ) -> None:
        """Add a manual assignment. Amount is optional and only used for validation."""
        # Validate that category exists
        if category_name not in self.categories:
            raise ManualAssignmentCategoryError(
                f"Manual assignment references category '{category_name}' which does not exist. "
                f"Available categories: {list(self.categories.keys())}",
            )

        assignment: dict[str, str | float] = {
            "date": date,
            "recipient": recipient,
            "purpose": purpose,
            "category": category_name,
        }
        # Only include amount if provided (for backwards compatibility)
        if amount is not None:
            assignment["amount"] = float(amount)

        self.manual_assignments.append(assignment)
        logger.info(
            f"Added manual assignment: {date} {recipient[:30]}... -> {category_name}",
        )
        self.save_manual_assignments()

    def remove_manual_assignment(self, date: str, recipient: str, purpose: str) -> None:
        """Remove a manual assignment."""
        initial_count = len(self.manual_assignments)
        self.manual_assignments = [
            manual_assignment
            for manual_assignment in self.manual_assignments
            if not (
                manual_assignment["date"] == date
                and manual_assignment["recipient"] == recipient
                and manual_assignment["purpose"] == purpose
            )
        ]

        if len(self.manual_assignments) < initial_count:
            logger.info(f"Removed manual assignment: {date} {recipient[:30]}...")
            self.save_manual_assignments()
        else:
            logger.warning(f"Manual assignment not found: {date} {recipient[:30]}...")

    def _check_manual_assignment(self, transaction: Transaction) -> Category | None:
        """Check if transaction has a manual assignment."""
        date_str = transaction.value_date.strftime("%d.%m.%y")

        for assignment in self.manual_assignments:
            # Match on date, recipient, and purpose
            if (
                assignment["date"] == date_str
                and assignment["recipient"] == transaction.recipient
                and assignment["purpose"] == transaction.purpose
            ):
                # If amount is specified, use it for validation (optional)
                if "amount" in assignment:
                    amount_val = assignment["amount"]
                    if (
                        isinstance(amount_val, (int, float))
                        and abs(float(amount_val) - transaction.amount) >= 0.01
                    ):
                        continue  # Amount mismatch, skip this assignment

                category_name = assignment["category"]
                if isinstance(category_name, str):
                    if category_name not in self.categories:
                        raise ManualAssignmentCategoryError(
                            f"Manual assignment references category '{category_name}' which does not exist. "
                            f"Available categories: {list(self.categories.keys())}",
                        )
                    return self.categories[category_name]

        return None
