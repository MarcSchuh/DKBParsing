"""
Data models for DKB parsing.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class TransactionType(Enum):
    """Transaction type enumeration."""

    INCOME = "Eingang"
    EXPENSE = "Ausgang"


@dataclass
class Transaction:
    """Represents a single bank transaction."""

    booking_date: datetime
    value_date: datetime
    status: str
    payer: str
    recipient: str
    purpose: str
    transaction_type: TransactionType
    iban: str
    amount: float
    creditor_id: str | None = None
    mandate_reference: str | None = None
    customer_reference: str | None = None

    @classmethod
    def from_csv_row(cls, row: dict[str, Any]) -> "Transaction":
        """Create Transaction from CSV row data."""
        # Parse dates
        booking_date = datetime.strptime(row["Buchungsdatum"], "%d.%m.%y")
        value_date = datetime.strptime(row["Wertstellung"], "%d.%m.%y")

        # Parse amount (handle German number format)
        amount_str = (
            row["Betrag (€)"]
            .replace(".", "")
            .replace(",", ".")
            .replace("€", "")
            .strip()
        )
        amount = float(amount_str)

        # Determine transaction type
        transaction_type = (
            TransactionType.INCOME if amount >= 0 else TransactionType.EXPENSE
        )

        return cls(
            booking_date=booking_date,
            value_date=value_date,
            status=row["Status"],
            payer=row["Zahlungspflichtige*r"],
            recipient=row["Zahlungsempfänger*in"],
            purpose=row["Verwendungszweck"],
            transaction_type=transaction_type,
            iban=row["IBAN"],
            amount=amount,
            creditor_id=row.get("Gläubiger-ID"),
            mandate_reference=row.get("Mandatsreferenz"),
            customer_reference=row.get("Kundenreferenz"),
        )


@dataclass
class Category:
    """Represents a transaction category."""

    name: str
    display_name: str
    search_strings: list[str]
    regex_patterns: list[str] | None = None

    def __post_init__(self):
        if self.regex_patterns is None:
            object.__setattr__(self, "regex_patterns", [])


@dataclass
class ParsedTransaction:
    """A transaction with its assigned category."""

    transaction: Transaction
    category: Category | None
    search_matches: list[str] | None = None

    def __post_init__(self):
        if self.search_matches is None:
            object.__setattr__(self, "search_matches", [])


@dataclass
class ParsingResult:
    """Result of parsing transactions."""

    parsed_transactions: list[ParsedTransaction]
    uncategorized_transactions: list[Transaction]
    category_totals: dict[str, float]
    total_income: float
    total_expenses: float
