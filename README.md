# DKB Parsing

A Python tool for parsing and categorizing DKB (Deutsche Kreditbank) account statement CSV exports.
Automatically categorizes transactions using search strings and regex patterns, supports manual assignments, and generates Excel-compatible output for easy integration into your budget spreadsheets.

## Getting Ready

### Prerequisites

This project uses [uv](https://github.com/astral-sh/uv), a fast Python package installer and resolver.

**Install uv** (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installation

```bash
# Sync dependencies and install the package (includes dev dependencies)
uv sync

# Or sync only production dependencies
uv sync --no-dev
```

This will create a virtual environment and install all dependencies from `pyproject.toml`.

## Development

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality before commits. These hooks run:
- **Ruff** for linting and formatting
- **MyPy** for type checking
- Various file checks (YAML, JSON, TOML validation, trailing whitespace, etc.)

**Setup:**
```bash
# Install pre-commit hooks
uv run pre-commit install

# Manually run all hooks
uv run pre-commit run --all-files
```

### Testing

Run the test suite with pytest:
```bash
uv run pytest tests/ -v
```

Run tests with coverage:
```bash
uv run pytest tests/ --cov=src/dkbparsing --cov-report=html
```

## Maintenance

### Updating Dependencies

To update all dependencies to their latest compatible versions:
```bash
uv lock --upgrade
uv sync
```

This will update the `uv.lock` file and sync your environment with the new versions.

## Usage

### Configuration

Create a CLI configuration file (JSON) that specifies:
- `category_config`: Path to your categories JSON file
- `manual_assignments_file`: Path to your manual assignments JSON file
- `output_template`: (Optional) Path to household budget template file
- `output_format`: Output format - `"excel"`, `"summary"`, `"household"`, or `"both"`

Example `cli_config.json`:
```json
{
  "category_config": "my_categories.json",
  "manual_assignments_file": "manual_assignments.json",
  "output_template": "household_template.txt",
  "output_format": "household"
}
```

### Category Configuration

Categories are defined in a JSON file with search strings and optional regex patterns:

```json
{
  "lebensmittel": {
    "display_name": "Lebensmittel",
    "search_strings": ["REWE", "EDEKA"],
    "regex_patterns": [],
    "expected_max_amount": 300.0
  }
}
```

### Manual assignemnts
For transactions that you would like to assign only once to a categoryuse manual_assigments.
An example can be found at `examples/manual_assigments.json`:

```json
{
  "manual_assignments": [
    {
      "date": "01.08.22",
      "recipient": "PayPal Europe S.a.r.l. et Cie S.C.A",
      "purpose": "123",
      "category": "Hardware"
    },
    {
      "date": "31.07.22",
      "recipient": "AMAZON PAYMENTS EUROPE S.C.A.",
      "purpose": "303-",
      "category": "Hardware"
    }
  ]
}
```
The defined category must exist in your category file.

### Basic Usage

**Parse a CSV file:**
```bash
python -m dkbparsing.cli /path/to/accounting.csv --config /path/to/cli_config.json
```

**Filter by date range:**
```bash
python -m dkbparsing.cli /path/to/accounting.csv --config /path/to/cli_config.json \
  --start-date 01.07.25 --end-date 31.07.25
```

**Add a new category:**
```bash
python -m dkbparsing.cli /path/to/accounting.csv --config /path/to/cli_config.json \
  --add-category "faz" "FAZ" "Frankfurter Allgemeine"
```

**Add a manual assignment:**
```bash
python -m dkbparsing.cli /path/to/accounting.csv --config /path/to/cli_config.json \
  --add-manual 01.01.99 "Parkhaus GmbH 123" "VISA Debitkartenumsatz" "car-expenses"
```

### Output Formats

**Excel Format** (`output_format: "excel"`):
Generates category totals and uncategorized transactions in a format ready to copy-paste into Excel.

**Summary Format** (`output_format: "summary"`):
Provides a detailed summary including:
- Total transactions processed
- Categorized vs uncategorized counts
- Total income and expenses
- Net balance
- Category totals
- Warnings for categories exceeding expected maximum amounts

**Household Format** (`output_format: "household"`):
Generates output based on a template file. The template should contain category display names (one per line), and the output will match the template order with amounts. Empty lines in the template are preserved.

Example template (`household_template.txt`):
```
Einkommen


Miete
Strom
Kleidung
Essen
```

This generates output like:
```
5312,5
12,30



1500,00
37,90
173,15
```

You can copy this directly into your Excel spreadsheet!

### Examples

See the `examples/` directory for:
- Sample category configuration (`categories.json`)
- Example CLI configuration (`cli_config.json`)
- Household budget template (`household_template.txt`)
- Manual assignments example (`manual_assignments.json`)

## License

See LICENSE file for details.
