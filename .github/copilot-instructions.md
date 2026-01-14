# GitHub Copilot Instructions

This document provides context and guidance for GitHub Copilot to generate more accurate and relevant code suggestions for this project.

## Project Overview

This project is a Dockerized solution for mining the Ergo (ERG) cryptocurrency using lolMiner. It supports both NVIDIA and AMD GPUs and includes features like automatic failover, health monitoring, a Prometheus exporter, and overclocking capabilities.

## Key Technologies

- **Docker:** The entire application is containerized. Pay close attention to `Dockerfile`, `Dockerfile.amd`, and `docker-compose.yml`.
- **Python:** Used for the web dashboard (`dashboard.py`), metrics exporter (`metrics.py`), and various scripts. The main libraries are Flask, Flask-SocketIO, prometheus-client, and requests.
- **Shell Scripting:** The `start.sh` script is the main entrypoint for the container. It's responsible for configuring and launching the miner, as well as starting the monitoring and overclocking processes.

## Important Files

- **`Dockerfile` & `Dockerfile.amd`:** These files define the Docker images for NVIDIA and AMD GPUs, respectively. When making changes, consider the impact on both environments.
- **`docker-compose.yml`:** The main Docker Compose file for single-GPU setups.
- **`docker-compose.multi-gpu.yml`:** The Docker Compose file for multi-GPU setups.
- **`start.sh`:** The container's entrypoint script. This is where the core logic for starting the miner and other services resides.
- **`metrics.py`:** The script that collects and exposes metrics for Prometheus.
- **`dashboard.py`:** The Flask application for the web dashboard.
- **`README.md`:** Provides a comprehensive overview of the project, including setup instructions, configuration options, and troubleshooting tips.

## Coding Conventions

- **Shell Scripts:** Follow the Google Shell Style Guide. Use `set -e` to exit on error.
- **Python:** Follow PEP 8. Use type hints where possible.
- **Dockerfile:** Use multi-stage builds to keep the final image size small. Combine `RUN` commands to reduce the number of layers.

## General Guidance

- When adding new features, ensure they are compatible with both NVIDIA and AMD environments.
- If you add a new dependency, update the `requirements.txt` file.
- If you change a configuration option, update the `.env.example` file and the `README.md`.
- Always consider the security implications of your changes. For example, run the lolMiner API in read-only mode.
