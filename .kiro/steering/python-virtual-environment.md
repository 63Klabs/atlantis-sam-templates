---
inclusion: auto
description: Rules for using the Python virtual environment (.venv) in this repository
---

# Python Virtual Environment

## Overview

This repository uses a single Python virtual environment (`.venv`) at the project root for all Python tooling, including linting, testing, and any other Python-based utilities.

## Rules

1. **Always activate `.venv` before running Python commands.** Use `source .venv/bin/activate` before executing any Python tool (`cfn-lint`, `pytest`, `python`, `pip`, etc.).

2. **Never install packages globally or create additional virtual environments.** All Python dependencies live in `.venv`. Do not create tool-specific venvs (e.g., `cfn-lint-env`).

3. **Use `.venv/bin/activate` for shell commands.** When running commands via bash, prefix with `source .venv/bin/activate &&`.

4. **Do not use bare `python` or `python3` commands** without first activating the virtual environment. The system Python may not have the required packages.

## Key Packages

The `.venv` environment includes:

- `cfn-lint` — CloudFormation template linting and validation
- `pytest` — Test runner
- `hypothesis` — Property-based testing
- `pyyaml` — YAML parsing for template tests
- `jinja2` — Template rendering utilities

## Examples

```bash
# Run cfn-lint
source .venv/bin/activate && cfn-lint templates/v2/storage/template-storage-s3-access-logs.yml

# Run tests
source .venv/bin/activate && pytest tests/

# Install a new package
source .venv/bin/activate && pip install <package-name>
```
