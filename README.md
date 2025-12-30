# Ergo Docker Miner

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This project provides a Dockerized solution for mining Ergo (ERG) using lolMiner. It simplifies the setup process and ensures a consistent mining environment.

## Features

- **Automated Failover:** Automatically switches to a backup pool if the primary one is unavailable.
- **Health Monitoring:** Includes a Docker health check to ensure the miner is running correctly.
- **Prometheus Exporter:** Exposes a Prometheus endpoint for easy integration with monitoring tools.
- **Grafana Dashboard:** Includes a pre-configured Grafana dashboard to visualize your mining performance.
- **Auto-Restart:** Automatically restarts the container if the miner crashes or becomes unresponsive.
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

For multi-GPU setups, a separate Docker Compose file is provided to simplify the configuration. This file (`docker-compose.multi-gpu.yml`) creates a separate container for each GPU, allowing you to customize the worker name and other settings for each one.

To use this configuration, run the following command:

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

## Verifying the Setup

You can monitor the miner's output and view logs using the following command:

```bash
sudo docker compose logs -f
```

## Monitoring

This Docker image includes built-in health checks and a metrics exporter to help you monitor your mining operation.

### Health Check

The container has a Docker health check that verifies the lolMiner API is running and responsive. If the miner crashes or the API becomes unavailable, the container will be marked as "unhealthy" and automatically restarted.

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

| GPU Model        | Hashrate (MH/s) | Power Consumption (Watts) |
| ---------------- | --------------- | ------------------------- |
| NVIDIA RTX 3080  | 200 - 235       | 230 - 250                 |
| NVIDIA RTX 3070  | 170 - 180       | 120 - 140                 |
| NVIDIA RTX 3060  | 120 - 130       | 110 - 120                 |

*Note: These are estimates. Your actual performance may vary.*

### Pool Fee Comparison

| Pool Name        | Fee   |
| ---------------- | ----- |
| F2Pool           | 2.5%  |
| 666 POOL         | 1%    |
| HEROMINERS       | 0%    |
| NANOPOOL         | 1%    |
| WOOLYPOOLY       | 0.9%  |
| 2MINERS          | 1%    |
| KRYPTEX          | 1%    |
| K1POOL           | 1%    |
| Sigmanauts Pool  | 0.9%  |

*Note: Fees are subject to change. Please verify the current fee on the pool's website.*

### Break-Even Calculator

Calculating your break-even point is crucial to determine if mining Ergo will be profitable for you. This calculation depends on several constantly changing factors:

*   **Total Hashrate:** This is the speed at which your mining hardware can perform calculations, measured in megahashes per second (MH/s) or gigahashes per second (GH/s). A higher hashrate means you can solve more blocks and earn more rewards.
*   **Total Power Consumption:** Your mining rig consumes a significant amount of electricity. This is measured in watts (W) and is a major operational cost.
*   **Electricity Cost:** The price you pay for electricity, usually measured in dollars per kilowatt-hour ($/kWh). This varies greatly by location and is a critical factor in your profitability.
*   **Pool Fee:** The percentage of your mining rewards that you pay to the mining pool for their services.
*   **Ergo (ERG) Price:** The current market price of Ergo. Since your rewards are paid in ERG, its value directly impacts your earnings in fiat currency (like USD).
*   **Network Difficulty:** This is a measure of how difficult it is to find a new block. As more miners join the network, the difficulty increases, which means your share of the rewards will decrease if your hashrate stays the same.

**Using an Online Calculator**

Instead of performing complex manual calculations, it's highly recommended to use an online profitability calculator. These tools automatically fetch the latest Ergo price and network difficulty, allowing you to get a more accurate estimate. Simply input your hashrate, power consumption, electricity cost, and pool fee.

Here are a few popular options:

*   [WhatToMine](https://whattomine.com/coins/345-erg-autolykos2)
*   [2CryptoCalc](https://2cryptocalc.com/erg-mining-calculator)
*   [MinerStat](https://minerstat.com/coin/ERG)

**Disclaimer:** The profitability estimates provided by these calculators are not guarantees. They are based on current market conditions and can change rapidly. It is essential to do your own research and understand the risks involved before investing in mining hardware.

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
