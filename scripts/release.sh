#!/bin/bash

# Configuration
VERSION="v1.0.0"
TITLE="v1.0.0 - Initial Release"
NOTES="Initial release of LanShare for Windows and Linux."
EXE_PATH="dist/LanShare.exe"
DEB_PATH="dist/lanshare_1.0.0.deb"

echo "🚀 Creating GitHub Release $VERSION..."

# Check if gh CLI is installed
if ! command -v gh &> /dev/null
then
    echo "❌ Error: 'gh' CLI is not installed. Please install it first."
    exit 1
fi

# Check if assets exist
if [ ! -f "$EXE_PATH" ] || [ ! -f "$DEB_PATH" ]; then
    echo "❌ Error: Release assets not found in dist/. Please run build scripts first."
    exit 1
fi

# Create the release and upload assets
gh release create "$VERSION" \
    "$EXE_PATH" \
    "$DEB_PATH" \
    --title "$TITLE" \
    --notes "$NOTES"

if [ $? -eq 0 ]; then
    echo "✅ Release $VERSION created successfully!"
else
    echo "❌ Failed to create release."
    exit 1
fi
