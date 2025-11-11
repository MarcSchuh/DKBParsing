"""Unit tests for cli.py."""

import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dkbparsing.category_manager import ManualAssignmentCategoryError
from dkbparsing.cli import FileSavingError, load_config, main, save_config


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_existing_file(self):
        """Test loading config from existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_data = {
                "category_config": "categories.json",
                "manual_assignments_file": "manual.json",
                "output_format": "excel",
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f)

            result = load_config(str(config_file))

            assert result == config_data

    def test_load_config_nonexistent_file(self):
        """Test loading config from non-existent file."""
        result = load_config("/nonexistent/path/config.json")

        assert result == {}

    def test_load_config_invalid_json(self):
        """Test loading config with invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"

            with open(config_file, "w", encoding="utf-8") as f:
                f.write("invalid json {")

            result = load_config(str(config_file))

            # Should return empty dict on error
            assert result == {}

    def test_load_config_empty_file(self):
        """Test loading config from empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"

            with open(config_file, "w", encoding="utf-8") as f:
                f.write("{}")

            result = load_config(str(config_file))

            assert result == {}


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_config_creates_file(self):
        """Test that save_config creates the file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_data = {
                "category_config": "categories.json",
                "manual_assignments_file": "manual.json",
            }

            save_config(str(config_file), config_data)

            assert config_file.exists()

    def test_save_config_creates_directory(self):
        """Test that save_config creates directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "subdir" / "config.json"
            config_data = {"test": "value"}

            save_config(str(config_file), config_data)

            assert config_file.parent.exists()
            assert config_file.exists()

    def test_save_config_writes_correct_data(self):
        """Test that save_config writes correct data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_data = {
                "category_config": "categories.json",
                "manual_assignments_file": "manual.json",
                "output_format": "excel",
            }

            save_config(str(config_file), config_data)

            with open(config_file, encoding="utf-8") as f:
                loaded_data = json.load(f)

            assert loaded_data == config_data

    def test_save_config_raises_on_error(self):
        """Test that save_config raises exception on error."""
        # Try to save to invalid path (if possible)
        with pytest.raises(FileSavingError):
            # This might not work on all systems, but we test the error handling
            save_config("/root/invalid/path/config.json", {"test": "value"})


