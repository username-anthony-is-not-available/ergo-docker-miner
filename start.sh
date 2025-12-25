#!/bin/bash

# Start the metrics exporter in the background
./metrics.sh &

# Base miner configuration
MINER_CONFIG="--algo AUTOLYKOS2 --pool ${POOL_ADDRESS} --user ${WALLET_ADDRESS}.${WORKER_NAME} --devices ${GPU_DEVICES} --apiport 4444 --json-read-only"

# Add backup pool if it's defined
if [ -n "$BACKUP_POOL_ADDRESS" ]; then
  MINER_CONFIG="$MINER_CONFIG --pool ${BACKUP_POOL_ADDRESS}"
fi

if [ -n "$TEST_MODE" ]; then
  /app/lolMiner $MINER_CONFIG &
  tail -f /dev/null
else
  exec /app/lolMiner $MINER_CONFIG
fi
