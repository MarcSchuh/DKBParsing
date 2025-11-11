"""
CSV parsing functionality for DKB exports.
"""

import logging
from datetime import datetime

import pandas as pd

from .models import Transaction

logger = logging.getLogger(__name__)


class DKBCSVParser:
    """Parser for DKB CSV export files."""

    def __init__(
        self,
        encoding: str = "utf-8",
        delimiter: str = ";",
        skiprows: int = 4,
    ):
        self.encoding = encoding
        self.delimiter = delimiter
        self.skiprows = skiprows

    def parse_file(self, file_path: str) -> list[Transaction]:
        """
        Parse a DKB CSV file and return list of transactions.

        Args:
            file_path: Path to the CSV file

        Returns:
            List of Transaction objects
        """
        try:
            df = pd.read_csv(
                file_path,
                delimiter=self.delimiter,
                encoding=self.encoding,
                skiprows=self.skiprows,
            )

            # Clean up column names
            df.columns = df.columns.str.strip()

            # Convert to list of dictionaries
            rows = df.to_dict("records")

            transactions = []
            for row in rows:
                try:
                    transaction = Transaction.from_csv_row(row)
                    transactions.append(transaction)
                except (ValueError, KeyError, TypeError) as e:
                    logger.warning(f"Could not parse transaction row: {e}")
                    continue

            return transactions

        except Exception as e:
            raise ValueError(f"Error parsing CSV file: {e}") from e

    def filter_by_date_range(
        self,
        transactions: list[Transaction],
        start_date: datetime,
        end_date: datetime,
    ) -> list[Transaction]:
        """
        Filter transactions by date range.

        Args:
            transactions: List of transactions to filter
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            Filtered list of transactions
        """
        return [t for t in transactions if start_date <= t.value_date <= end_date]
