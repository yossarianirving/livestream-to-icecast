# Agent Guidelines for `livestream-to-ice-cast`

## Table of Contents
- [Build, Lint & Test Commands](#build-lint--test-commands)
- [Code Style Guide](#code-style-guide)
  - [Import Ordering](#import-ordering)
  - [Formatting Rules](#formatting-rules)
  - [Typing Conventions](#typing-conventions)
  - [Naming Conventions](#naming-conventions)
  - [Error Handling & Logging](#error-handling--logging)
  - [Docstrings](#docstrings)
- [Testing Practices](#testing-practices)
- [CI Hooks (Suggested)](#ci-hooks-suggested)
- [Cursor / Copilot Rules](#cursor--copilot-rules)

---

## Build, Lint & Test Commands
### Prerequisites
- Python >= **3.10**.
- Recommended: create a virtual environment:
  ```bash
  python -m venv .venv && source .venv/bin/activate
  ```
- Install the project in editable mode with dev extras (ruff, black, pytest, mypy):
  ```bash
  pip install -e .[dev]
  # or using UV (if installed)
  uv sync --all-extras
  ```
### Build / Installation
- The package is pure‑Python; no compilation step required.
- Entry point defined in `pyproject.toml` as `livestream-to-ice-cast`.
### Linting & Formatting
```bash
ruff check .          # static analysis
ruff --fix .         # auto‑fix simple issues
black .              # code formatter (line length 88)
```
### Type Checking (optional)
```bash
mypy livestream_to_ice_cast
```
### Testing
- Install pytest if not already present:
  ```bash
  pip install pytest
  ```
- Run the full suite:
  ```bash
  pytest -vv
  ```
- Run a single test (or subset) using `-k` or file path:
  ```bash
  # by keyword
  pytest -k live -vv
  # specific test function
  pytest tests/test_config.py::test_load_config_success -vv
  ```
- Stop after first failure for fast feedback:
  ```bash
  pytest --maxfail=1 -q
  ```
---

## Code Style Guide
The repository follows **Ruff** + **Black** conventions.

### Import Ordering (`isort` compatible)
```
# Standard library (alphabetical)
import argparse
import logging
from pathlib import Path

# Third‑party
import tomllib  # or tomli on <3.11

# Project modules (absolute imports)
from livestream_to_ice_cast.config import AppConfig, load_config
from livestream_to_ice_cast.yt_dlp_helper import get_m3u8_url, is_live
```
- Blank line separates each group.
- No wildcard imports.

### Formatting Rules
- Run `black .` before committing (line length 88).
- Use double quotes for strings unless the string contains a double quote.
- Trailing commas in multi‑line collections and function signatures.
- One blank line between top‑level definitions; end files with a newline.

### Typing Conventions
- All public functions have full type hints.
- Prefer concrete types (`str`, `int`, `Path`, `Optional[T]`).
- Use `@dataclass` for structured config objects.
```python
from typing import Optional

def get_m3u8_url(channel_url: str) -> Optional[str]:
    ...
```
- Avoid `Any` unless unavoidable.

### Naming Conventions
| Entity | Style |
|--------|-------|
| Modules & files | `snake_case.py` |
| Packages | `snake_case` |
| Classes / dataclasses | `PascalCase` |
| Functions / methods | `snake_case` |
| Constants | `UPPER_SNAKE_CASE` |
| Variables | `snake_case` (short, descriptive) |
- Private helpers prefixed with a single underscore (`_run_yt_dlp`).

### Error Handling & Logging
- Use the standard `logging` module; never `print` in production code.
```python
import logging
log = logging.getLogger("livestream-to-ice-cast")
```
- Raise specific exceptions (`ValueError`, `FileNotFoundError`, `RuntimeError`).
- Avoid bare `except:`; use `except Exception as exc:` and log or re‑raise.
- Log messages at appropriate levels (debug, info, warning, error) and keep them structured.
- CLI entry point should catch top‑level errors, log, then exit non‑zero:
```python
try:
    cfg = load_config(args.config)
except Exception as exc:  # pragma: no cover
    log.error("Failed to load configuration: %s", exc)
    sys.exit(1)
```

### Docstrings
- Use **Google style** for public APIs.
```python
def load_config(path: Path) -> AppConfig:
    """Load and validate a TOML config file.

    Args:
        path: Path to the ``.toml`` file.
    Returns:
        An :class:`AppConfig` instance.
    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: For missing or invalid keys.
    """
    ...
```
- Keep docstrings concise; module‑level docstring should summarize purpose.

---

## Testing Practices
- Place tests under a top‑level `tests/` directory mirroring the package layout.
- Use **pytest** fixtures for temporary files and mock external calls (`subprocess.run`).
- Example pattern for config validation:
```python
def test_load_config_success(tmp_path: Path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("""
    platform = "twitch"
    channel_url = "https://example.com/channel"
    poll_interval = 10
    [icecast]
    host = "localhost"
    port = 8000
    mount = "/live.mp3"
    source_user = "src"
    source_password = "pwd"
    """)
    from livestream_to_ice_cast.config import load_config
    cfg = load_config(cfg_file)
    assert cfg.icecast.port == 8000
```
- Use `pytest.raises` to verify error paths.
- Keep tests deterministic; avoid real network calls.

---

## CI Hooks (Suggested)
A minimal CI workflow (GitHub Actions) could be:
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install UV & deps
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          uv sync --all-extras
      - name: Lint & format check
        run: |
          ruff check .
          black --check .
      - name: Type check
        run: mypy livestream_to_ice_cast
      - name: Test
        run: pytest -q
```
- Enforce a pre‑commit hook running Black and Ruff on staged files.

---

## Cursor / Copilot Rules
- No `.cursor` or `.cursorrules` directory was found.
- No `.github/copilot-instructions.md` file exists.
- Therefore, there are **no custom cursor or Copilot policies**; agents should follow the generic style guidelines above.

---

*This document serves as a single source of truth for building, linting, testing, and coding standards in the `livestream-to-ice-cast` project.*