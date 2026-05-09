#!/bin/bash

# Clean up existing build artifacts
rm -rf build dist __pycache__

# Build the binary
pyinstaller QuantCopierTelegram.spec

# Set source and target paths
src_file="dist/QuantCopierTelegram.exe"
target_dir="../QuantCopierTelegramUI/src-tauri/binaries"

# Get rust target triple
if command -v rustc >/dev/null 2>&1; then
    target_triple=$(rustc -vV | grep 'host:' | cut -d' ' -f2)
else
    echo "rustc not found. Please install Rust or set target triple manually."
    exit 1
fi
if [ -z "$target_triple" ]; then
    echo "Failed to determine platform target triple"
    exit 1
fi

target_file="$target_dir/QuantCopierTelegram-${target_triple}.exe"

# Check if source file exists
if [ ! -f "$src_file" ]; then
    echo "Source file $src_file does not exist. Build it first."
    exit 1
fi

# Create target directory if it doesn't exist
mkdir -p "$target_dir"

# Copy the file to the target directory
cp "$src_file" "$target_file"

if [ $? -eq 0 ]; then
    echo "Copied $src_file to $target_file successfully."
else
    echo "Failed to copy $src_file to $target_file."
    exit 1
fi