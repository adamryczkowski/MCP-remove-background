# MCP-remove-background

MCP server that removes background from images

## Features

- Spack-based system dependency management (Python runtime)
- Poetry-based Python dependency management and packaging
- Pre-commit hooks (formatting, linting, security, type-checking, tests)
- Justfile with common developer tasks
- Pytest with coverage
- Docs scaffold in `docs/`

## Requirements

- Git (for Spack installation if not present)
- just (command runner)

The following are managed automatically by Spack (installed on first `just setup`):
- Python 3.13.11+

The following are installed via pipx/pip:
- Poetry 2.x
- pre-commit

## Quickstart

Initialize the development environment:

```bash
just setup
```

Run tests with coverage:

```bash
just test
```

Run all pre-commit hooks on all files:

```bash
just validate
```

Build a wheel in `dist/`:

```bash
just package
```

Clean build and temp artifacts:

```bash
just clean
```

## Spack Integration

This project uses [Spack](https://spack.io/) to manage system-level dependencies (like the Python interpreter). Spack is automatically installed to `~/.local/share/spack` if not already available.

To manually activate the Spack environment:

```bash
source .spack-activate.sh
```

To update Spack packages:

```bash
spack -e . concretize --fresh-roots --force
spack -e . install
```

## Project layout

```
MCP-remove-background/
├─ MCP_remove_background/
│  ├─ __init__.py
│  └─ core.py
├─ tests/
│  ├─ pytest.ini
│  └─ test-mock.py
├─ docs/
│  └─ README.md
├─ scripts/
│  └─ spack-ensure.sh
├─ .pre-commit-config.yaml
├─ .gitignore
├─ justfile
├─ pyproject.toml
├─ spack.yaml
└─ README.md
