#!/bin/bash

# Start the metrics exporter in the background
./metrics.sh &

# Start GPU monitoring in the background based on available tools
if command -v nvidia-smi &> /dev/null; then
  (
    # Add a small delay to prevent log interleaving at startup
    sleep 5
    while true; do
      echo "--- GPU Stats ---"
      nvidia-smi --query-gpu=index,temperature.gpu,power.draw,fan.speed --format=csv,noheader,nounits | while IFS=, read -r index temp power fan; do
        # Trim leading/trailing whitespace
        index=$(echo "$index" | xargs)
        temp=$(echo "$temp" | xargs)
        power=$(echo "$power" | xargs)
        fan=$(echo "$fan" | xargs)
        echo "GPU $index: Temp: ${temp}°C, Power: ${power}W, Fan: ${fan}%"
      done
      echo "-----------------"
      sleep 10
    done
  ) &
elif command -v rocm-smi &> /dev/null; then
  (
    sleep 5
    while true; do
      echo "--- GPU Stats ---"
      # The rocm-smi csv output has a header, so we skip it with tail
      rocm-smi --showtemp --showpower --showfan --csv | tail -n +2 | while IFS=, read -r card temp power fan; do
        # Trim leading/trailing whitespace
        card=$(echo "$card" | xargs)
        temp=$(echo "$temp" | xargs)
        power=$(echo "$power" | xargs)
        fan=$(echo "$fan" | xargs)
        echo "GPU ${card}: Temp: ${temp}°C, Power: ${power}W, Fan: ${fan}%"
      done
      echo "-----------------"
      sleep 10
    done
  ) &
fi

# Apply overclocking settings if enabled and nvidia-smi is present
if [ "$APPLY_OC" = "true" ] && command -v nvidia-smi &> /dev/null; then
  echo "Applying overclocking settings..."
  # Start a virtual X server for nvidia-settings
  export DISPLAY=:0
  Xorg -core :0 &
  XORG_PID=$!
  sleep 3

  # Enable persistence mode
  nvidia-smi -pm 1

  # Apply settings to all GPUs visible in the container
  for GPU_INDEX in $(nvidia-smi --query-gpu=index --format=csv,noheader); do
    echo "Applying settings to GPU ${GPU_INDEX}..."
    [ -n "$GPU_POWER_LIMIT" ] && [ "$GPU_POWER_LIMIT" -gt 0 ] && nvidia-smi -i "$GPU_INDEX" -pl "$GPU_POWER_LIMIT"
    [ -n "$GPU_CLOCK_OFFSET" ] && nvidia-settings -a "[gpu:${GPU_INDEX}]/GPUGraphicsClockOffsetAllPerformanceLevels=${GPU_CLOCK_OFFSET}"
    [ -n "$GPU_MEM_OFFSET" ] && nvidia-settings -a "[gpu:${GPU_INDEX}]/GPUMemoryTransferRateOffsetAllPerformanceLevels=${GPU_MEM_OFFSET}"
  done

  # Terminate the virtual X server
  kill $XORG_PID
  wait $XORG_PID 2>/dev/null

  echo "Overclocking settings applied."
fi

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
