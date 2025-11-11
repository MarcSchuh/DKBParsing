"""Unit tests for models.py."""

from datetime import datetime

from dkbparsing.models import (
    Category,
    ParsedTransaction,
    ParsingResult,
    Transaction,
    TransactionType,
)


class TestTransactionType:
    """Tests for TransactionType enum."""

    def test_income_value(self):
        """Test that INCOME has the correct value."""
        assert TransactionType.INCOME.value == "Eingang"

    def test_expense_value(self):
        """Test that EXPENSE has the correct value."""
        assert TransactionType.EXPENSE.value == "Ausgang"

    def test_enum_members(self):
        """Test that enum has both expected members."""
        assert len(TransactionType) == 2
        assert TransactionType.INCOME in TransactionType
        assert TransactionType.EXPENSE in TransactionType


class TestTransaction:
    """Tests for Transaction dataclass."""

    def test_transaction_creation(self):
        """Test creating a Transaction with all required fields."""
        booking_date = datetime(2024, 1, 15)
        value_date = datetime(2024, 1, 16)
        transaction = Transaction(
            booking_date=booking_date,
            value_date=value_date,
            status="Buchung",
            payer="Max Mustermann",
            recipient="Jane Doe",
            purpose="Test transaction",
            transaction_type=TransactionType.INCOME,
            iban="DE89370400440532013000",
            amount=100.50,
        )

        assert transaction.booking_date == booking_date
        assert transaction.value_date == value_date
        assert transaction.status == "Buchung"
        assert transaction.payer == "Max Mustermann"
        assert transaction.recipient == "Jane Doe"
        assert transaction.purpose == "Test transaction"
        assert transaction.transaction_type == TransactionType.INCOME
        assert transaction.iban == "DE89370400440532013000"
        assert transaction.amount == 100.50
        assert transaction.creditor_id is None
        assert transaction.mandate_reference is None
        assert transaction.customer_reference is None

    def test_transaction_with_optional_fields(self):
        """Test creating a Transaction with optional fields."""
        booking_date = datetime(2024, 1, 15)
        value_date = datetime(2024, 1, 16)
        transaction = Transaction(
            booking_date=booking_date,
            value_date=value_date,
            status="Buchung",
            payer="Max Mustermann",
            recipient="Jane Doe",
            purpose="Test transaction",
            transaction_type=TransactionType.EXPENSE,
            iban="DE89370400440532013000",
            amount=-50.25,
            creditor_id="DE98ZZZ09999999999",
            mandate_reference="MANDATE123",
            customer_reference="CUST456",
        )

        assert transaction.creditor_id == "DE98ZZZ09999999999"
        assert transaction.mandate_reference == "MANDATE123"
        assert transaction.customer_reference == "CUST456"

    def test_from_csv_row_income(self):
        """Test creating Transaction from CSV row with positive amount (income)."""
        row = {
            "Buchungsdatum": "15.01.24",
            "Wertstellung": "16.01.24",
            "Status": "Buchung",
            "Zahlungspflichtige*r": "Max Mustermann",
            "Zahlungsempfänger*in": "Jane Doe",
            "Verwendungszweck": "Test income",
            "Betrag (€)": "100,50 €",
            "IBAN": "DE89370400440532013000",
        }

        transaction = Transaction.from_csv_row(row)

        assert transaction.booking_date == datetime(2024, 1, 15)
        assert transaction.value_date == datetime(2024, 1, 16)
        assert transaction.status == "Buchung"
        assert transaction.payer == "Max Mustermann"
        assert transaction.recipient == "Jane Doe"
        assert transaction.purpose == "Test income"
        assert transaction.iban == "DE89370400440532013000"
        assert transaction.amount == 100.50
        assert transaction.transaction_type == TransactionType.INCOME

    def test_from_csv_row_expense(self):
        """Test creating Transaction from CSV row with negative amount (expense)."""
        row = {
            "Buchungsdatum": "20.02.24",
            "Wertstellung": "21.02.24",
            "Status": "Buchung",
            "Zahlungspflichtige*r": "Max Mustermann",
            "Zahlungsempfänger*in": "Supermarket",
            "Verwendungszweck": "Grocery shopping",
            "Betrag (€)": "-50,25 €",
            "IBAN": "DE89370400440532013000",
        }

        transaction = Transaction.from_csv_row(row)

        assert transaction.booking_date == datetime(2024, 2, 20)
        assert transaction.value_date == datetime(2024, 2, 21)
        assert transaction.amount == -50.25
        assert transaction.transaction_type == TransactionType.EXPENSE

    def test_from_csv_row_with_optional_fields(self):
        """Test creating Transaction from CSV row with optional fields."""
        row = {
            "Buchungsdatum": "15.01.24",
            "Wertstellung": "16.01.24",
            "Status": "Buchung",
            "Zahlungspflichtige*r": "Max Mustermann",
            "Zahlungsempfänger*in": "Jane Doe",
            "Verwendungszweck": "Test transaction",
            "Betrag (€)": "100,50 €",
            "IBAN": "DE89370400440532013000",
            "Gläubiger-ID": "DE98ZZZ09999999999",
            "Mandatsreferenz": "MANDATE123",
            "Kundenreferenz": "CUST456",
        }

        transaction = Transaction.from_csv_row(row)

        assert transaction.creditor_id == "DE98ZZZ09999999999"
        assert transaction.mandate_reference == "MANDATE123"
        assert transaction.customer_reference == "CUST456"

    def test_from_csv_row_amount_parsing(self):
        """Test parsing different German number formats."""
        test_cases = [
            ("100,50 €", 100.50),
            ("1.000,50 €", 1000.50),
            ("-50,25 €", -50.25),
            ("-1.234,56 €", -1234.56),
            ("0,00 €", 0.0),
        ]

        base_row = {
            "Buchungsdatum": "15.01.24",
            "Wertstellung": "16.01.24",
            "Status": "Buchung",
            "Zahlungspflichtige*r": "Max Mustermann",
            "Zahlungsempfänger*in": "Jane Doe",
            "Verwendungszweck": "Test",
            "IBAN": "DE89370400440532013000",
        }

        for amount_str, expected_amount in test_cases:
            row = {**base_row, "Betrag (€)": amount_str}
            transaction = Transaction.from_csv_row(row)
            assert transaction.amount == expected_amount

    def test_from_csv_row_zero_amount(self):
        """Test that zero amount is treated as income."""
        row = {
            "Buchungsdatum": "15.01.24",
            "Wertstellung": "16.01.24",
            "Status": "Buchung",
            "Zahlungspflichtige*r": "Max Mustermann",
            "Zahlungsempfänger*in": "Jane Doe",
            "Verwendungszweck": "Test",
            "Betrag (€)": "0,00 €",
            "IBAN": "DE89370400440532013000",
        }

        transaction = Transaction.from_csv_row(row)
        assert transaction.amount == 0.0
        assert transaction.transaction_type == TransactionType.INCOME


