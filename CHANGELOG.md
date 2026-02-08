# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Add NVIDIA container runtime validation tool to `setup.sh` for easier first-time troubleshooting.
- Enhance Prometheus metrics with `miner_info`, `miner_uptime`, and `miner_api_up`.
- Add `worker` label to all Prometheus metrics for better multi-rig support.
- Add 'Eco Mode' underclocking profiles for RTX 30/40 series GPUs.
- Implement 'One-Click Multi-GPU' discovery in `start.sh` for both NVIDIA and AMD.
- Add support for `MULTI_PROCESS` mining mode, running one miner process per GPU for improved isolation and stability.
- Implement 'Telegram Bot' notifications for rig downtime and recovery.
- New interactive Telegram configuration prompts in `setup.sh`.
- Implement 'Auto-Profit Switching' between pools via a background supervisor.
- Implement 'Rootless Docker' support by running the miner process as a non-root user (`miner`).
- Support for `EXTRA_ARGS` environment variable to pass custom flags to both lolMiner and T-Rex.
- Full miner log download feature in the web dashboard.
- Miner selection (lolMiner vs T-Rex) and `EXTRA_ARGS` configuration in the web dashboard.
- GPU count verification in `healthcheck.sh` to ensure all configured GPUs are active.
- New unit tests for log download endpoint and health check GPU count verification.
- Integrated `EXTRA_ARGS` prompt in `setup.sh`.
- New `miner_api.py` module to centralize and de-duplicate miner and GPU data fetching logic.
- Dynamic "Miner Status" indicator in the web dashboard (Mining, Idle, Error).
- Retry logic and improved error handling for miner API calls.
- Integrated miner log viewer in the web dashboard with a new `/api/logs` endpoint.
- Rig-wide metrics (Total Power Draw, Average Temperature) in the web dashboard.
- Automated T-Rex version discovery in `setup.sh`.
- WoolyPooly pool support in `setup.sh`.
- New GPU tuning profiles for RTX 3060 Ti, 3090, 4070, and 4090 in `gpu_profiles.json`.
- `miner_total_shares_accepted` and `miner_total_shares_rejected` Prometheus metrics.
- Multi-miner support (lolMiner and T-Rex) in the web dashboard via a normalization layer.
- Hardware-level GPU metrics (Temperature, Power Draw) in the dashboard using `nvidia-smi` and `rocm-smi`.
- "Restart Miner" button and API endpoint in the web dashboard.
- Automated lolMiner version discovery in `setup.sh`.
- New script `scripts/fetch_latest_release.sh` to fetch latest GitHub releases.
- Multi-GPU Grafana Dashboard with comprehensive overview.
- GPU Current Status table in Grafana dashboard.
- Total Dual Hashrate and Average Fan Speed metrics to Grafana dashboard.
- Detailed per-GPU timeseries for Dual Hashrate, Fan Speed, and Power Draw in Grafana.

### Changed
- Migrated the web dashboard from Flask to FastAPI for improved performance and async support.
- Updated Dockerfiles to include `gosu` and a non-root `miner` user (UID 1000).
- Modified `start.sh` to drop privileges to the `miner` user after performing root-level operations like overclocking.
- Refactored `dashboard.py` and `metrics.py` to use the centralized `miner_api.py`.
- Generalized dashboard title from "lolMiner Dashboard" to "Miner Dashboard".
- Configured miners to log to `miner.log` for persistent access in the dashboard.
- Refactored `dashboard.py` to use `subprocess` for improved security and error handling.
- Enhanced `dashboard.py` with comprehensive logging and error handling for API and SMI calls.
- Updated `templates/index.html` with a new stats grid, log viewer, and "Last Updated" timestamp.
- Refactored `Dockerfile` and `Dockerfile.amd` to use `LOLMINER_VERSION` build argument.
- Updated Docker Compose files to support `LOLMINER_VERSION` build argument.
- Generalized Prometheus metrics prefix from `lolminer_` to `miner_` to support multiple backends.
- Updated Grafana dashboard to use new `miner_` metric names.
- Improved Prometheus exporter to use string labels for GPU indices, fixing potential type errors.
- Enhanced `setup.sh` with better numbering and interactive prompts.

### Removed
- Legacy `hashrate_history.csv` file (replaced by SQLite database).

### Fixed
- Fixed Prometheus label type error in `metrics.py` by ensuring GPU indices are strings.
- Fixed setup script numbering in section "8. Extra Arguments".
