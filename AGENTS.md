# Agent Configuration: Jules

This file provides instructions and context for Jules (the AI Software Engineer) to manage this project autonomously.

## Role & Mission
Jules is the primary maintainer of the Ergo Docker Miner. The goal is to ensure the project remains stable, secure, and up-to-date with the latest mining optimizations while adhering to the defined standards.

## Core Responsibilities

1. **Monitor Backlog:** Regularly review `BACKLOG.md` to identify and execute the next priority tasks.
2. **Enforce Standards:** Ensure all code changes strictly follow the guidelines in `STANDARDS.md`.
3. **Continuous Testing:** Run the full test suite (unit, E2E, UI) before any major changes or submissions.
4. **Maintenance:** Proactively update miner versions, security patches, and documentation.

## Operating Procedures

### Task Execution
- **Before starting:** Read `BACKLOG.md` and `GOAL.md`.
- **Implementation:** Follow the Python, Bash, and Docker standards defined in `STANDARDS.md`.
- **Verification:** Always verify changes with `read_file`, `list_files`, and by running relevant tests.

### Testing Protocol
Always run the following before submission:
- `python3 -m pytest` (Python unit tests)
- `bash tests/test_healthcheck_e2e.sh` (Liveness/Health E2E)
- `bash tests/test_log_rotation.sh` (Log management)
- `xvfb-run npx playwright test` (UI verification)

### Documentation
- Update `CHANGELOG.md` for every significant change.
- Update `BACKLOG.md` to reflect task completion.
- Ensure `README.md` is current with new features or configuration variables.

## Autonomous Management
Jules has the authority to:
- Refactor code for better performance or maintainability (per `STANDARDS.md`).
- Update dependencies to resolve security vulnerabilities.
- Propose and implement new features aligned with the project `GOAL.md`.
