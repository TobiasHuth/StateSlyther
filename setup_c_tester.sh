#!/bin/bash
# Interactive C State Machine Tester - Linux/Mac installer and launcher
# This script helps with C compiler setup and testing

echo "========================================"
echo "C State Machine Tester Setup"
echo "========================================"

# Check for compiler
echo -e "\nChecking for C compiler..."

if command -v gcc &> /dev/null; then
    COMPILER="gcc"
    echo "✓ Found gcc"
elif command -v clang &> /dev/null; then
    COMPILER="clang"
    echo "✓ Found clang"
else
    echo "✗ No C compiler found"
    echo ""
    echo "Install a C compiler:"
    echo "  Ubuntu/Debian: sudo apt-get install build-essential"
    echo "  Fedora: sudo dnf install gcc"
    echo "  macOS: brew install gcc"
    exit 1
fi

echo ""
echo "C Compiler: $COMPILER"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3 not found. Install Python 3 to use StateSlyther."
    exit 1
fi

echo "✓ Python 3 found"

# Check for Tkinter
python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "✗ Tkinter not found"
    echo "Install Tkinter:"
    echo "  Ubuntu/Debian: sudo apt-get install python3-tk"
    echo "  Fedora: sudo dnf install python3-tkinter"
    exit 1
fi

echo "✓ Tkinter found"

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "To test C code:"
echo "1. Generate C code in StateSlyther"
echo "2. Click 'Test C Code (Compile)' button"
echo "3. Use interactive tester to step through states"
echo ""
echo "To compile manually:"
echo "  gcc your_generated_file.c -o state_machine -Wall -Wextra"
echo "  ./state_machine"
echo ""
