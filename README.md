# Ergo Docker Miner

This project provides a Dockerized solution for mining Ergo (ERG) using lolMiner.

## Setup

1. Install Docker and the NVIDIA Container Toolkit.
2. Create a `.env` file in the project root with the following content, replacing the placeholders with your actual values:

   ```bash
   POOL_ADDRESS=stratum+tcp://erg.2miners.com:8080
   WALLET_ADDRESS=YourErgoWalletAddress
   WORKER_NAME=YourWorkerName
   GPU_DEVICES=0
   ```

3. Build the Docker image:

   ```bash
   docker build -t ergo-miner .
   ```

4. Run the Docker container:

   ```bash
   docker run --gpus all -d --name ergo-miner --env-file .env --restart unless-stopped ergo-miner
   ```

...
