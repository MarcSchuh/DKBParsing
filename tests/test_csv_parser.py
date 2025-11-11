"""Unit tests for csv_parser.py."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from dkbparsing.csv_parser import DKBCSVParser
from dkbparsing.models import Transaction, TransactionType


class TestDKBCSVParser:
    """Tests for DKBCSVParser class."""

    def test_init_default_parameters(self):
        """Test DKBCSVParser initialization with default parameters."""
        parser = DKBCSVParser()
        assert parser.encoding == "utf-8"
        assert parser.delimiter == ";"
        assert parser.skiprows == 4

    def test_init_custom_parameters(self):
        """Test DKBCSVParser initialization with custom parameters."""
        parser = DKBCSVParser(encoding="latin-1", delimiter=",", skiprows=5)
        assert parser.encoding == "latin-1"
        assert parser.delimiter == ","
        assert parser.skiprows == 5

    def test_parse_file_valid_csv(self):
        """Test parsing a valid DKB CSV file."""
        # Create a temporary CSV file with DKB format
        csv_content = """Header line 1
Header line 2
Header line 3
Header line 4
Buchungsdatum;Wertstellung;Status;Zahlungspflichtige*r;Zahlungsempfänger*in;Verwendungszweck;Betrag (€);IBAN
15.01.24;16.01.24;Buchung;Max Mustermann;Supermarket;Grocery shopping;-50,25 €;DE89370400440532013000
20.02.24;21.02.24;Buchung;Employer;Max Mustermann;Salary;2000,00 €;DE89370400440532013000
"""

        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            suffix=".csv",
            encoding="utf-8",
        ) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            parser = DKBCSVParser()
            transactions = parser.parse_file(csv_path)

            assert len(transactions) == 2
            assert transactions[0].amount == -50.25
            assert transactions[0].transaction_type == TransactionType.EXPENSE
            assert transactions[0].recipient == "Supermarket"
            assert transactions[0].purpose == "Grocery shopping"
            assert transactions[1].amount == 2000.00
            assert transactions[1].transaction_type == TransactionType.INCOME
            assert transactions[1].payer == "Employer"
        finally:
            Path(csv_path).unlink()

    def test_parse_file_with_optional_fields(self):
        """Test parsing CSV file with optional fields."""
        csv_content = """Header line 1
Header line 2
Header line 3
Header line 4
Buchungsdatum;Wertstellung;Status;Zahlungspflichtige*r;Zahlungsempfänger*in;Verwendungszweck;Betrag (€);IBAN;Gläubiger-ID;Mandatsreferenz;Kundenreferenz
15.01.24;16.01.24;Buchung;Max Mustermann;Company;Payment;50,25 €;DE89370400440532013000;DE98ZZZ09999999999;MANDATE123;CUST456
"""

        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            suffix=".csv",
            encoding="utf-8",
        ) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            parser = DKBCSVParser()
            transactions = parser.parse_file(csv_path)

            assert len(transactions) == 1
            assert transactions[0].creditor_id == "DE98ZZZ09999999999"
            assert transactions[0].mandate_reference == "MANDATE123"
            assert transactions[0].customer_reference == "CUST456"
        finally:
            Path(csv_path).unlink()

    def test_parse_file_with_invalid_row(self):
        """Test parsing CSV file with invalid rows (should skip them)."""
        csv_content = """Header line 1
Header line 2
Header line 3
Header line 4
Buchungsdatum;Wertstellung;Status;Zahlungspflichtige*r;Zahlungsempfänger*in;Verwendungszweck;Betrag (€);IBAN
15.01.24;16.01.24;Buchung;Max Mustermann;Supermarket;Grocery shopping;50,25 €;DE89370400440532013000
invalid;date;row;should;be;skipped;xxx;yyy
20.02.24;21.02.24;Buchung;Employer;Max Mustermann;Salary;2000,00 €;DE89370400440532013000
"""

        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            suffix=".csv",
            encoding="utf-8",
        ) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            parser = DKBCSVParser()
            transactions = parser.parse_file(csv_path)

            # Should only have 2 valid transactions
            assert len(transactions) == 2
            assert transactions[0].recipient == "Supermarket"
            assert transactions[1].payer == "Employer"
        finally:
            Path(csv_path).unlink()

    def test_parse_file_missing_file(self):
        """Test parsing a non-existent file."""
        parser = DKBCSVParser()
        with pytest.raises(ValueError, match="Error parsing CSV file"):
            parser.parse_file("/nonexistent/path/file.csv")

    def test_parse_file_empty_file(self):
        """Test parsing an empty CSV file (only headers)."""
        csv_content = """Header line 1
