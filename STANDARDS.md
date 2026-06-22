# Project Standards

This project follows strict development guidelines to ensure stability, maintainability, and security.

## General Principles

- **Security First:** Always run processes with the least privilege. The miner and dashboard must run as the non-root `miner` user.
- **Test Driven:** New features should include unit tests and, where applicable, E2E tests.
- **Documentation:** Any changes to configuration or features must be reflected in `README.md` and `CHANGELOG.md`.

## Quick Reference

| Category          | Requirement                                                    |
| ----------------- | -------------------------------------------------------------- |
| **Test Coverage** | ≥80% for new code (90% for core modules)                       |
| **Linting**       | Must pass before merge                                         |
| **Type Safety**   | Python type hints required for all new modules                 |
| **Commits**       | [Conventional Commits](https://conventionalcommits.org) format |
| **PRs**           | Require approval + passing CI                                  |
| **Secrets**       | Never committed; use env vars or Docker secrets                |

## Python Standards

- **Version:** Python 3.10+
- **Type Hinting:** Use PEP 484 type hints for all function signatures and complex variables.
- **Testing:**
  - Framework: `pytest`
  - Mocking: Use `pytest-mock` (`mocker` fixture) instead of `unittest.mock`.
  - Organization: Tests reside in the `tests/` directory.
- **Concurrency:** Prefer `asyncio` for I/O bound tasks (e.g., API calls in FastAPI).

## Bash Standards

- Use `#!/bin/bash` and ensure scripts are executable.
- Implement proper error handling (`set -e` where appropriate).
- Use environment variables for configuration, providing sensible defaults.

## Docker Standards

- **User:** All processes must run as user `miner` (UID 1000).
- **Persistence:** All writable data must be stored in the directory specified by `DATA_DIR` (default: `/app/data`).
- **Base Images:** Use stable, official base images (e.g., `python:3.12-slim`, `rocm/dev-ubuntu-22.04`).

## Git & Workflow

- **Branching:** Use descriptive branch names (e.g., `feature/profit-switcher-updates`).
- **Commit Messages:** Follow Conventional Commits:
  - `feat:` for new features
  - `fix:` for bug fixes
  - `docs:` for documentation changes
  - `test:` for adding/updating tests
  - `refactor:` for code changes that neither fix a bug nor add a feature
