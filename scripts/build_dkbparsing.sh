#!/bin/bash

# Build script for dkbparsing executable using PyInstaller

set -e

echo "Building dkbparsing executable..."

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/dkbparsing __pycache__/ *.spec

# Build the executable
echo "Building executable with PyInstaller..."
uv run pyinstaller --onefile \
    --name dkbparsing \
    --hidden-import dkbparsing \
    --hidden-import dkbparsing.cli \
    --hidden-import dkbparsing.parser \
    --hidden-import dkbparsing.csv_parser \
    --hidden-import dkbparsing.category_manager \
    --hidden-import dkbparsing.output_formatter \
    --hidden-import dkbparsing.models \
    --hidden-import dkbparsing.openrouter_client \
    --hidden-import pandas \
    --hidden-import openai \
    --strip \
    --upx-dir=/usr/bin \
    src/dkbparsing/cli.py

# Check if build was successful
if [ -f "dist/dkbparsing" ]; then
    echo "✅ Build successful!"
    echo "📦 Executable created: dist/dkbparsing"
    echo "📏 File size: $(du -h dist/dkbparsing | cut -f1)"

    # Make executable
    chmod +x dist/dkbparsing

    echo ""
    echo "🚀 You can now run: ./dist/dkbparsing --help"
    echo "📋 Example usage: ./dist/dkbparsing /path/to/accounting.csv --config /path/to/cli_config.json"
    rm -rf build/ *.spec
else
    echo "❌ Build failed!"
    exit 1
fi
