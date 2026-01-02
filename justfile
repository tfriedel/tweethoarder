# justfile for Python Project Template
# Usage: just <recipe>
# Use 'just --list' to see all available recipes

# Default recipe - show help
default: help

# Show this help message
help:
    @echo "Available recipes:"
    @just --list

## Setup and Installation

# Initialize a newly checked out repository
setup:
    @echo "🚀 Setting up development environment..."
    @just init-git
    @just install-tdd-guard
    @just install-dev
    @just install-hooks
    @echo "✅ Setup complete! You're ready to develop."

# Initialize git repository if needed
init-git:
    @if [ ! -d .git ]; then \
        echo "📁 Initializing Git repository..."; \
        git init; \
        echo "✅ Git repository initialized"; \
    else \
        echo "✅ Git repository already initialized"; \
    fi

# Install TDD-Guard for test-driven development enforcement
install-tdd-guard:
    @echo "🛡️ Installing/updating TDD-Guard..."
    @if command -v npm >/dev/null 2>&1; then \
        npm install -g tdd-guard@latest; \
        echo "✅ TDD-Guard installed/updated"; \
    else \
        echo "⚠️  npm not found - skipping TDD-Guard installation"; \
        echo "   Install Node.js to enable TDD-Guard: https://nodejs.org/"; \
    fi

# Install development dependencies
install-dev:
    @echo "📦 Installing development dependencies..."
    uv sync --dev

# Install pre-commit hooks
install-hooks:
    @echo "🪝 Installing pre-commit hooks..."
    uv run prek install
    @echo "✅ Pre-commit hooks installed"

## Code Quality

# Format code with ruff
format:
    @echo "🎨 Formatting code..."
    uv run --frozen ruff format .
    @echo "✅ Code formatted"

# Lint code with ruff
lint:
    @echo "🔍 Linting code..."
    uv run --frozen ruff check .

# Lint code and auto-fix issues
lint-fix:
    @echo "🔧 Linting code with auto-fix..."
    uv run --frozen ruff check . --fix

# Run type checking with Zuban
typecheck:
    @echo "🔍 Running type checker..."
    uv run --frozen zmypy

# Check for dependency issues with deptry
deptry:
    @echo "🔍 Checking for dependency issues..."
    uv run --frozen deptry src

## Testing

# Run tests
test:
    @echo "🧪 Running tests..."
    uv run --frozen pytest

# Run tests with verbose output
test-verbose:
    @echo "🧪 Running tests (verbose)..."
    uv run --frozen pytest -v

# Run tests with coverage report
test-coverage:
    @echo "🧪 Running tests with coverage..."
    uv run --frozen pytest --cov=src --cov-report=term-missing

## Build and Clean

# Build the package
build:
    @echo "🔨 Building package..."
    uv build

# Clean up temporary files and caches
clean:
    @echo "🧹 Cleaning up..."
    find . -type f -name "*.pyc" -delete
    find . -type d -name "__pycache__" -delete
    find . -type d -name "*.egg-info" -exec rm -rf {} +
    find . -type d -name ".pytest_cache" -exec rm -rf {} +
    find . -type d -name ".ruff_cache" -exec rm -rf {} +
    rm -rf dist/
    rm -rf build/
    @echo "✅ Cleanup complete"

## CI/Development Workflow

# Run all code quality checks (lint + typecheck + test)
check:
    @echo "🔍 Running all checks..."
    @just lint
    @just typecheck
    @just deptry
    @just test
    @echo "✅ All checks passed"

# Run full CI pipeline (format, lint, typecheck, test)
ci:
    @echo "🤖 Running CI pipeline..."
    @just format
    @just lint
    @just typecheck
    @just deptry
    @just test
    @echo "✅ CI pipeline complete"

# Run pre-commit hooks on all files
pre-commit:
    @echo "🪝 Running pre-commit hooks..."
    uv run prek run --all-files

## Development Utilities

# Generate/update CHANGELOG.md from git history
changelog:
    @echo "📝 Generating changelog..."
    uv run git-cliff -o CHANGELOG.md
    @echo "✅ CHANGELOG.md updated"

# Update all dependencies to latest versions
update-deps:
    @echo "📦 Updating dependencies..."
    uv lock --upgrade

# Generate/update lockfile
lock:
    @echo "🔒 Updating lockfile..."
    uv lock

# Sync environment with lockfile
sync:
    @echo "🔄 Syncing environment..."
    uv sync

## Project Info

# Show project information
info:
    @echo "📊 Project Information:"
    @echo "  Name: twitterdump"
    @echo "  Python: $(uv run python --version)"
    @echo "  UV: $(uv --version)"
    @echo "  Git branch: $(git branch --show-current)"
    @echo "  Git status: $(git status --porcelain | wc -l) changed files"
    @echo "  Pre-commit: $(if [ -f .git/hooks/pre-commit ]; then echo 'installed'; else echo 'not installed'; fi)"

# Show dependency tree
deps:
    @echo "📋 Dependency tree:"
    uv tree
