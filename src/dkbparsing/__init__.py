"""
DKB Parsing - A clean, configurable parser for DKB account statements.

This package provides tools to parse DKB CSV exports, categorize transactions,
and generate Excel-compatible output.
"""

from .category_manager import CategoryManager
from .csv_parser import DKBCSVParser
from .models import Category, ParsedTransaction, ParsingResult, Transaction
from .output_formatter import ExcelFormatter, SummaryFormatter
from .parser import DKBParser

__version__ = "0.1.0"
__all__ = [
    "Category",
    "CategoryManager",
    "DKBCSVParser",
    "DKBParser",
    "ExcelFormatter",
    "ParsedTransaction",
    "ParsingResult",
    "SummaryFormatter",
    "Transaction",
]
