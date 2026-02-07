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

## Requirements

- [Docker](https.docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### For NVIDIA Users

- [NVIDIA Drivers](https://www.nvidia.com/Download/index.aspx)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- CUDA-enabled NVIDIA GPU

### For AMD Users

- [ROCm Drivers](https://rocm.docs.amd.com/en/latest/deploy/linux/index.html)
- AMD GPU

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

To use this configuration for AMD GPUs, run the following command:

```bash
sudo docker compose -f docker-compose.multi-gpu.amd.yml up -d --build
```

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

To enable overclocking, set the `APPLY_OC` environment variable to `true` in your `.env` file. You can then use the following variables to configure your desired settings:

-   `GPU_CLOCK_OFFSET`: The desired GPU clock offset in MHz.
-   `GPU_MEM_OFFSET`: The desired GPU memory offset in MHz.
-   `GPU_POWER_LIMIT`: The desired GPU power limit in watts.

The overclocking settings will be applied to all GPUs visible within the container.


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

### Prometheus Exporter

The image includes a built-in Prometheus exporter that provides key performance indicators.

-   **URL:** `http://<your-docker-host>:4455/metrics`
-   **Format:** Prometheus Text-Based

This endpoint can be scraped by a Prometheus server to collect and store the metrics over time.

### Grafana Dashboard

A pre-configured Grafana dashboard is available in the `grafana-dashboard.json` file. You can import this dashboard into your Grafana instance to get a visual representation of your miner's performance. The dashboard includes panels for:

-   Total Hashrate
-   Individual GPU Hashrate
-   GPU Temperatures
-   GPU Power Draw
-   GPU Fan Speeds
-   Accepted and Rejected Shares

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

To use a different version of lolMiner, you can modify the `LOLMINER_URL` in the `Dockerfile` and rebuild the image. For advanced configurations, you can edit the `start.sh` script to pass additional command-line arguments to the miner.

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request with your suggested changes.
