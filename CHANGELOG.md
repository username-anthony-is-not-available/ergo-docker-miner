# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Automated lolMiner version discovery in `setup.sh`.
- New script `scripts/fetch_latest_release.sh` to fetch latest GitHub releases.
- Multi-GPU Grafana Dashboard with comprehensive overview.
- GPU Current Status table in Grafana dashboard.
- Total Dual Hashrate and Average Fan Speed metrics to Grafana dashboard.
- Detailed per-GPU timeseries for Dual Hashrate, Fan Speed, and Power Draw in Grafana.

### Changed
- Refactored `Dockerfile` and `Dockerfile.amd` to use `LOLMINER_VERSION` build argument.
- Updated Docker Compose files to support `LOLMINER_VERSION` build argument.
- Generalized Prometheus metrics prefix from `lolminer_` to `miner_` to support multiple backends.
- Updated Grafana dashboard to use new `miner_` metric names.
- Improved Prometheus exporter to use string labels for GPU indices, fixing potential type errors.

### Fixed
- Fixed Prometheus label type error in `metrics.py` by ensuring GPU indices are strings.
