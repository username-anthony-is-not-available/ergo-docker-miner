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
    sudo docker run --gpus all -d --name ergo-miner --env-file .env --restart unless-stopped ergo-miner
    ```

## Environment Variable Reference

-   `POOL_ADDRESS`: The full address of the mining pool (e.g., `stratum+tcp://erg.2miners.com:8080`).
-   `WALLET_ADDRESS`: Your Ergo wallet address where the mining rewards will be sent.
-   `WORKER_NAME`: A name for your mining rig to identify it on the pool's dashboard.
-   `GPU_DEVICES`: The specific GPU device(s) to use for mining (e.g., `0` for the first GPU, `0,1` for the first two).

## Verifying the Setup

You can monitor the miner's output and view logs using the following command:

```bash
sudo docker logs -f ergo-miner
```

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
