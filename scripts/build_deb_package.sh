#!/bin/bash

# Build script for the dkbparsing .deb package
#
# Wraps the PyInstaller executable created by build_dkbparsing.sh into a
# Debian package. Result: dist/dkbparsing_<version>_amd64.deb

set -euo pipefail

echo "Building dkbparsing .deb package..."

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

if [ ! -f "dist/dkbparsing" ]; then
    echo "Error: dist/dkbparsing not found. Run scripts/build_dkbparsing.sh first."
    exit 1
fi

VERSION=$(grep -E '^version\s*=' pyproject.toml | sed -E 's/version\s*=\s*"([^"]+)"/\1/')

PACKAGE_ROOT="build/deb"
rm -rf "${PACKAGE_ROOT}"

mkdir -p "${PACKAGE_ROOT}/DEBIAN"
mkdir -p "${PACKAGE_ROOT}/usr/bin"

install -m 0755 dist/dkbparsing "${PACKAGE_ROOT}/usr/bin/dkbparsing"

cat > "${PACKAGE_ROOT}/DEBIAN/control" <<EOF
Package: dkbparsing
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Marc Schuh <dkbparsing@marc-schuh.de>
Homepage: https://github.com/MarcSchuh/DKBParsing
Description: Parsing and categorizing of DKB account statement CSV exports
 DKBParsing parses and categorizes DKB (Deutsche Kreditbank) account
 statement CSV exports. It supports categorization via search strings
 and regex patterns, manual assignments, and AI-powered categorization
 suggestions via the OpenRouter API.
Built-Using: PyInstaller
EOF

dpkg-deb --root-owner-group --build "${PACKAGE_ROOT}" "dist/dkbparsing_${VERSION}_amd64.deb"

echo "✅ Package built: dist/dkbparsing_${VERSION}_amd64.deb"
echo "📏 File size: $(du -h "dist/dkbparsing_${VERSION}_amd64.deb" | cut -f1)"
