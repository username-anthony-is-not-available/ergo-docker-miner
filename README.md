# Ergo Docker Miner

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This project provides a Dockerized solution for mining Ergo (ERG) using lolMiner. It simplifies the setup process and ensures a consistent mining environment.

## Requirements

To use this Dockerized Ergo miner, you need the following:

- **Docker:** The containerization platform to run the miner. Follow the [official installation guide](https://docs.docker.com/engine/install/) for your operating system.
- **NVIDIA Drivers:** The official NVIDIA drivers for your GPU must be installed on the host machine.
- **NVIDIA Container Toolkit:** This package allows Docker to access the GPU. Follow the [official installation guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).
- **GPU Compatibility:** A CUDA-enabled NVIDIA GPU is required.

## Setup

1.  **Configure your environment.** Copy the example `.env.example` file to `.env` and edit it with your wallet address and pool information.
    ```bash
    cp .env.example .env
    nano .env
    ```

2.  **Build the Docker image:**
    ```bash
    sudo docker build -t ergo-miner .
    ```

3.  **Run the Docker container:**
    ```bash
    sudo docker run --gpus all -d --name ergo-miner -p 4444:4444 -p 4455:4455 --env-file .env --restart unless-stopped ergo-miner
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
sudo docker logs -f ergo-miner
```

## Monitoring

This Docker image includes built-in health checks and a metrics exporter to help you monitor your mining operation.

### Health Check

The container has a Docker health check that verifies the lolMiner API is running and responsive. If the miner crashes or the API becomes unavailable, the container will be marked as "unhealthy" and automatically restarted (if you're using the `--restart unless-stopped` flag).

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

-   **Container exits immediately:** Check the container logs for errors using `docker logs ergo-miner`. This is often due to an incorrect `.env` file or NVIDIA driver issues.
-   **`nvidia-container-cli: initialization error`:** This indicates a problem with the NVIDIA Container Toolkit installation. Ensure it's properly installed and configured.
-   **Low hashrate:** This could be due to a number of factors, including GPU overheating, incorrect drivers, or suboptimal lolMiner settings.

## Building from Source

To use a different version of lolMiner, you can modify the `LOLMINER_URL` in the `Dockerfile` and rebuild the image.

## Performance Tuning Tips

For advanced users, you can pass additional command-line arguments to lolMiner by modifying `miner_config.template`. Refer to the [lolMiner documentation](https://github.com/Lolliedieb/lolMiner-releases) for a full list of available options.

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request with your suggested changes.