Header line 2
Header line 3
Header line 4
Buchungsdatum;Wertstellung;Status;Zahlungspflichtige*r;Zahlungsempfänger*in;Verwendungszweck;Betrag (€);IBAN
"""

        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            suffix=".csv",
            encoding="utf-8",
        ) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            parser = DKBCSVParser()
            transactions = parser.parse_file(csv_path)

            assert len(transactions) == 0
        finally:
            Path(csv_path).unlink()

    def test_parse_file_custom_encoding(self):
        """Test parsing CSV file with custom encoding."""
        csv_content = """Header line 1
Header line 2
Header line 3
Header line 4
Buchungsdatum;Wertstellung;Status;Zahlungspflichtige*r;Zahlungsempfänger*in;Verwendungszweck;Betrag (€);IBAN
15.01.24;16.01.24;Buchung;Max Mustermann;Supermarket;Grocery shopping;50,25 €;DE89370400440532013000
"""

        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            suffix=".csv",
            encoding="utf-8",
        ) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            parser = DKBCSVParser(encoding="utf-8")
            transactions = parser.parse_file(csv_path)

            assert len(transactions) == 1
        finally:
            Path(csv_path).unlink()

    def test_parse_file_custom_delimiter(self):
        """Test parsing CSV file with custom delimiter (tab-separated)."""
        csv_content = """Header line 1
Header line 2
Header line 3
Header line 4
Buchungsdatum	Wertstellung	Status	Zahlungspflichtige*r	Zahlungsempfänger*in	Verwendungszweck	Betrag (€)	IBAN
15.01.24	16.01.24	Buchung	Max Mustermann	Supermarket	Grocery shopping	-50,25 €	DE89370400440532013000
"""

        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            suffix=".csv",
            encoding="utf-8",
        ) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            parser = DKBCSVParser(delimiter="\t")
            transactions = parser.parse_file(csv_path)

            assert len(transactions) == 1
            assert transactions[0].recipient == "Supermarket"
            assert transactions[0].amount == -50.25
        finally:
            Path(csv_path).unlink()

    def test_parse_file_custom_skiprows(self):
        """Test parsing CSV file with custom skiprows."""
        csv_content = """Header line 1
Header line 2
Header line 3
Header line 4
Header line 5
Buchungsdatum;Wertstellung;Status;Zahlungspflichtige*r;Zahlungsempfänger*in;Verwendungszweck;Betrag (€);IBAN
15.01.24;16.01.24;Buchung;Max Mustermann;Supermarket;Grocery shopping;50,25 €;DE89370400440532013000
"""

        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            suffix=".csv",
            encoding="utf-8",
        ) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            parser = DKBCSVParser(skiprows=5)
            transactions = parser.parse_file(csv_path)

            assert len(transactions) == 1
        finally:
            Path(csv_path).unlink()

    def test_parse_file_columns_with_whitespace(self):
        """Test parsing CSV file with column names containing whitespace."""
        csv_content = """Header line 1
