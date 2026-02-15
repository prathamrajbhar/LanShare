#!/bin/bash
# Move to project root
cd "$(dirname "$0")/.."

echo "=================================================="
echo "LanShare Build Script for Linux"
echo "=================================================="

# Check for python3
if ! command -v python3 &> /dev/null
then
    echo "Error: python3 could not be found."
    exit 1
fi

echo "Starting build process..."
python3 scripts/build.py

if [ $? -eq 0 ]; then
    echo ""
    echo "Build successful! Standard executable in 'dist/'."
    echo ""
    echo "Creating Debian package (.deb)..."
    python3 scripts/package_linux.py
    echo ""
    echo "Done! Check the 'dist' folder for both the binary and the .deb package."

else
    echo ""
    echo "BUILD FAILED!"
    exit 1
fi
