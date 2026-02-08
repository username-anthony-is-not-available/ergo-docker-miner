#!/bin/bash
# cuda_monitor.sh - Background monitor for CUDA errors in miner logs

LOG_FILE="miner.log"

# Wait for log file to be created by the miner
echo "Waiting for $LOG_FILE to be created..."
while [ ! -f "$LOG_FILE" ]; do
  sleep 2
done

echo "Starting CUDA error monitor on $LOG_FILE..."

# Pattern to match common CUDA errors across different miners
# Case-insensitive match for:
# - out of memory
# - illegal instruction
# - CUDA error
# - GPU fell off the bus
# - an illegal memory access was encountered
ERROR_PATTERN="out of memory|illegal instruction|CUDA error|GPU fell off the bus|an illegal memory access was encountered"

tail -F "$LOG_FILE" | while read -r line; do
  if echo "$line" | grep -Ei "$ERROR_PATTERN" > /dev/null; then
    echo "$(date): CRITICAL: CUDA error detected: $line"
    echo "$(date): Triggering auto-restart..."
    # Give it a second to log the error fully
    sleep 1
    ./restart.sh
    # Monitor exits after triggering restart as the whole container will restart
    exit 0
  fi
done
