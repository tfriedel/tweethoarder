# tweethoarder

Dump your twitter data (liks, bookmarks, ...) to files

## Features

- 🚀 **Modern Python**: Support for Python 3.13+
- 📦 **uv Package Manager**: Fast and reliable package management with [uv](https://github.com/astral-sh/uv)
- 🐳 **Docker Support**: Complete Docker development environment
- 📦 **Devcontainer Support**: VS Code devcontainer for consistent development
- ✨ **AI Editor Support**: [Cursor rules](https://docs.cursor.com/context/rules) and [CLAUDE.md](https://docs.anthropic.com/en/docs/claude-code/overview) included for AI-powered development
- 🛡️ **TDD-Guard**: Automated TDD enforcement for Claude Code with real-time test-driven development validation
- 📝 **Type Checking**: Zuban type checker with mypy-compatible mode
- 🔍 **Code Quality**: Pre-configured Ruff for linting and formatting
- 🧪 **Testing**: pytest setup with coverage reporting and enhanced output (pytest-cov, pytest-sugar)
- 📊 **Modern Logging**: Loguru for intuitive, zero-config logging
- 🔧 **Pre-commit Hooks**: Automated code quality checks with prek (10x faster than traditional pre-commit)
- 🔄 **Version Sync**: sync-with-uv eliminates version drift between uv.lock and pre-commit config
- 🏷️ **Dynamic Versioning**: Automatic versioning from git tags (no manual version bumping!)
- 📝 **Changelog Generation**: Automated CHANGELOG.md from conventional commits
- 🏗️ **CI Ready**: GitHub Actions workflows included
- ⚡ **justfile**: Modern command runner for common development tasks

## Quick Start

### Pre-Requirements

- [uv](https://docs.astral.sh/uv/): Fast Python package installer
- [just](https://just.systems/): Command runner (optional but recommended)
- [Node.js](https://nodejs.org/) (optional, for TDD-Guard): Required for TDD enforcement with Claude Code

### Development Setup

```bash
# Quick setup (initializes git, installs TDD-Guard, dependencies, and pre-commit hooks)
just setup

# Or manually:
# Initialize git repository (required for dynamic versioning)
git init

# Install TDD-Guard (optional, requires Node.js/npm)
npm install -g tdd-guard@latest

# Install dependencies
uv sync --dev

# Install pre-commit hooks
uv run prek install
```

### Common Commands

```bash
# View all available commands
just --list

# Testing
just test              # Run tests
just test-verbose      # Run tests with verbose output
just test-coverage     # Run tests with coverage report

# Code quality
just format            # Format code with ruff
just lint              # Check code quality
just lint-fix          # Auto-fix linting issues

# Development workflow
just ci                # Run full CI pipeline (format, lint, test)
just changelog         # Generate/update CHANGELOG.md
just clean             # Clean up temporary files and caches
```

### Manual Commands (without justfile)

```bash
# Run tests
uv run pytest

# Run formatting and linting (automatically runs on commit)
uv run ruff format .
uv run ruff check .
# Auto Fix
uv run ruff check . --fix
```

### Docker Development Setup

The template includes a complete Docker setup:

```bash
# create uv.lock file
uv sync

# use the provided scripts
./docker/build.sh
./docker/run.sh # or./docker/run.sh (Command)

# Build and run with Docker Compose
docker compose build
docker compose up
```

### VS Code Devcontainer

Open the project in VS Code and use the "Reopen in Container" command for a fully configured development environment.

### Update Template

This project was created from [tfriedel/python-copier-template](https://github.com/tfriedel/python-copier-template), a fork of [mjun0812/python-copier-template](https://github.com/mjun0812/python-copier-template) with TDD-Guard integration.

You can apply updates from the template using:

```bash
cd tweethoarder
uvx copier update -A
```

## Project Structure

```text
tweethoarder/
├── src/
│   └── tweethoarder/          # Main package
├── tests/                          # Test files
├── docker/                         # Docker configuration
├── compose.yml                     # Docker Compose setup
├── pyproject.toml                  # Project configuration
└── README.md                       # Project documentation
```

## Q&A

### What type checker does this use?

This template includes [Zuban](https://github.com/lorencarvalho/zuban), a modern type checker with mypy-compatible mode. If you prefer a different type checker like mypy or pyright, you can easily swap it out.

### How does versioning work?

This template uses **dynamic versioning** from git tags - no manual version bumping required!

- Version is automatically derived from git tags using `uv-dynamic-versioning`
- Create a git tag (e.g., `v1.0.0`) to set your version
- The version in your built package will match the tag
- No need to manually update `pyproject.toml` for version changes

**Example workflow:**
```bash
# Make your changes and commit them
git commit -m "feat: add new feature"

# Create a version tag
git tag v1.0.0

# Build your package (version will be 1.0.0)
uv build
```

### How do I generate a changelog?

The template includes automated changelog generation from git commits using conventional commits:

```bash
# Generate/update CHANGELOG.md
just changelog
```

**Conventional commit format:**
```
type(scope): description

Examples:
- feat: add user authentication
- fix: resolve login bug
- docs: update installation guide
- chore: update dependencies
```

Supported types: `feat`, `fix`, `docs`, `perf`, `refactor`, `style`, `test`, `chore`

### What logging library should I use?

The template includes [Loguru](https://github.com/Delgan/loguru) for modern, zero-config logging:

```python
from loguru import logger

logger.info("Application started")
logger.debug("Debug info: {}", some_var)
logger.error("Something went wrong!")

# Easy file logging with rotation
logger.add("logs/app_{time}.log", rotation="500 MB", retention="10 days")
```

## Support

- 📖 [Copier Documentation](https://copier.readthedocs.io/)
- 🐍 [uv Documentation](https://docs.astral.sh/uv/)
- ⚡ [just Documentation](https://just.systems/)
- 🔍 [Ruff Documentation](https://docs.astral.sh/ruff/)
