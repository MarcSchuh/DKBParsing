"""
Category management system for transaction categorization.
"""

import json
import logging
import re
from pathlib import Path

from .models import Category, ParsedTransaction, Transaction

logger = logging.getLogger(__name__)


class CategoryManager:
    """Manages transaction categories and their search patterns."""

    def __init__(
        self,
        config_file: str | None = None,
        manual_assignments_file: str | None = None,
    ):
        self.categories: dict[str, Category] = {}
        self.config_file = config_file
        self.manual_assignments_file = manual_assignments_file
        self.manual_assignments: list[dict[str, str | float]] = []

        if config_file and Path(config_file).exists():
            logger.info(f"Loading categories from {config_file}")
            self.load_categories()
            logger.info(f"Loaded {len(self.categories)} categories")
        else:
            logger.debug("No category config file provided or file does not exist")

        if manual_assignments_file and Path(manual_assignments_file).exists():
            logger.info(f"Loading manual assignments from {manual_assignments_file}")
            self.load_manual_assignments()
            logger.info(f"Loaded {len(self.manual_assignments)} manual assignments")
        else:
            logger.debug("No manual assignments file provided or file does not exist")

    def add_category(self, category: Category) -> None:
        """Add a new category."""
        if category.name in self.categories:
            logger.warning(f"Category '{category.name}' already exists, overwriting")
        else:
            logger.info(f"Adding new category '{category.name}'")
        self.categories[category.name] = category

        # Auto-save if config file is set
        if self.config_file:
            try:
                self.save_categories()
            except Exception as e:
                logger.warning(
                    f"Failed to auto-save categories after adding '{category.name}': {e}. "
                    f"Please save manually using save_categories().",
                )

    def remove_category(self, name: str) -> None:
        """Remove a category."""
        if name in self.categories:
            logger.info(f"Removing category '{name}'")
            del self.categories[name]

            # Auto-save if config file is set
            if self.config_file:
                try:
                    self.save_categories()
                except Exception as e:
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

    def add_regex_pattern(self, category_name: str, pattern: str) -> None:
        """Add a regex pattern to a category."""
        if category_name not in self.categories:
            logger.warning(
                f"Category '{category_name}' does not exist. Cannot add regex pattern. "
                f"Available categories: {list(self.categories.keys())}",
            )
            return

        category = self.categories[category_name]
        if category.regex_patterns is None:
            object.__setattr__(category, "regex_patterns", [])

        # Ensure regex_patterns is not None for type checking
        patterns = category.regex_patterns
        if patterns is None:
            patterns = []
            object.__setattr__(category, "regex_patterns", patterns)

        if pattern in patterns:
            logger.debug(f"Regex pattern already exists in category '{category_name}'")
            return

        # Validate regex pattern
        try:
            re.compile(pattern)
            patterns.append(pattern)
            logger.info(f"Added regex pattern to category '{category_name}'")
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            raise ValueError(f"Invalid regex pattern: {e}") from e

    def remove_regex_pattern(self, category_name: str, pattern: str) -> None:
        """Remove a regex pattern from a category."""
        if category_name not in self.categories:
            logger.warning(
                f"Category '{category_name}' does not exist. Cannot remove regex pattern. "
                f"Available categories: {list(self.categories.keys())}",
            )
            return

        category = self.categories[category_name]
        if category.regex_patterns is None:
            object.__setattr__(category, "regex_patterns", [])

        # Ensure regex_patterns is not None for type checking
        patterns = category.regex_patterns
        if patterns is None:
            patterns = []
            object.__setattr__(category, "regex_patterns", patterns)

        if pattern not in patterns:
            logger.warning(
                f"Regex pattern does not exist in category '{category_name}'. "
                f"Available patterns: {patterns}",
            )
            return

        patterns.remove(pattern)
        logger.info(f"Removed regex pattern from category '{category_name}'")

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
        search_text = search_text.lower()

        for category in self.categories.values():
            matches = []

            # Check search strings
            for search_string in category.search_strings:
                if search_string.lower() in search_text:
                    matches.append(search_string)

            # Check regex patterns
            if category.regex_patterns:
                for pattern in category.regex_patterns:
                    try:
                        if re.search(pattern, search_text, re.IGNORECASE):
                            matches.append(f"regex: {pattern}")
                    except re.error:
                        continue

            if matches:
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

    def save_categories(self, file_path: str | None = None) -> None:
        """Save categories to JSON file."""
        save_path = file_path or self.config_file
        if not save_path:
            logger.error("No file path provided for saving categories")
            raise ValueError("No file path provided for saving categories")

        logger.info(f"Saving {len(self.categories)} categories to {save_path}")
        data = {}
        for name, category in self.categories.items():
            data[name] = {
                "display_name": category.display_name,
                "search_strings": category.search_strings,
                "regex_patterns": category.regex_patterns,
            }

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Successfully saved categories to {save_path}")
        except Exception as e:
            logger.error(f"Failed to save categories to {save_path}: {e}")
            raise

    def load_categories(self, file_path: str | None = None) -> None:
        """Load categories from JSON file."""
        load_path = file_path or self.config_file
        if not load_path or not Path(load_path).exists():
            logger.debug(f"Category file {load_path} does not exist, skipping load")
            return

        try:
            with open(load_path, encoding="utf-8") as f:
                data = json.load(f)

            self.categories = {}
            for name, category_data in data.items():
                category = Category(
                    name=name,
                    display_name=category_data.get("display_name", name),
                    search_strings=category_data.get("search_strings", []),
                    regex_patterns=category_data.get("regex_patterns", []),
                )
                self.categories[name] = category
            logger.debug(f"Loaded {len(self.categories)} categories from {load_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in category file {load_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load categories from {load_path}: {e}")
            raise

    def load_manual_assignments(self, file_path: str | None = None) -> None:
        """Load manual assignments from JSON file."""
        load_path = file_path or self.manual_assignments_file
        if not load_path or not Path(load_path).exists():
            logger.debug(
                f"Manual assignments file {load_path} does not exist, skipping load",
            )
            return

        try:
            with open(load_path, encoding="utf-8") as f:
                data = json.load(f)

            self.manual_assignments = data.get("manual_assignments", [])
            logger.debug(
                f"Loaded {len(self.manual_assignments)} manual assignments from {load_path}",
            )
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in manual assignments file {load_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load manual assignments from {load_path}: {e}")
            raise

    def save_manual_assignments(self, file_path: str | None = None) -> None:
        """Save manual assignments to JSON file."""
        save_path = file_path or self.manual_assignments_file
        if not save_path:
            logger.error("No file path provided for saving manual assignments")
            raise ValueError("No file path provided for saving manual assignments")

        logger.info(
            f"Saving {len(self.manual_assignments)} manual assignments to {save_path}",
        )
        data = {"manual_assignments": self.manual_assignments}
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Successfully saved manual assignments to {save_path}")
        except Exception as e:
            logger.error(f"Failed to save manual assignments to {save_path}: {e}")
            raise

    def add_manual_assignment(
        self,
        date: str,
        recipient: str,
        purpose: str,
        category_name: str,
        amount: float | None = None,
    ) -> None:
        """Add a manual assignment. Amount is optional and only used for validation."""
        # Create category if it doesn't exist
        if category_name not in self.categories:
            logger.info(f"Creating category '{category_name}' for manual assignment")
            from .models import Category

            self.categories[category_name] = Category(
                name=category_name,
                display_name=category_name,
                search_strings=[],
                regex_patterns=[],
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

    def remove_manual_assignment(self, date: str, recipient: str, purpose: str) -> None:
        """Remove a manual assignment."""
        initial_count = len(self.manual_assignments)
        self.manual_assignments = [
            a
            for a in self.manual_assignments
            if not (
                a["date"] == date
                and a["recipient"] == recipient
                and a["purpose"] == purpose
            )
        ]

        if len(self.manual_assignments) < initial_count:
            logger.info(f"Removed manual assignment: {date} {recipient[:30]}...")
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
                if isinstance(category_name, str) and category_name in self.categories:
                    return self.categories[category_name]

        return None
