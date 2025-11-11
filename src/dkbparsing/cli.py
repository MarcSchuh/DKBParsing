"""
Command-line interface for DKB parsing.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from .parser import DKBParser

logger = logging.getLogger(__name__)


class FileSavingError(Exception):
    """Exception raised when a file cannot be saved."""


def load_config(config_file: str) -> dict:
    """Load CLI configuration from JSON file."""

    config_path = Path(config_file)
    if not config_path.exists():
        logger.debug(f"CLI config file {config_file} does not exist")
        return {}

    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        logger.debug(f"Loaded CLI config from {config_file}")
        return config
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in CLI config file {config_file}: {e}")
        return {}
    except OSError as e:
        logger.warning(f"Failed to load CLI config from {config_file}: {e}")
        return {}


def save_config(config_file: str, config: dict) -> None:
    """Save CLI configuration to JSON file."""
    try:
        config_path = Path(config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"CLI configuration saved to {config_file}")
    except OSError as e:
        logger.error(f"Failed to save CLI config to {config_file}: {e}")
        raise FileSavingError(
            f"Failed to save CLI config to {config_file}: {e}",
        ) from e


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Parse DKB CSV exports and categorize transactions",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (INFO level)",
    )

    parser.add_argument(
        "--config",
        help="Path to CLI configuration file (contains defaults for config, manual-assignments, template, output)",
    )

    parser.add_argument(
        "csv_file",
        nargs="?",
        help="Path to the DKB CSV file (optional if only managing categories/assignments)",
    )

    parser.add_argument(
        "--start-date",
        help="Start date filter (DD.MM.YY format)",
    )

    parser.add_argument(
        "--end-date",
        help="End date filter (DD.MM.YY format)",
    )

    parser.add_argument(
        "--add-manual",
        nargs=4,
        metavar=("DATE", "RECIPIENT", "PURPOSE", "CATEGORY"),
        help="Add manual assignment (DATE in DD.MM.YY format). Amount is automatically taken from transaction data. Requires --config with manual_assignments_file set.",
    )

    parser.add_argument(
        "--add-category",
        nargs=3,
        metavar=("NAME", "DISPLAY_NAME", "SEARCH_STRING"),
        help="Add a new category. Requires --config with category_config set.",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
    )

    # Load config
    config = load_config(args.config)

    # Load configuration from CLI config
    category_file_str = config.get("category_config")
    manual_assignments_file_str = config.get("manual_assignments_file")
    output_template = config.get("output_template")
    output_format = config.get("output_format", "excel")

    # Ensure category_file is set (required)
    if not args.config:
        logger.error(
            "Error: --config is required. Please provide a CLI config file with category_config set.",
        )
        sys.exit(1)

    if not category_file_str:
        logger.error(
            "Error: category_config must be set in CLI config file",
        )
        sys.exit(1)

    if not manual_assignments_file_str:
        logger.error(
            "Error: manual_assignments_file must be set in CLI config file",
        )
        sys.exit(1)

    category_file = Path(category_file_str)
    manual_assignments_file = Path(manual_assignments_file_str)

    # Initialize parser
    dkb_parser = DKBParser(category_file, manual_assignments_file)

    # Handle category management
    if args.add_category:
        name, display_name, search_string = args.add_category
        dkb_parser.add_category(name, display_name, [search_string])
        logger.info(f"Added category '{name}' with search string '{search_string}'")
        return

    # Handle manual assignments
    if args.add_manual:
        if len(args.add_manual) != 4:
            logger.error(
                "Error: --add-manual requires exactly 4 arguments: DATE RECIPIENT PURPOSE CATEGORY",
            )
            logger.error(
                f"Received {len(args.add_manual)} arguments: {args.add_manual}",
            )
            sys.exit(1)

        date, recipient, purpose, category = args.add_manual
        dkb_parser.add_manual_assignment(date, recipient, purpose, category)
        logger.info(f"Added manual assignment: {date} {recipient} -> {category}")
        return

    # Only parse CSV if csv_file is provided
    if not args.csv_file:
        # If no CSV file and no category/manual assignment operations, show help
        if not (
            args.add_category
            or args.add_manual
            or args.add_search_string
            or args.remove_search_string
        ):
            parser.error(
                "csv_file is required unless managing categories or manual assignments",
            )
        return

    # Parse dates if provided
    start_date = None
    end_date = None

    if args.start_date:
        start_date = datetime.strptime(args.start_date, "%d.%m.%y")

    if args.end_date:
        end_date = datetime.strptime(args.end_date, "%d.%m.%y")

    # Parse the CSV file
    try:
        result = dkb_parser.parse_file(args.csv_file, start_date, end_date)
    except (ValueError, FileNotFoundError, OSError) as e:
        logger.error(f"Error parsing file: {e}")
        sys.exit(1)

    # Generate output
    outputs_printed = []

    if output_format in ["excel", "both"]:
        excel_output = dkb_parser.format_for_excel(result)
        # Output to stdout for user to copy/paste
        logger.info(excel_output)
        outputs_printed.append("excel")

    if output_format in ["summary", "both"]:
        if outputs_printed:
            logger.info("\n" + "=" * 50 + "\n")
        summary_output = dkb_parser.format_summary(result)
        # Output to stdout for user to copy/paste
        logger.info(summary_output)
        outputs_printed.append("summary")

    if output_format in ["household", "both"]:
        if not output_template:
            logger.error(
                "Error: output_template required for household output (set in CLI config)",
            )
            sys.exit(1)

        if outputs_printed:
            logger.info("\n" + "=" * 50 + "\n")

        # Template contains category names directly
        household_output = dkb_parser.format_household(result, output_template)
        # Output to stdout for user to copy/paste
        logger.info(household_output)
        outputs_printed.append("household")


if __name__ == "__main__":
    main()
