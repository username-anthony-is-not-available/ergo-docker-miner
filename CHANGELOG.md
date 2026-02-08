# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Implement individual background service management with new `/api/services/restart/{service_name}` endpoint and dashboard buttons.
- Export `GPU_DEVICES` in `start.sh` for reliable environment propagation to background processes.
- Implement GPU name caching in `miner_api.py` to reduce SMI overhead and improve dashboard responsiveness.
- Enhance `profit_switcher.py` with profitability score caching and a configurable `MIN_SWITCH_COOLDOWN` (default 900s).
- Improve `miner_api.py` robustness in `MULTI_PROCESS` mode with automatic device discovery fallback.
- Implement rig-wide and per-GPU power efficiency metrics (MH/s per Watt) in the dashboard and Prometheus exporter.
- Add "Service Status" watchdog to monitor the health of background processes (Metrics, Profit Switcher, CUDA Monitor).
- Implement a 15-minute safety cooldown in `profit_switcher.py` to prevent rapid pool switching and ensure stability.
- Improve multi-process cleanup in `start.sh` with more robust termination logic using `jobs -p` and `pkill` fallback.
- Implement detailed per-GPU historical tracking in a new `gpu_history` database table.
- Add real-time, non-refresh chart updates to the web dashboard using Socket.IO.
- Add total power draw history chart and rig-wide power tracking in the dashboard.
- New `/gpu-history/{gpu_index}` API endpoint for granular performance analysis.
- Implement rejected share ratio monitoring in `healthcheck.sh` with automated restart threshold (10%).
- Improve `profit_switcher.py` with actual luck/effort parsing for 2Miners, Nanopool, and WoolyPooly.
- Enhance profit switcher with configurable `PROFIT_SWITCHING_THRESHOLD` and `PROFIT_SWITCHING_INTERVAL`.
- Add Nanopool and WoolyPooly support to the profit switcher for feature parity with `setup.sh`.
- Collect and expose GPU fan speed from hardware SMI in the dashboard and metrics.
- New profit switching configuration fields in the web dashboard.
- Integrated profit switching threshold and interval prompts in `setup.sh`.
- Implement automated CUDA error detection and auto-restart functionality via `cuda_monitor.sh`.
- New 'Auto-Restart on CUDA Error' configuration option in `setup.sh` and the web dashboard.
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
- Comprehensive GPU tuning profiles for NVIDIA 30/40 series (3050, 3060/Ti, 3070/Ti, 3080/Ti, 3090/Ti, 4060/Ti, 4070/Super/Ti/Ti Super, 4080/Super, 4090) in `gpu_profiles.json`.
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