Header line 2
Header line 3
Header line 4
Buchungsdatum ; Wertstellung ; Status ; Zahlungspflichtige*r ; Zahlungsempfänger*in ; Verwendungszweck ; Betrag (€) ; IBAN
15.01.24;16.01.24;Buchung;Max Mustermann;Supermarket;Grocery shopping;50,25 €;DE89370400440532013000
"""

        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            suffix=".csv",
            encoding="utf-8",
        ) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            parser = DKBCSVParser()
            transactions = parser.parse_file(csv_path)

            # Should still parse correctly after stripping whitespace
            assert len(transactions) == 1
            assert transactions[0].recipient == "Supermarket"
        finally:
            Path(csv_path).unlink()

    def test_filter_by_date_range_all_in_range(self):
        """Test filtering transactions where all are in date range."""
        booking_date = datetime(2024, 1, 15)
        transactions = [
            Transaction(
                booking_date=booking_date,
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
                booking_date=booking_date,
                value_date=datetime(2024, 1, 20),
                status="Buchung",
                payer="Employer",
                recipient="Max Mustermann",
                purpose="Salary",
                transaction_type=TransactionType.INCOME,
                iban="DE89370400440532013000",
                amount=2000.00,
            ),
        ]

        parser = DKBCSVParser()
        filtered = parser.filter_by_date_range(
            transactions,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        assert len(filtered) == 2
        assert filtered == transactions

    def test_filter_by_date_range_some_in_range(self):
        """Test filtering transactions where some are in date range."""
        booking_date = datetime(2024, 1, 15)
        transactions = [
            Transaction(
                booking_date=booking_date,
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
                booking_date=booking_date,
                value_date=datetime(2024, 2, 20),
                status="Buchung",
                payer="Employer",
                recipient="Max Mustermann",
                purpose="Salary",
                transaction_type=TransactionType.INCOME,
                iban="DE89370400440532013000",
                amount=2000.00,
            ),
        ]

        parser = DKBCSVParser()
        filtered = parser.filter_by_date_range(
            transactions,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        assert len(filtered) == 1
        assert filtered[0].value_date == datetime(2024, 1, 16)

    def test_filter_by_date_range_none_in_range(self):
        """Test filtering transactions where none are in date range."""
        booking_date = datetime(2024, 1, 15)
        transactions = [
            Transaction(
                booking_date=booking_date,
                value_date=datetime(2024, 2, 16),
                status="Buchung",
                payer="Max Mustermann",
                recipient="Supermarket",
                purpose="Grocery shopping",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            ),
            Transaction(
                booking_date=booking_date,
                value_date=datetime(2024, 3, 20),
                status="Buchung",
                payer="Employer",
                recipient="Max Mustermann",
                purpose="Salary",
                transaction_type=TransactionType.INCOME,
                iban="DE89370400440532013000",
                amount=2000.00,
            ),
        ]

        parser = DKBCSVParser()
        filtered = parser.filter_by_date_range(
            transactions,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        assert len(filtered) == 0

    def test_filter_by_date_range_empty_list(self):
        """Test filtering empty transaction list."""
        parser = DKBCSVParser()
        filtered = parser.filter_by_date_range(
            [],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        assert len(filtered) == 0

    def test_filter_by_date_range_boundary_dates(self):
        """Test filtering with boundary dates (inclusive)."""
        booking_date = datetime(2024, 1, 15)
        transactions = [
            Transaction(
                booking_date=booking_date,
                value_date=datetime(2024, 1, 1),  # Start date
                status="Buchung",
                payer="Max Mustermann",
                recipient="Supermarket",
                purpose="Grocery shopping",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-50.25,
            ),
            Transaction(
                booking_date=booking_date,
                value_date=datetime(2024, 1, 31),  # End date
                status="Buchung",
                payer="Employer",
                recipient="Max Mustermann",
                purpose="Salary",
                transaction_type=TransactionType.INCOME,
                iban="DE89370400440532013000",
                amount=2000.00,
            ),
            Transaction(
                booking_date=booking_date,
                value_date=datetime(2023, 12, 31),  # Before start
                status="Buchung",
                payer="Max Mustermann",
                recipient="Store",
                purpose="Purchase",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-25.00,
            ),
            Transaction(
                booking_date=booking_date,
                value_date=datetime(2024, 2, 1),  # After end
                status="Buchung",
                payer="Max Mustermann",
                recipient="Store",
                purpose="Purchase",
                transaction_type=TransactionType.EXPENSE,
                iban="DE89370400440532013000",
                amount=-30.00,
            ),
        ]

        parser = DKBCSVParser()
        filtered = parser.filter_by_date_range(
            transactions,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        assert len(filtered) == 2
        assert filtered[0].value_date == datetime(2024, 1, 1)
        assert filtered[1].value_date == datetime(2024, 1, 31)
