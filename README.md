# Ergo Docker Miner

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This project provides a Dockerized solution for mining Ergo (ERG) using lolMiner. It simplifies the setup process and ensures a consistent mining environment.

## Quick Start

The easiest way to get started is to use our interactive setup script:

```bash
chmod +x setup.sh
./setup.sh
```

This script will guide you through configuring your wallet, pool, and GPU settings, and can even start the miner for you!

## Features

- **Automated Failover:** Automatically switches to a backup pool if the primary one is unavailable.
- **Health Monitoring:** Includes a robust health check script that monitors both process status and hashrate.
- **Prometheus Exporter:** Exposes a Prometheus endpoint for easy integration with monitoring tools.
- **Grafana Dashboard:** Includes a pre-configured Grafana dashboard to visualize your mining performance.
- **Auto-Restart:** Automatically restarts the container if the miner crashes or stops submitting shares for more than 5 minutes.
- **Automatic Overclocking:** Apply overclocking settings to your GPUs to improve performance and efficiency.
- **Auto-Profit Switching:** Automatically switches to the most profitable pool based on real-time stats to maximize your earnings.
- **Telegram Notifications:** Receive instant alerts on your phone when your rig goes down or experiences zero hashrate.
- **Hashrate Logging & Reports:** Automatically logs hashrate to CSV and generates weekly summary reports for performance tracking.
- **Enhanced Security:** The miner runs as a non-root user (`miner`) inside the container by default. It also supports Rootless Docker environments.

## Requirements

