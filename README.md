# DKB Parsing

A clean, configurable parser for DKB account statements that allows you to categorize transactions and generate Excel-compatible output.

## Installation

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver:

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies and install the package (includes dev dependencies)
uv sync

# Or sync only production dependencies
uv sync --no-dev
```

This will create a virtual environment and install all dependencies from `pyproject.toml`.

### Code Quality Tools
**Pre-commit Hooks (Recommended):**

To automatically run ruff and other checks before each commit:

```bash
# Install pre-commit hooks
pre-commit install

# Manually run all hooks
pre-commit run --all-files
```

## Quick Start

### 1. Typical usage

```bash
# Basic parsing

python -m dkbparsing.cli /path/to/accounting.csv --config /path/to/config.json  --add-category "faz" "FAZ" "Frankfurter Allgemeine"

python -m dkbparsing.cli /path/to/accounting.csv --config /path/to/config.json  --add-manual 01.01.99 "Parkhaus GmbH 123" "VISA Debitkartenumsatz" "car-expenses"

python -m dkbparsing.cli /path/to/accounting.csv --config /path/to/config.json --start-date 01.07.25 --end-date 31.07.25
```

## Household Budget Integration

The parser supports direct integration with household budget spreadsheets:

### 1. Create a Template File

Create a text file with your budget categories in the desired order:

```
Einkommen
Finanzamt




Miete
Strom
Kleidung
Essen
```

**Notes:**
- Empty lines in the template are preserved in the output
- Category names should match the `display_name` from your category configuration
- For income, use any line containing "einkommen" (case-insensitive) - it will automatically map to total income
- Matching is case-insensitive, so "lebensmittel" matches "Lebensmittel"

### 2. Generate Household Output

```bash
python -m dkbparsing.cli export.csv --output household --template my_template.txt
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

## Examples

See the `examples/` directory for:
- Sample configuration file
- Example usage code
- Configuration templates
- Household budget integration examples

## Contributing

This library is designed to be easily extensible. You can:
- Add new output formats by extending the formatter classes
- Add new categorization methods by extending the category manager
- Add new CSV formats by extending the CSV parser

## License

See LICENSE file for details.

# ToDo
- Wenn manuelle Zuordnung eine Kategorie enthält, die in den Hauptkategorien nicht dabei ist, soll ein Fehler geworfen werden.
- Wenn das Output Template nicht alles abdeckt, was an Kategorien befüllt wird, soll ein Fehler geworfen werden.
- Das versehentliche Überschreiben von Kategorien soll schwerer werden
- Tests
- Maximalbetrag pro Kategorie