class TestCategory:
    """Tests for Category dataclass."""

    def test_category_creation(self):
        """Test creating a Category with required fields."""
        category = Category(
            name="groceries",
            display_name="Groceries",
            search_strings=["supermarket", "grocery", "food"],
        )

        assert category.name == "groceries"
        assert category.display_name == "Groceries"
        assert category.search_strings == ["supermarket", "grocery", "food"]
        assert category.regex_patterns == []

    def test_category_with_regex_patterns(self):
        """Test creating a Category with regex patterns."""
        category = Category(
            name="salary",
            display_name="Salary",
            search_strings=["salary", "wage"],
            regex_patterns=[r"^SALARY", r"PAYROLL"],
        )

        assert category.regex_patterns == [r"^SALARY", r"PAYROLL"]

    def test_category_regex_patterns_default(self):
        """Test that regex_patterns defaults to empty list if None."""
        category = Category(
            name="test",
            display_name="Test",
            search_strings=["test"],
            regex_patterns=None,
        )

        assert category.regex_patterns == []


class TestParsedTransaction:
    """Tests for ParsedTransaction dataclass."""

    def test_parsed_transaction_creation(self):
        """Test creating a ParsedTransaction with transaction and category."""
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

        parsed = ParsedTransaction(transaction=transaction, category=category)

        assert parsed.transaction == transaction
        assert parsed.category == category
        assert parsed.search_matches == []

    def test_parsed_transaction_without_category(self):
        """Test creating a ParsedTransaction without category."""
        booking_date = datetime(2024, 1, 15)
        value_date = datetime(2024, 1, 16)
        transaction = Transaction(
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

        parsed = ParsedTransaction(transaction=transaction, category=None)

        assert parsed.transaction == transaction
        assert parsed.category is None
        assert parsed.search_matches == []

    def test_parsed_transaction_with_search_matches(self):
        """Test creating a ParsedTransaction with search matches."""
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

        parsed = ParsedTransaction(
            transaction=transaction,
            category=category,
            search_matches=["supermarket"],
        )

        assert parsed.search_matches == ["supermarket"]

    def test_parsed_transaction_search_matches_default(self):
        """Test that search_matches defaults to empty list if None."""
        booking_date = datetime(2024, 1, 15)
        value_date = datetime(2024, 1, 16)
        transaction = Transaction(
            booking_date=booking_date,
            value_date=value_date,
            status="Buchung",
            payer="Max Mustermann",
            recipient="Test",
            purpose="Test",
            transaction_type=TransactionType.EXPENSE,
            iban="DE89370400440532013000",
            amount=-10.00,
        )

        parsed = ParsedTransaction(
            transaction=transaction,
            category=None,
            search_matches=None,
        )

        assert parsed.search_matches == []


class TestParsingResult:
    """Tests for ParsingResult dataclass."""

    def test_parsing_result_creation(self):
        """Test creating a ParsingResult with all fields."""
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

        assert len(result.parsed_transactions) == 1
        assert len(result.uncategorized_transactions) == 1
        assert result.category_totals == {"Groceries": -50.25}
        assert result.total_income == 2000.00
        assert result.total_expenses == -50.25

    def test_parsing_result_empty(self):
        """Test creating an empty ParsingResult."""
        result = ParsingResult(
            parsed_transactions=[],
            uncategorized_transactions=[],
            category_totals={},
            total_income=0.0,
            total_expenses=0.0,
        )

        assert result.parsed_transactions == []
        assert result.uncategorized_transactions == []
        assert result.category_totals == {}
        assert result.total_income == 0.0
        assert result.total_expenses == 0.0
