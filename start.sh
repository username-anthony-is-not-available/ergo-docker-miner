#!/bin/bash

# Start the metrics exporter in the background
./metrics.sh &

# Base miner configuration
MINER_CONFIG="--algo AUTOLYKOS2 --pool ${POOL_ADDRESS} --user ${WALLET_ADDRESS}.${WORKER_NAME} --devices ${GPU_DEVICES} --apiport 4444 --json-read-only"

# Add backup pool if it's defined
if [ -n "$BACKUP_POOL_ADDRESS" ]; then
  MINER_CONFIG="$MINER_CONFIG --pool ${BACKUP_POOL_ADDRESS}"
fi

echo "$MINER_CONFIG" > miner_config.sh

chmod +x miner_config.sh

/app/1.92/lolMiner $(cat miner_config.sh)
