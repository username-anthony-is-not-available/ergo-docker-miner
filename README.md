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

The following tables list the approximate hashrate and power consumption for popular NVIDIA and AMD GPUs when mining Ergo. These values can vary depending on your specific GPU model, overclocking settings, and the mining software you use.

**NVIDIA**

| GPU Model             | Hashrate (MH/s) | Power Consumption (Watts) |
| --------------------- | --------------- | ------------------------- |
| NVIDIA RTX 3090       | 270 - 275       | 260 - 270                 |
| NVIDIA RTX 3080       | 215 - 220       | 175 - 185                 |
| NVIDIA RTX 3070 Ti    | 170 - 175       | 155 - 165                 |
| NVIDIA RTX 3070       | 170 - 175       | 125 - 135                 |
| NVIDIA RTX 3060 Ti    | 130 - 135       | 115 - 125                 |
| NVIDIA RTX 3060       | 105 - 110       | 105 - 115                 |
| NVIDIA GTX 1660 Ti    | 48 - 50         | 90 - 95                   |
| NVIDIA GTX 1660       | 40 - 42         | 70 - 75                   |

**AMD**

| GPU Model       | Hashrate (MH/s) | Power Consumption (Watts) |
| --------------- | --------------- | ------------------------- |
| AMD RX Vega 56  | 160 - 165       | 115 - 125                 |
| AMD RX Vega 64  | 160 - 165       | 130 - 135                 |
| AMD RX 5700 XT  | 90 - 95         | 105 - 110                 |
| AMD RX 6800     | 110 - 115       | 130 - 135                 |
| AMD RX 6800 XT  | 115 - 120       | 200 - 210                 |

*Note: These are estimates. Your actual performance may vary.*

### Pool Fee Comparison

Most mining pools charge a fee for their services, which is typically a percentage of your mining rewards. The table below compares the fees and payout schemes for some of the most popular Ergo mining pools.

| Pool          | Fee       | Payout Scheme | Minimum Payout |
| ------------- | --------- | ------------- | -------------- |
| Nanopool      | 1%        | PPLNS         | 1 ERG          |
| WoolyPooly    | 0.9%      | PPLNS         | 1 ERG          |
| 2Miners       | 1%        | PPLNS         | 1 ERG          |
| HeroMiners    | 0%        | PROP          | 0.5 ERG        |
| Cruxpool      | 1%        | PPS+          | 1 ERG          |

*Note: Pool fees and payout schemes are subject to change. Always verify the latest information on the pool's website.*

### Break-Even and Profitability Calculator

Calculating your break-even point and potential profitability is crucial for a successful mining operation. This section provides a more detailed guide to help you understand the key factors and perform your own calculations.

**Key Factors:**

*   **Hardware Cost:** The initial investment in your mining rig, including GPUs, motherboard, CPU, RAM, and power supply.
*   **Total Hashrate:** The combined hashrate of all your GPUs in MH/s. You can use the tables above as a starting point.
*   **Total Power Consumption:** The total power draw of your mining rig in watts. This can be measured with a wattmeter for the most accurate reading.
*   **Electricity Cost:** Your cost per kilowatt-hour (kWh). This can be found on your utility bill.
*   **Pool Fee:** The fee charged by your chosen mining pool (e.g., 1%).
*   **Ergo Price:** The current market price of ERG.
*   **Network Difficulty:** The current difficulty of the Ergo network. A higher difficulty means it's harder to find a block, which can impact your earnings.

**Step-by-Step Calculation:**

1.  **Calculate your daily electricity cost:**
    ```
    (Total Power Consumption (Watts) / 1000) * 24 * Electricity Cost ($/kWh)
    ```

2.  **Estimate your daily ERG earnings:**
    This is best done using an online calculator, as it takes into account the current network difficulty and block reward.

3.  **Calculate your daily profit:**
    ```
    (Daily ERG Earnings * ERG Price) - Daily Electricity Cost
    ```

4.  **Calculate your break-even point:**
    ```
    Hardware Cost / Daily Profit
    ```
    This will give you the number of days it will take to pay off your initial hardware investment.

**Online Calculators:**

While it's helpful to understand the manual calculation process, online profitability calculators can simplify the process by automatically fetching the latest Ergo price and network difficulty. Here are a few popular options:

*   [WhatToMine](https://whattomine.com/coins/345-erg-autolykos2)
*   [2CryptoCalc](https://2cryptocalc.com/erg-mining-calculator)
*   [MinerStat](https://minerstat.com/coin/ERG)

**Disclaimer:** The information provided in this guide is for estimation purposes only. Your actual profitability may vary due to market volatility and changes in network difficulty. Always do your own research and calculations before making any investment decisions.

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
