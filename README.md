# Ergo Docker Miner

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This project provides a Dockerized solution for mining Ergo (ERG) using lolMiner. It simplifies the setup process and ensures a consistent mining environment.

## Features

- **Automated Failover:** Automatically switches to a backup pool if the primary one is unavailable.
- **Health Monitoring:** Includes a Docker health check to ensure the miner is running correctly.
- **Performance Metrics:** Exposes a JSON endpoint for easy integration with monitoring tools.
- **Web Dashboard:** Provides a simple web interface to view real-time mining statistics.
- **Auto-Restart:** Automatically restarts the container if the miner crashes or becomes unresponsive.
- **Automatic Overclocking:** Apply overclocking settings to your GPUs to improve performance and efficiency.

## Requirements

- [Docker](https.docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [NVIDIA Drivers](https://www.nvidia.com/Download/index.aspx)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- CUDA-enabled NVIDIA GPU

## Setup

1.  **Configure your environment.** Copy the example `.env.example` file to `.env` and edit it with your wallet address and pool information.
    ```bash
    cp .env.example .env
    nano .env
    ```

2.  **Build and run the Docker container:**
    ```bash
    sudo docker-compose up -d --build
    ```

## Multi-GPU Setup

For multi-GPU setups, a separate Docker Compose file is provided to simplify the configuration. This file (`docker-compose.multi-gpu.yml`) creates a separate container for each GPU, allowing you to customize the worker name and other settings for each one.

To use this configuration, run the following command:

```bash
sudo docker-compose -f docker-compose.multi-gpu.yml up -d --build
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
sudo docker-compose logs -f
```

## Monitoring

This Docker image includes built-in health checks and a metrics exporter to help you monitor your mining operation.

### Health Check

The container has a Docker health check that verifies the lolMiner API is running and responsive. If the miner crashes or the API becomes unavailable, the container will be marked as "unhealthy" and automatically restarted.

### Web Dashboard

The image includes a web dashboard to view real-time mining statistics.

-   **URL:** `http://<your-docker-host>:4456`

### Metrics Endpoint

The image also includes a lightweight metrics exporter that provides key performance indicators in a simple JSON format.

-   **URL:** `http://<your-docker-host>:4455`
-   **Method:** `GET`

**Example Output:**

```json
{
  "hashrate": "246.90 MH/s",
  "avg_temperature": "65",
  "avg_fan_speed": "80",
  "gpus": [
    {
      "hashrate": "123.45 MH/s"
    },
    {
      "hashrate": "123.45 MH/s"
    }
  ]
}
```

If the miner is not running or the API is unavailable, the endpoint will return "N/A" for all values:

```json
{
  "hashrate": "N/A",
  "avg_temperature": "N/A",
  "avg_fan_speed": "N/A",
  "gpus": []
}
```

You can use this endpoint to integrate with monitoring systems like Prometheus (with a simple exporter), Grafana, or your own custom scripts.

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

### Pool Fees

Most mining pools charge a fee for their services, which is typically a percentage of your mining rewards. This fee can range from **1% to 2%**. Be sure to check the fee structure of your chosen pool.

### Break-Even Calculator

To calculate your break-even point, you need to consider the following:

*   **Total Hashrate:** The combined hashrate of all your GPUs.
*   **Total Power Consumption:** The total power draw of your mining rig in watts.
*   **Electricity Cost:** Your cost per kilowatt-hour (kWh).
*   **Pool Fee:** The fee charged by your mining pool.
*   **Ergo Price:** The current market price of ERG.
*   **Network Difficulty:** The current difficulty of the Ergo network.

There are several online profitability calculators that can help you with this calculation. Here are a few popular options:

*   [WhatToMine](https://whattomine.com/coins/345-erg-autolykos2)
*   [2CryptoCalc](https://2cryptocalc.com/erg-mining-calculator)
*   [MinerStat](https://minerstat.com/coin/ERG)

**Disclaimer:** The information provided in this guide is for estimation purposes only. Your actual profitability may vary. Always do your own research and calculations before making any investment decisions.

## Troubleshooting

-   **Container exits immediately:** Check the container logs for errors using `docker-compose logs`. This is often due to an incorrect `.env` file or NVIDIA driver issues.
-   **`nvidia-container-cli: initialization error`:** This indicates a problem with the NVIDIA Container Toolkit installation. Ensure it's properly installed and configured.
-   **Low hashrate:** This could be due to a number of factors, including GPU overheating, incorrect drivers, or suboptimal lolMiner settings.

## Building from Source

To use a different version of lolMiner, you can modify the `LOLMINER_URL` in the `Dockerfile` and rebuild the image. For advanced configurations, you can edit the `start.sh` script to pass additional command-line arguments to the miner.

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request with your suggested changes.
