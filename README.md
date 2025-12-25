# Ergo Docker Miner

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This project provides a Dockerized solution for mining Ergo (ERG) using lolMiner. It simplifies the setup process and ensures a consistent mining environment.

## Features

- **Automated Failover:** Automatically switches to a backup pool if the primary one is unavailable.
- **Health Monitoring:** Includes a Docker health check to ensure the miner is running correctly.
- **Performance Metrics:** Exposes a JSON endpoint for easy integration with monitoring tools.
- **Web Dashboard:** Provides a simple web interface to view real-time mining statistics.
- **Auto-Restart:** Automatically restarts the container if the miner crashes or becomes unresponsive.

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

## Environment Variable Reference

-   `POOL_ADDRESS`: The full address of the mining pool (e.g., `stratum+tcp://erg.2miners.com:8080`).
-   `BACKUP_POOL_ADDRESS`: The address of a backup mining pool. The miner will automatically failover to this pool if the primary one becomes unavailable.
-   `WALLET_ADDRESS`: Your Ergo wallet address where the mining rewards will be sent.
-   `WORKER_NAME`: A name for your mining rig to identify it on the pool's dashboard.
-   `GPU_DEVICES`: The specific GPU device(s) to use for mining. Set to `AUTO` to use all available GPUs, or specify a comma-separated list of device IDs (e.g., `0,1`).

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