class TestCLIMain:
    """Tests for main() function."""

    def test_main_add_category(self):
        """Test adding a category via CLI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"
            config_file = Path(tmpdir) / "config.json"

            config_data = {
                "category_config": str(category_file),
                "manual_assignments_file": str(manual_file),
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f)

            with (
                patch(
                    "sys.argv",
                    [
                        "cli.py",
                        "--config",
                        str(config_file),
                        "--add-category",
                        "groceries",
                        "Groceries",
                        "supermarket",
                    ],
                ),
                patch("dkbparsing.cli.logger") as mock_logger,
            ):
                main()

                mock_logger.info.assert_called()
                # Verify category was added by checking if file exists or was modified
                # (actual verification would require checking the file content)

    def test_main_add_manual_assignment(self):
        """Test adding a manual assignment via CLI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"
            config_file = Path(tmpdir) / "config.json"

            config_data = {
                "category_config": str(category_file),
                "manual_assignments_file": str(manual_file),
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f)

            # Create category first
            from dkbparsing.category_manager import CategoryManager
            from dkbparsing.models import Category

            manager = CategoryManager(category_file, manual_file)
            manager.add_category(
                Category(
                    name="test_category",
                    display_name="Test Category",
                    search_strings=[],
                ),
            )

            with (
                patch(
                    "sys.argv",
                    [
                        "cli.py",
                        "--config",
                        str(config_file),
                        "--add-manual",
                        "16.01.24",
                        "Test Recipient",
                        "Test Purpose",
                        "test_category",
                    ],
                ),
                patch("dkbparsing.cli.logger") as mock_logger,
            ):
                main()

                mock_logger.info.assert_called()

    def test_main_add_manual_assignment_with_invalid_category(self):
        """Test that adding manual assignment with invalid category raises ManualAssignmentCategoryError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"
            config_file = Path(tmpdir) / "config.json"

            config_data = {
                "category_config": str(category_file),
                "manual_assignments_file": str(manual_file),
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f)

            with (
                patch(
                    "sys.argv",
                    [
                        "cli.py",
                        "--config",
                        str(config_file),
                        "--add-manual",
                        "16.01.24",
                        "Test Recipient",
                        "Test Purpose",
                        "nonexistent_category",
                    ],
                ),
                pytest.raises(ManualAssignmentCategoryError),
            ):
                main()

    def test_main_parse_csv_file(self):
        """Test parsing a CSV file via CLI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"
            config_file = Path(tmpdir) / "config.json"
            csv_file = Path(tmpdir) / "test.csv"

            # Create minimal CSV file
            with open(csv_file, "w", encoding="utf-8") as f:
                f.write("Header\n")

            config_data = {
                "category_config": str(category_file),
                "manual_assignments_file": str(manual_file),
                "output_format": "excel",
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f)

            with (
                patch(
                    "sys.argv",
                    ["cli.py", "--config", str(config_file), str(csv_file)],
                ),
                patch("dkbparsing.cli.DKBParser") as mock_parser_class,
            ):
                mock_parser = Mock()
                mock_parser_class.return_value = mock_parser

                mock_result = Mock()
                mock_result.parsed_transactions = []
                mock_result.uncategorized_transactions = []
                mock_result.category_totals = {}
                mock_result.total_income = 0.0
                mock_result.total_expenses = 0.0

                mock_parser.parse_file = Mock(return_value=mock_result)
                mock_parser.format_for_excel = Mock(return_value="excel output")

                with patch("dkbparsing.cli.logger") as mock_logger:
                    main()

                    mock_parser.parse_file.assert_called_once()
                    mock_parser.format_for_excel.assert_called_once_with(mock_result)
                    mock_logger.info.assert_called()

    def test_main_parse_csv_with_date_filter(self):
        """Test parsing CSV with date filters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"
            config_file = Path(tmpdir) / "config.json"
            csv_file = Path(tmpdir) / "test.csv"

            with open(csv_file, "w", encoding="utf-8") as f:
                f.write("Header\n")

            config_data = {
                "category_config": str(category_file),
                "manual_assignments_file": str(manual_file),
                "output_format": "excel",
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f)

            with (
                patch(
                    "sys.argv",
                    [
                        "cli.py",
                        "--config",
                        str(config_file),
                        str(csv_file),
                        "--start-date",
                        "01.01.24",
                        "--end-date",
                        "31.01.24",
                    ],
                ),
                patch("dkbparsing.cli.DKBParser") as mock_parser_class,
            ):
                mock_parser = Mock()
                mock_parser_class.return_value = mock_parser

                mock_result = Mock()
                mock_result.parsed_transactions = []
                mock_result.uncategorized_transactions = []
                mock_result.category_totals = {}
                mock_result.total_income = 0.0
                mock_result.total_expenses = 0.0

                mock_parser.parse_file = Mock(return_value=mock_result)
                mock_parser.format_for_excel = Mock(return_value="excel output")

                with patch("dkbparsing.cli.logger"):
                    main()

                    # Verify parse_file was called with date filters
                    call_args = mock_parser.parse_file.call_args
                    assert call_args[0][0] == str(csv_file)
                    assert call_args[0][1] is not None  # start_date
                    assert call_args[0][2] is not None  # end_date

    def test_main_output_format_summary(self):
        """Test output format summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"
            config_file = Path(tmpdir) / "config.json"
            csv_file = Path(tmpdir) / "test.csv"

            with open(csv_file, "w", encoding="utf-8") as f:
                f.write("Header\n")

            config_data = {
                "category_config": str(category_file),
                "manual_assignments_file": str(manual_file),
                "output_format": "summary",
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f)

            with (
                patch(
                    "sys.argv",
                    ["cli.py", "--config", str(config_file), str(csv_file)],
                ),
                patch("dkbparsing.cli.DKBParser") as mock_parser_class,
            ):
                mock_parser = Mock()
                mock_parser_class.return_value = mock_parser

                mock_result = Mock()
                mock_result.parsed_transactions = []
                mock_result.uncategorized_transactions = []
                mock_result.category_totals = {}
                mock_result.total_income = 0.0
                mock_result.total_expenses = 0.0

                mock_parser.parse_file = Mock(return_value=mock_result)
                mock_parser.format_summary = Mock(return_value="summary output")

                with patch("dkbparsing.cli.logger") as mock_logger:
                    main()

                    mock_parser.format_summary.assert_called_once_with(mock_result)
                    mock_logger.info.assert_called()

    def test_main_output_format_household(self):
        """Test output format household."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"
            config_file = Path(tmpdir) / "config.json"
            csv_file = Path(tmpdir) / "test.csv"
            template_file = Path(tmpdir) / "template.txt"

            with open(csv_file, "w", encoding="utf-8") as f:
                f.write("Header\n")

            with open(template_file, "w", encoding="utf-8") as f:
                f.write("Groceries\n")

            config_data = {
                "category_config": str(category_file),
                "manual_assignments_file": str(manual_file),
                "output_format": "household",
                "output_template": str(template_file),
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f)

            with (
                patch(
                    "sys.argv",
                    ["cli.py", "--config", str(config_file), str(csv_file)],
                ),
                patch("dkbparsing.cli.DKBParser") as mock_parser_class,
            ):
                mock_parser = Mock()
                mock_parser_class.return_value = mock_parser

                mock_result = Mock()
                mock_result.parsed_transactions = []
                mock_result.uncategorized_transactions = []
                mock_result.category_totals = {}
                mock_result.total_income = 0.0
                mock_result.total_expenses = 0.0

                mock_parser.parse_file = Mock(return_value=mock_result)
                mock_parser.format_household = Mock(return_value="household output")

                with patch("dkbparsing.cli.logger") as mock_logger:
                    main()

                    mock_parser.format_household.assert_called_once_with(
                        mock_result,
                        str(template_file),
                    )
                    mock_logger.info.assert_called()

    def test_main_output_format_household_missing_template_exits(self):
        """Test that household format exits when template is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"
            config_file = Path(tmpdir) / "config.json"
            csv_file = Path(tmpdir) / "test.csv"

            with open(csv_file, "w", encoding="utf-8") as f:
                f.write("Header\n")

            config_data = {
                "category_config": str(category_file),
                "manual_assignments_file": str(manual_file),
                "output_format": "household",
                # output_template missing
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f)

            with (
                patch(
                    "sys.argv",
                    ["cli.py", "--config", str(config_file), str(csv_file)],
                ),
                patch("dkbparsing.cli.DKBParser") as mock_parser_class,
            ):
                mock_parser = Mock()
                mock_parser_class.return_value = mock_parser

                mock_result = Mock()
                mock_result.parsed_transactions = []
                mock_result.uncategorized_transactions = []
                mock_result.category_totals = {}
                mock_result.total_income = 0.0
                mock_result.total_expenses = 0.0

                mock_parser.parse_file = Mock(return_value=mock_result)

                with (
                    patch("sys.exit") as mock_exit,
                    patch(
                        "dkbparsing.cli.logger",
                    ) as mock_logger,
                ):
                    main()

                    mock_exit.assert_called_once_with(1)
                    mock_logger.error.assert_called()

    def test_main_output_format_both(self):
        """Test output format both (excel and summary)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"
            config_file = Path(tmpdir) / "config.json"
            csv_file = Path(tmpdir) / "test.csv"

            with open(csv_file, "w", encoding="utf-8") as f:
                f.write("Header\n")

            config_data = {
                "category_config": str(category_file),
                "manual_assignments_file": str(manual_file),
                "output_format": "both",
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f)

            with (
                patch(
                    "sys.argv",
                    ["cli.py", "--config", str(config_file), str(csv_file)],
                ),
                patch("dkbparsing.cli.DKBParser") as mock_parser_class,
            ):
                mock_parser = Mock()
                mock_parser_class.return_value = mock_parser

                mock_result = Mock()
                mock_result.parsed_transactions = []
                mock_result.uncategorized_transactions = []
                mock_result.category_totals = {}
                mock_result.total_income = 0.0
                mock_result.total_expenses = 0.0

                mock_parser.parse_file = Mock(return_value=mock_result)
                mock_parser.format_for_excel = Mock(return_value="excel output")
                mock_parser.format_summary = Mock(return_value="summary output")

                with (
                    patch("dkbparsing.cli.logger") as mock_logger,
                    patch(
                        "sys.exit",
                    ),
                ):
                    main()

                    mock_parser.format_for_excel.assert_called_once()
                    mock_parser.format_summary.assert_called_once()
                    # Should log both outputs with separator
                    assert mock_logger.info.call_count >= 2

    def test_main_verbose_logging(self):
        """Test that --verbose enables verbose logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"
            config_file = Path(tmpdir) / "config.json"

            config_data = {
                "category_config": str(category_file),
                "manual_assignments_file": str(manual_file),
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f)

            with (
                patch(
                    "sys.argv",
                    ["cli.py", "--config", str(config_file), "--verbose"],
                ),
                patch("dkbparsing.cli.logging.basicConfig") as mock_basic_config,
                patch(
                    "dkbparsing.cli.argparse.ArgumentParser",
                ) as mock_parser_class,
            ):
                mock_parser = Mock()
                mock_parser_class.return_value = mock_parser
                mock_args = Mock()
                mock_args.config = str(config_file)
                mock_args.verbose = True
                mock_args.csv_file = None
                mock_args.add_category = None
                mock_args.add_manual = None
                mock_args.start_date = None
                mock_args.end_date = None
                mock_parser.parse_args.return_value = mock_args
                with (
                    patch("dkbparsing.cli.DKBParser"),
                    patch(
                        "dkbparsing.cli.load_config",
                        return_value=config_data,
                    ),
                    patch("sys.exit"),
                ):
                    main()

                    # Verify logging was configured with DEBUG level
                    call_kwargs = mock_basic_config.call_args[1]
                    assert call_kwargs["level"] == logging.DEBUG

    def test_main_no_csv_file_no_operations(self):
        """Test that main shows error when no CSV file and no operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            category_file = Path(tmpdir) / "categories.json"
            manual_file = Path(tmpdir) / "manual.json"
            config_file = Path(tmpdir) / "config.json"

            config_data = {
                "category_config": str(category_file),
                "manual_assignments_file": str(manual_file),
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f)

            with (
                patch(
                    "sys.argv",
                    ["cli.py", "--config", str(config_file)],
                ),
                patch("dkbparsing.cli.argparse.ArgumentParser") as mock_parser_class,
            ):
                mock_parser = Mock()
                mock_parser_class.return_value = mock_parser
                mock_args = Mock()
                mock_args.config = str(config_file)
                mock_args.csv_file = None
                mock_args.add_category = None
                mock_args.add_manual = None
                mock_args.add_search_string = None
                mock_args.remove_search_string = None
                mock_args.verbose = False
                mock_args.start_date = None
                mock_args.end_date = None
                mock_parser.parse_args.return_value = mock_args
                mock_parser.error = Mock(side_effect=SystemExit)

                with (
                    patch(
                        "dkbparsing.cli.load_config",
                        return_value=config_data,
                    ),
                    patch("dkbparsing.cli.logger"),
                ):
                    # This should call parser.error()
                    with pytest.raises(SystemExit):
                        main()

                    # Verify error was called
                    mock_parser.error.assert_called()
