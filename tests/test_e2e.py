"""End-to-end tests for the complete DKB parsing workflow."""

import json
import subprocess
import tempfile
from pathlib import Path

from dkbparsing.parser import DKBParser


class TestEndToEnd:
    """End-to-end tests using real files and CLI."""

    def test_e2e_complete_workflow(self):
        """Test complete workflow: CSV parsing, categorization, and output generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup test files
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual_assignments.json"
            template_file = Path(tmpdir) / "household_template.txt"
            csv_file = Path(tmpdir) / "test_transactions.csv"
            config_file = Path(tmpdir) / "cli_config.json"

            # Create categories file
            categories_data = {
                "groceries": {
                    "display_name": "Lebensmittel",
                    "search_strings": ["REWE", "EDEKA", "Supermarket"],
                    "regex_patterns": [],
                },
                "salary": {
                    "display_name": "Einkommen",
                    "search_strings": ["Salary", "Gehalt"],
                    "regex_patterns": [],
                },
                "rent": {
                    "display_name": "Miete",
                    "search_strings": ["Miete", "Rent"],
                    "regex_patterns": [],
                },
            }
            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(categories_data, f, indent=2, ensure_ascii=False)

            # Create manual assignments file
            # Note: date must match value_date from CSV (17.01.24)
            manual_data = {
                "manual_assignments": [
                    {
                        "date": "17.01.24",
                        "recipient": "Max Mustermann",
                        "purpose": "Special Payment",
                        "category": "salary",
                    },
                ],
            }
            with open(manual_file, "w", encoding="utf-8") as f:
                json.dump(manual_data, f, indent=2, ensure_ascii=False)

            # Create household template
            template_content = """Einkommen

Miete
Lebensmittel
"""
            with open(template_file, "w", encoding="utf-8") as f:
                f.write(template_content)

            # Create CSV file with DKB format
            # Note: Manual assignment uses value_date (17.01.24), so CSV should match
            csv_content = """Header line 1
Header line 2
Header line 3
Header line 4
Buchungsdatum;Wertstellung;Status;Zahlungspflichtige*r;Zahlungsempfänger*in;Verwendungszweck;Betrag (€);IBAN
15.01.24;16.01.24;Buchung;Employer;Max Mustermann;Salary January;2000,00 €;DE89370400440532013000
20.01.24;21.01.24;Buchung;Max Mustermann;REWE Supermarket;Grocery shopping;-50,25 €;DE89370400440532013000
25.01.24;26.01.24;Buchung;Max Mustermann;Landlord;Miete;-800,00 €;DE89370400440532013000
16.01.24;17.01.24;Buchung;Client;Max Mustermann;Special Payment;500,00 €;DE89370400440532013000
"""
            with open(csv_file, "w", encoding="utf-8") as f:
                f.write(csv_content)

            # Create CLI config
            cli_config = {
                "category_config": str(category_file),
                "manual_assignments_file": str(manual_file),
                "output_template": str(template_file),
                "output_format": "both",
            }
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(cli_config, f, indent=2, ensure_ascii=False)

            # Test using DKBParser directly
            parser = DKBParser(category_file, manual_file)
            result = parser.parse_file(str(csv_file))

            # Verify results
            assert len(result.parsed_transactions) == 4
            # Special Payment should be categorized via manual assignment
            # Check that we have categorized transactions
            categorized_count = sum(
                1 for pt in result.parsed_transactions if pt.category
            )
            assert categorized_count >= 3  # At least 3 should be categorized

            # Check category totals
            assert "Lebensmittel" in result.category_totals
            assert "Einkommen" in result.category_totals
            assert "Miete" in result.category_totals

            # Verify amounts
            assert result.category_totals["Lebensmittel"] == -50.25
            assert result.category_totals["Miete"] == -800.00
            # Einkommen should include both salary (2000) and special payment (500) = 2500
            assert result.category_totals["Einkommen"] == 2500.00

            # Verify income and expenses
            assert result.total_income == 2500.00
            assert result.total_expenses == -850.25

            # Test Excel formatting
            excel_output = parser.format_for_excel(result)
            assert "Lebensmittel" in excel_output
            assert "Miete" in excel_output
            assert "Einkommen" in excel_output
            assert "-50,25" in excel_output or "-50,2" in excel_output
            assert "-800,0" in excel_output or "-800" in excel_output

            # Test summary formatting
            summary_output = parser.format_summary(result)
            assert "Total transactions processed: 4" in summary_output
            assert "Categorized transactions: 4" in summary_output
            assert "Total income: 2500.00" in summary_output
            assert "Total expenses: 850.25" in summary_output

            # Test household formatting
            household_output = parser.format_household(result, str(template_file))
            lines = household_output.split("\n")
            # Should have values for Einkommen, Miete, Lebensmittel
            assert len([line for line in lines if line.strip()]) >= 3

    def test_e2e_with_date_filter(self):
        """Test E2E workflow with date filtering."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual_assignments.json"
            csv_file = Path(tmpdir) / "test_transactions.csv"

            # Create minimal categories
            categories_data = {
                "groceries": {
                    "display_name": "Lebensmittel",
                    "search_strings": ["REWE"],
                    "regex_patterns": [],
                },
            }
            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(categories_data, f, indent=2, ensure_ascii=False)

            # Create empty manual assignments
            with open(manual_file, "w", encoding="utf-8") as f:
                json.dump({"manual_assignments": []}, f)

            # Create CSV with transactions spanning multiple months
            csv_content = """Header line 1
Header line 2
Header line 3
Header line 4
Buchungsdatum;Wertstellung;Status;Zahlungspflichtige*r;Zahlungsempfänger*in;Verwendungszweck;Betrag (€);IBAN
15.01.24;16.01.24;Buchung;Test;REWE;Grocery;-50,00 €;DE89370400440532013000
15.02.24;16.02.24;Buchung;Test;REWE;Grocery;-75,00 €;DE89370400440532013000
15.03.24;16.03.24;Buchung;Test;REWE;Grocery;-100,00 €;DE89370400440532013000
"""
            with open(csv_file, "w", encoding="utf-8") as f:
                f.write(csv_content)

            # Test with date filter (only January)
            parser = DKBParser(category_file, manual_file)
            from datetime import datetime

            result = parser.parse_file(
                str(csv_file),
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
            )

            # Should only have January transaction
            assert len(result.parsed_transactions) == 1
            assert result.category_totals["Lebensmittel"] == -50.00

    def test_e2e_uncategorized_transactions(self):
        """Test E2E workflow with uncategorized transactions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual_assignments.json"
            csv_file = Path(tmpdir) / "test_transactions.csv"

            # Create minimal categories
            categories_data = {
                "groceries": {
                    "display_name": "Lebensmittel",
                    "search_strings": ["REWE"],
                    "regex_patterns": [],
                },
            }
            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(categories_data, f, indent=2, ensure_ascii=False)

            # Create empty manual assignments
            with open(manual_file, "w", encoding="utf-8") as f:
                json.dump({"manual_assignments": []}, f)

            # Create CSV with categorized and uncategorized transactions
            csv_content = """Header line 1