- [Docker](https.docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### For NVIDIA Users

- [NVIDIA Drivers](https://www.nvidia.com/Download/index.aspx)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- CUDA-enabled NVIDIA GPU

### For AMD Users

- [ROCm Drivers](https://rocm.docs.amd.com/en/latest/deploy/linux/index.html) (ROCm 5.x or 6.x recommended)
- AMD GPU (Polaris, Vega, Navi, or later)
- Access to `/dev/kfd` and `/dev/dri` on the host

## Setup

### Interactive Setup (Recommended)

Run the interactive setup script:

```bash
chmod +x setup.sh
./setup.sh
```

### Manual Setup

1.  **Configure your environment.** Copy the example `.env.example` file to `.env` and edit it with your wallet address and pool information.
    ```bash
    cp .env.example .env
    nano .env
    ```

2.  **Build and run the Docker container:**
    - For NVIDIA GPUs, run the following command:
    ```bash
    sudo docker compose up -d --build nvidia
    ```
    - For AMD GPUs, run the following command:
    ```bash
    sudo docker compose up -d --build amd
    ```
    **Note:** The `docker-compose.yml` file is pre-configured to pass the necessary AMD GPU devices (`/dev/kfd` and `/dev/dri`) to the container. Ensure these devices exist on your host system.

## Multi-GPU Setup

For multi-GPU setups, separate Docker Compose files are provided to simplify the configuration. These files create a separate container for each GPU, allowing you to customize the worker name and other settings for each one.

### NVIDIA

To use this configuration for NVIDIA GPUs, run the following command:

```bash
sudo docker compose -f docker-compose.multi-gpu.yml up -d --build
```

By default, the file is configured for a two-GPU setup. To add more GPUs, you can duplicate the `ergo-miner-gpu1` service and update the following fields:

-   **Service name:** (e.g., `ergo-miner-gpu2`)
-   **Container name:** (e.g., `ergo-miner-gpu2`)
-   **`WORKER_NAME`:** (e.g., `ergo-miner-gpu2`)
-   **`GPU_DEVICES`:** (e.g., `2`)
-   **Host ports:** (e.g., `4446:4444`, `4459:4455`, `4460:4456`)
-   **`device_ids`:** (e.g., `['2']`)

### AMD

The AMD configuration utilizes `Dockerfile.amd` based on the ROCm runtime. To use this configuration for AMD GPUs, run the following command:

```bash
sudo docker compose -f docker-compose.multi-gpu.amd.yml up -d --build
```

**Note for AMD:** Ensure your user has permissions to access `/dev/kfd` and `/dev/dri`. Adding your user to the `video` and `render` groups on the host is usually required.

By default, the file is configured for a two-GPU setup. To add more GPUs, you can duplicate the `ergo-miner-gpu1` service and update the following fields:

-   **Service name:** (e.g., `ergo-miner-gpu2`)
-   **Container name:** (e.g., `ergo-miner-gpu2`)
-   **`WORKER_NAME`:** (e.g., `ergo-miner-gpu2`)
-   **`GPU_DEVICES`:** (e.g., `2`)
-   **Host ports:** (e.g., `4446:4444`, `4459:4455`, `4460:4456`)

## Environment Variable Reference

-   `POOL_ADDRESS`: The full address of the mining pool (e.g., `stratum+tcp://erg.2miners.com:8080`).
-   `BACKUP_POOL_ADDRESS`: The address of a backup mining pool. The miner will automatically failover to this pool if the primary one becomes unavailable.
-   `WALLET_ADDRESS`: Your Ergo wallet address where the mining rewards will be sent.
-   `WORKER_NAME`: A name for your mining rig to identify it on the pool's dashboard.
-   `GPU_DEVICES`: The specific GPU device(s) to use for mining. Set to `AUTO` to use all available GPUs, or specify a comma-separated list of device IDs (e.g., `0,1`).
-   `APPLY_OC`: Set to `true` to enable the automatic overclocking feature.
-   `GPU_CLOCK_OFFSET`: The desired GPU clock offset in MHz (e.g., `-200` or `200`).
-   `GPU_MEM_OFFSET`: The desired GPU memory offset in MHz (e.g., `800`).
-   `GPU_POWER_LIMIT`: The desired GPU power limit in watts (e.g., `250`).
-   `DUAL_ALGO`: (lolMiner only) The algorithm for dual mining (e.g., `KASPADUAL` for Kaspa, `ALEPHDUAL` for Alephium).
-   `DUAL_POOL`: (lolMiner only) The address of the dual mining pool.
-   `DUAL_WALLET`: (lolMiner only) Your wallet address for the second coin.
-   `DUAL_WORKER`: (lolMiner only) Optional worker name for the dual mining pool (defaults to `WORKER_NAME`).
-   `AUTO_PROFIT_SWITCHING`: Set to `true` to enable the automatic pool switching feature.
-   `TELEGRAM_ENABLE`: Set to `true` to enable Telegram notifications.
-   `TELEGRAM_BOT_TOKEN`: Your Telegram Bot API token.
-   `TELEGRAM_CHAT_ID`: Your Telegram Chat ID.
-   `TELEGRAM_NOTIFY_THRESHOLD`: Grace period in seconds before sending a downtime notification (default: `300`).
-   `PROFIT_SWITCHING_THRESHOLD`: Minimum profitability gain required to switch pools (e.g. `0.005` for 0.5%).
-   `PROFIT_SWITCHING_INTERVAL`: Time in seconds between profitability checks (default: `3600`).

## Auto-Profit Switching

This image includes a supervisor that periodically checks the profitability of supported pools (2Miners, HeroMiners, Nanopool, and WoolyPooly) based on their fees and current luck/effort. If it finds a pool that is significantly more profitable than your current pool, it will automatically update your configuration and restart the miner.

The default threshold for switching is a **0.5% gain**, and checks are performed **every hour**. Both parameters are configurable via environment variables or the web dashboard.

You can enable this feature during setup or by setting `AUTO_PROFIT_SWITCHING=true` in your `.env` file. The supervisor runs every hour and includes safety thresholds to prevent frequent switching.

## Dual Mining

This image supports dual mining with lolMiner. This allows you to mine Ergo and another coin (like Kaspa or Alephium) simultaneously to maximize your hardware's profitability.

To enable dual mining, set the following environment variables in your `.env` file:

- `DUAL_ALGO`: Set this to `KASPADUAL` for Kaspa or `ALEPHDUAL` for Alephium.
- `DUAL_POOL`: The pool address for the second coin.
- `DUAL_WALLET`: Your wallet address for the second coin.

The dashboard will automatically detect dual mining and display the hashrates for both algorithms.

## Overclocking

This image includes a feature to automatically apply overclocking settings to your NVIDIA GPUs on container startup. This can help you improve your hashrate and reduce power consumption.

**Note:** This feature is currently only supported for NVIDIA GPUs.

### **Disclaimer**

Overclocking can be risky and may damage your hardware if not done correctly. The author of this project is not responsible for any damage caused by the use of this feature. Please use it at your own risk and ensure you understand the proper overclocking settings for your specific GPU model.

### **Configuration**

For a detailed guide on the best overclocking settings for the latest hardware, check out our **[Overclocking Bible (RTX 40-Series)](OVERCLOCKING.md)**.

To enable overclocking, set the `APPLY_OC` environment variable to `true` in your `.env` file. You can then use the following variables to configure your desired settings:

-   `GPU_CLOCK_OFFSET`: The desired GPU clock offset in MHz.
-   `GPU_MEM_OFFSET`: The desired GPU memory offset in MHz.
-   `GPU_POWER_LIMIT`: The desired GPU power limit in watts.

The overclocking settings will be applied to all GPUs visible within the container.

**Security Note:** Applying overclocking settings requires the container to be started as `root` (UID 0). The `start.sh` script will apply the settings as root and then immediately drop privileges to the non-root `miner` user for the actual mining process.

## Security & Rootless Docker

This project is designed with security in mind.

### Non-Root Execution
By default, the mining process, dashboard, and metrics exporter run as a non-root user named `miner` (UID 1000) inside the container. This limits the potential impact of any vulnerability in the mining software.

### Rootless Docker Support
The image is compatible with [Rootless Docker](https://docs.docker.com/engine/security/rootless/). When running in a rootless environment:
- The container's `root` (UID 0) is mapped to your host user.
- The `start.sh` script will still function, but applying overclocking settings might require additional host-side configuration or may not be possible depending on your driver setup.
- Ensure your host user has permissions to access the GPU device nodes (`/dev/nvidia*` or `/dev/kfd`, `/dev/dri`).

### Running without Root Privileges
If you wish to run the container without *any* root privileges inside (i.e., skipping the initial root-based setup), you can start the container as UID 1000:
```bash
docker run --user 1000:1000 ...
```
*Note: If started as a non-root user, the automatic overclocking feature will be skipped as it requires root privileges.*

### Docker Secrets
For improved security, you can use Docker secrets to provide sensitive information like wallet addresses instead of including them in plain text in your `docker-compose.yml` or `.env` file.

The following secrets are supported:
- `WALLET_ADDRESS`: Your primary Ergo wallet address.
- `DUAL_WALLET`: Your wallet address for the second coin (if dual mining).

To use secrets in Docker Compose:
```yaml
services:
  nvidia:
    # ...
    secrets:
      - WALLET_ADDRESS
secrets:
  WALLET_ADDRESS:
    file: ./wallet_address.txt
```

### GPU Tuning Profiles

To simplify overclocking for different GPU models, this image supports tuning profiles. By setting the `GPU_PROFILE` environment variable to the name of a profile defined in `gpu_profiles.json`, you can apply pre-configured tuning settings.

**Example `gpu_profiles.json`:**
```json
{
  "RTX 3060": {
    "GPU_CLOCK_OFFSET": -200,
    "GPU_MEM_OFFSET": 1200,
    "GPU_POWER_LIMIT": 120
  },
  "RTX 3070": {
    "GPU_CLOCK_OFFSET": -200,
    "GPU_MEM_OFFSET": 1300,
    "GPU_POWER_LIMIT": 130
  }
}
```

To use the "RTX 3070" profile, set `GPU_PROFILE=RTX 3070` in your `.env` file.

If `GPU_PROFILE` is set, it will override any values set for `GPU_CLOCK_OFFSET`, `GPU_MEM_OFFSET`, and `GPU_POWER_LIMIT`. If the specified profile is not found in `gpu_profiles.json`, the script will fall back to using the individual environment variables.

### **Eco Mode**

The image includes a "Eco Mode" feature for NVIDIA RTX 30 and 40 series GPUs. When enabled, it automatically switches to a more conservative tuning profile that reduces power consumption while maintaining a solid hashrate for Ergo.

To enable Eco Mode:
1. Set `APPLY_OC=true` and `ECO_MODE=true` in your `.env` file.
2. Select a compatible `GPU_PROFILE` (e.g., `RTX 3070`) or use `AUTO` detection.

The miner will automatically look for an "(Eco)" version of your profile in `gpu_profiles.json` and apply those settings (lower power limits and core clock offsets).

## Verifying the Setup

You can monitor the miner's output and view logs using the following command:

```bash
sudo docker compose logs -f
```

## Monitoring

This Docker image includes built-in health checks and a metrics exporter to help you monitor your mining operation.

### Health Check

The container has a Docker health check that verifies:
1.  The miner process (lolMiner or T-Rex) is running.
2.  The miner is submitting hashrate.

If the miner process stops, the container will be restarted immediately. If the hashrate remains at 0 for more than 5 minutes (e.g., due to a hung API or driver issue), the health check will also trigger a restart. This ensures maximum uptime and prevents "zombie" mining sessions.

### Hashrate Logging and Weekly Reports

The miner includes a background process that appends hashrate snapshots to `hashrate_history.csv` every minute. Additionally, it generates a weekly summary report (`weekly_report.txt`) every 24 hours, calculating the average hashrate over the last 7 days. These reports and logs can be viewed and downloaded directly from the **History** page of the web dashboard.

### Telegram Notifications

You can receive instant alerts on your phone when your rig goes down. This feature is integrated into the metrics exporter and will notify you if:
1. The miner process crashes.
2. The miner API is unreachable.
3. The rig produces zero hashrate for a sustained period.

To set up Telegram notifications:
1. Create a new bot using [BotFather](https://t.me/botfather) and get your **Bot Token**.
2. Get your **Chat ID** (you can use a bot like [@userinfobot](https://t.me/userinfobot)).
3. Enable the feature during the interactive setup or by setting the `TELEGRAM_*` variables in your `.env` file.

The default notification threshold is 300 seconds (5 minutes), meaning you will only receive an alert if the rig stays down for that duration. You will also receive a follow-up message once the rig recovers.

### Prometheus Exporter

The image includes a built-in Prometheus exporter that provides key performance indicators.

-   **URL:** `http://<your-docker-host>:4455/metrics`
-   **Format:** Prometheus Text-Based

### **Key Metrics**

The exporter provides the following metrics, all labeled with `worker` for easy multi-rig aggregation:

- `miner_info`: Static information including `miner` type and `version`.
- `miner_hashrate`: Total rig hashrate in MH/s.
- `miner_uptime`: Miner session uptime in seconds.
- `miner_api_up`: Status of the miner API (1 for UP, 0 for DOWN).
- `miner_total_power_draw`: Total power consumption in watts.
- `miner_gpu_hashrate`: Per-GPU hashrate (labeled with `gpu` index).
- `miner_gpu_temperature`: Per-GPU temperature in °C.
- `miner_gpu_power_draw`: Per-GPU power draw in watts.

This endpoint can be scraped by a Prometheus server to collect and store the metrics over time.

### Grafana Dashboard

A pre-configured Grafana dashboard is available in the `grafana-dashboard.json` file. You can import this dashboard into your Grafana instance to get a visual representation of your miner's performance. The dashboard is designed for multi-GPU setups (supporting up to 6+ GPUs on one screen) and includes:

-   **GPU Current Status Table:** An at-a-glance overview of hashrate, dual hashrate, temperature, fan speed, and power draw for all GPUs.
-   **Total Metrics:** Timeseries for Total Hashrate, Total Dual Hashrate, Total Power Draw, and Average Fan Speed.
-   **Per-GPU Metrics:** Detailed timeseries for Hashrate, Dual Hashrate, Temperature, Power Draw, and Fan Speed for each individual GPU.
-   **Share Tracking:** Accepted and Rejected shares per GPU.

## Profitability Estimation

Mining profitability can vary significantly based on your hardware, electricity costs, and the current price of Ergo. This section provides some general estimates to help you gauge your potential earnings.

### Expected Hashrate & Power Consumption

The following table lists the approximate hashrate and power consumption for popular NVIDIA GPUs when mining Ergo. These values can vary depending on your specific GPU model, overclocking settings, and the mining software you use.

| GPU Model         | Hashrate (MH/s) | Power Consumption (Watts) |
| ----------------- | --------------- | ------------------------- |
| NVIDIA RTX 3080   | 200 - 235       | 230 - 250                 |
| NVIDIA RTX 3070   | 170 - 180       | 120 - 140                 |
| NVIDIA RTX 3060   | 120 - 130       | 110 - 120                 |
| AMD RX 6800       | 160 - 170       | 110 - 130                 |
| AMD RX 6700 XT    | 110 - 120       | 95 - 110                  |

*Note: These are estimates based on community-reported data. Your actual performance may vary depending on your specific hardware, driver versions, and overclocking settings.*

### Pool Fees

Most mining pools charge a fee for their services, which is typically a percentage of your mining rewards. This fee can range from **1% to 2%**. Be sure to check the fee structure of your chosen pool.

Here's a comparison of some popular Ergo mining pools:

| Pool           | Fee Structure     | Minimum Payout |
| -------------- | ----------------- | -------------- |
| Nanopool       | 1% PPLNS          | 1 ERG          |
| WoolyPooly     | 0.9% PPLNS or SOLO | 1 ERG          |
| 2Miners        | 1% PPLNS or 1.5% SOLO | 1 ERG          |
| HeroMiners     | 0% PROP           | 0.5 ERG        |

*Note: PPLNS (Pay Per Last N Shares) and PROP (Proportional) are different reward distribution methods. Your choice of pool may also depend on factors like server location, hashrate, and community.*

### Break-Even Calculator

To calculate your break-even point and estimate your profitability, you need to consider the following factors:

*   **Total Hashrate (H):** The combined hashrate of all your GPUs in MH/s.
*   **Total Power Consumption (P):** The total power draw of your mining rig in watts.
*   **Electricity Cost (C):** Your cost per kilowatt-hour (kWh).
*   **Pool Fee (F):** The fee charged by your mining pool (e.g., 1% = 0.01).
*   **Ergo Price (ERG_P):** The current market price of ERG.
*   **Network Difficulty (D):** The current difficulty of the Ergo network.
*   **Block Reward (R):** The number of ERG coins awarded for solving a block.

#### Profitability Formula

You can use the following formula to estimate your daily earnings:

**Daily Earnings (ERG) = (H * 10^6 * R * 86400) / (D * 2^32)**

*   **86400** is the number of seconds in a day.
*   **2^32** is a constant used in the Ergo mining algorithm.

To calculate your daily profit in USD, you can use this formula:

**Daily Profit (USD) = (Daily Earnings (ERG) * ERG_P) - ((P / 1000) * 24 * C) - (Daily Earnings (ERG) * ERG_P * F)**

#### Online Calculators

For a more straightforward approach, you can use an online profitability calculator. These tools automatically fetch the latest network difficulty and Ergo price, making it easier to get an accurate estimate.

*   [WhatToMine](https://whattomine.com/coins/345-erg-autolykos2)
*   [2CryptoCalc](https://2cryptocalc.com/erg-mining-calculator)
*   [MinerStat](https://minerstat.com/coin/ERG)

**Disclaimer:** The information provided in this guide is for estimation purposes only. Your actual profitability may vary due to fluctuations in network difficulty, coin price, and other factors. Always do your own research and calculations before making any investment decisions.

## Troubleshooting

-   **Container exits immediately:** Check the container logs for errors using `docker compose logs`. This is often due to an incorrect `.env` file or NVIDIA driver issues.
-   **`nvidia-container-cli: initialization error`:** This indicates a problem with the NVIDIA Container Toolkit installation. Ensure it's properly installed and configured.
-   **Low hashrate:** This could be due to a number of factors, including GPU overheating, incorrect drivers, or suboptimal lolMiner settings.

## Building from Source

To use a different version of lolMiner, you can pass the `LOLMINER_VERSION` build argument during the build process. For example:

```bash
docker compose build --build-arg LOLMINER_VERSION=1.92
```

The interactive `setup.sh` script automatically fetches the latest lolMiner version and configures it in your `.env` file, which is then passed as a build argument by Docker Compose.

For advanced configurations, you can edit the `start.sh` script to pass additional command-line arguments to the miner.

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request with your suggested changes.
