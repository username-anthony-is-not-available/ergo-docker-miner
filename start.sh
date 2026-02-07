#!/bin/bash

# Start the metrics exporter in the background
./metrics.sh &

# Start the dashboard in the background
python3 dashboard.py &

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

  # Determine which OC settings to use
  if [ -n "$GPU_PROFILE" ] && [ -f "gpu_profiles.json" ]; then
    echo "Using GPU profile: $GPU_PROFILE"
    PROFILE_SETTINGS=$(jq -r ".[\"$GPU_PROFILE\"]" gpu_profiles.json)

    if [ "$PROFILE_SETTINGS" != "null" ]; then
      # Extract settings from JSON
      GPU_CLOCK_OFFSET=$(echo "$PROFILE_SETTINGS" | jq -r ".GPU_CLOCK_OFFSET // \"\"")
      GPU_MEM_OFFSET=$(echo "$PROFILE_SETTINGS" | jq -r ".GPU_MEM_OFFSET // \"\"")
      GPU_POWER_LIMIT=$(echo "$PROFILE_SETTINGS" | jq -r ".GPU_POWER_LIMIT // \"\"")
      echo "Applying profile settings: CLOCK=${GPU_CLOCK_OFFSET}, MEM=${GPU_MEM_OFFSET}, PL=${GPU_POWER_LIMIT}"
    else
      echo "Warning: GPU profile '$GPU_PROFILE' not found in gpu_profiles.json. Falling back to environment variables."
    fi
  else
    echo "Using overclock settings from environment variables."
  fi

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

# Default to lolminer if MINER is not set
MINER=${MINER:-lolminer}

echo "Starting miner: $MINER"

# Miner-specific configuration
case "$MINER" in
  lolminer)
    MINER_BIN="/app/lolMiner"
    MINER_CONFIG="--algo AUTOLYKOS2 --pool ${POOL_ADDRESS} --user ${WALLET_ADDRESS}.${WORKER_NAME} --devices ${GPU_DEVICES} --apiport 4444 --json-read-only"
    # Add backup pool if it's defined
    if [ -n "$BACKUP_POOL_ADDRESS" ]; then
      MINER_CONFIG="$MINER_CONFIG --pool ${BACKUP_POOL_ADDRESS}"
    fi
    # Add dual mining parameters if DUAL_ALGO is set
    if [ -n "$DUAL_ALGO" ]; then
      echo "Configuring dual mining: ERGO + $DUAL_ALGO"
      MINER_CONFIG="$MINER_CONFIG --dualmode ${DUAL_ALGO} --dualpool ${DUAL_POOL} --dualuser ${DUAL_WALLET}.${DUAL_WORKER:-$WORKER_NAME}"
    fi
    ;;
  t-rex)
    MINER_BIN="/app/t-rex"
    MINER_CONFIG="-a AUTOLYKOS2 -o ${POOL_ADDRESS} -u ${WALLET_ADDRESS}.${WORKER_NAME} -d ${GPU_DEVICES} --api-bind-http 127.0.0.1:4444"
    # Add backup pool if it's defined
    if [ -n "$BACKUP_POOL_ADDRESS" ]; then
      MINER_CONFIG="$MINER_CONFIG -o2 ${BACKUP_POOL_ADDRESS} -u2 ${WALLET_ADDRESS}.${WORKER_NAME}"
    fi
    ;;
  *)
    echo "Unsupported miner: $MINER"
    exit 1
    ;;
esac

# Start the selected miner
if [ -n "$TEST_MODE" ]; then
  $MINER_BIN $MINER_CONFIG &
  tail -f /dev/null
else
  exec $MINER_BIN $MINER_CONFIG
fi