Header line 2
Header line 3
Header line 4
Buchungsdatum;Wertstellung;Status;Zahlungspflichtige*r;Zahlungsempfänger*in;Verwendungszweck;Betrag (€);IBAN
15.01.24;16.01.24;Buchung;Test;REWE;Grocery;-50,00 €;DE89370400440532013000
20.01.24;21.01.24;Buchung;Test;Unknown Store;Unknown purchase;-25,00 €;DE89370400440532013000
"""
            with open(csv_file, "w", encoding="utf-8") as f:
                f.write(csv_content)

            parser = DKBParser(category_file, manual_file)
            result = parser.parse_file(str(csv_file))

            # Should have 2 transactions
            assert len(result.parsed_transactions) == 2
            # One should be categorized, one uncategorized
            assert len(result.uncategorized_transactions) == 1
            assert result.uncategorized_transactions[0].recipient == "Unknown Store"

            # Excel output should show uncategorized (default is True)
            excel_output = parser.format_for_excel(result)
            assert "Uncategorized transactions:" in excel_output
            assert "Unknown Store" in excel_output

    def test_e2e_cli_integration(self):
        """Test E2E workflow using CLI subprocess."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual_assignments.json"
            template_file = Path(tmpdir) / "household_template.txt"
            csv_file = Path(tmpdir) / "test_transactions.csv"
            config_file = Path(tmpdir) / "cli_config.json"

            # Create categories file
            categories_data = {
                "groceries": {
                    "display_name": "Lebensmittel",
                    "search_strings": ["REWE"],
                    "regex_patterns": [],
                },
            }
            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(categories_data, f, indent=2, ensure_ascii=False)

            # Create empty manual assignments
            with open(manual_file, "w", encoding="utf-8") as f:
                json.dump({"manual_assignments": []}, f)

            # Create household template
            with open(template_file, "w", encoding="utf-8") as f:
                f.write("Lebensmittel\n")

            # Create CSV file
            csv_content = """Header line 1
Header line 2
Header line 3
Header line 4
Buchungsdatum;Wertstellung;Status;Zahlungspflichtige*r;Zahlungsempfänger*in;Verwendungszweck;Betrag (€);IBAN
15.01.24;16.01.24;Buchung;Test;REWE;Grocery;-50,00 €;DE89370400440532013000
"""
            with open(csv_file, "w", encoding="utf-8") as f:
                f.write(csv_content)

            # Create CLI config
            cli_config = {
                "category_config": str(category_file),
                "manual_assignments_file": str(manual_file),
                "output_template": str(template_file),
                "output_format": "excel",
            }
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(cli_config, f, indent=2, ensure_ascii=False)

            # Run CLI via subprocess
            import sys

            python_executable = sys.executable
            result = subprocess.run(
                [
                    python_executable,
                    "-m",
                    "dkbparsing.cli",
                    "--config",
                    str(config_file),
                    str(csv_file),
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            # CLI should succeed
            assert result.returncode == 0

            # Output should contain expected content
            assert "Lebensmittel" in result.stdout or "Lebensmittel" in result.stderr
