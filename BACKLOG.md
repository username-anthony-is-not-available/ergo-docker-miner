# Project Backlog

This backlog tracks the strategic priorities and upcoming tasks for the Ergo Docker Miner.

## Strategic Milestones (2025)

- [ ] **M1: Core Maintenance**
  - [ ] Keep lolMiner version updated with latest optimizations.
  - [ ] Regular security scans and dependency updates.
- [ ] **M2: Observability & Reporting**
  - [ ] Enhance metrics for more granular per-GPU tracking.
  - [ ] Implement automated weekly performance reports (email/telegram).
- [ ] **M3: Advanced Configuration**
  - [ ] Expand `gpu_profiles.json` with more community-tested presets.
  - [ ] Improve AMD GPU tuning support.
- [ ] **M4: Automation**
  - [ ] Refine auto-profit switching logic and pool support.
  - [ ] Implement self-healing for common miner/driver errors.

## Upcoming Tasks

### High Priority
- [ ] Implement automated release workflow for lolMiner updates.
- [ ] Add more multi-GPU configuration examples to documentation.
- [ ] Enhance `streamlit_app.py` with more interactive historical charts.

### Medium Priority
- [ ] Integration with more Ergo-specific tools (e.g., Ergo Node).
- [ ] Add support for additional secondary coins in dual mining.
- [ ] Refactor `miner_api.py` for better hardware abstraction.

### Low Priority
- [ ] UI/UX improvements for the web dashboard.
- [ ] Expand unit test coverage for `metrics.py`.
- [ ] Explore rootless Docker optimizations for overclocking.

## Completed (Recent)
- [x] Multi-process mining mode implementation.
- [x] Telegram notifications for rig downtime.
- [x] Auto-profit switching initial release.
- [x] Enhanced web dashboard with FastAPI backend.
