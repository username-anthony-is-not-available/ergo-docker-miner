#!/bin/bash

# Support Docker secrets for sensitive variables
load_secret() {
    local var=$1
    local file="/run/secrets/$var"
    if [ -f "$file" ]; then
        if [ -z "${!var}" ]; then
            export "$var"=$(cat "$file" | tr -d '\r\n')
            echo "Loaded $var from secret."
        fi
    fi
}

load_secret WALLET_ADDRESS
load_secret DUAL_WALLET

# Default to /app/data if DATA_DIR is not set
DATA_DIR=${DATA_DIR:-/app/data}

# Handle privilege dropping if running as root
if [ "$(id -u)" = '0' ]; then
  echo "Running as root. Ensuring $DATA_DIR ownership and applying OC settings..."
  mkdir -p "$DATA_DIR"
  chown -R miner:miner "$DATA_DIR"

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
    if [ -f "gpu_profiles.json" ]; then
      if [ -z "$GPU_PROFILE" ] || [ "$GPU_PROFILE" == "AUTO" ]; then
        echo "Attempting to auto-detect GPU profile..."
        DETECTED_GPU=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1)
        echo "Detected GPU: $DETECTED_GPU"

        # Use python for robust substring matching against profile keys
        GPU_PROFILE=$(DETECTED_GPU="$DETECTED_GPU" python3 -c "
import json, os
try:
    with open('gpu_profiles.json') as f:
        profiles = json.load(f)
    detected = os.getenv('DETECTED_GPU', '').lower()
    match = next((p for p in profiles if p.lower() in detected), '')
    print(match)
except Exception:
    print('')
")
        if [ -n "$GPU_PROFILE" ]; then
          echo "Auto-detected matching profile: $GPU_PROFILE"
        else
          echo "No matching profile found for $DETECTED_GPU"
        fi
      fi
    fi

    if [ -n "$GPU_PROFILE" ] && [ "$GPU_PROFILE" != "null" ] && [ -f "gpu_profiles.json" ]; then
      # Handle Tuning Presets
      # Backward compatibility for ECO_MODE
      if [ -z "$GPU_TUNING" ] && [ "$ECO_MODE" = "true" ]; then
        GPU_TUNING="Efficient"
      fi

      if [ -n "$GPU_TUNING" ]; then
        SUFFIX=""
        case "$GPU_TUNING" in
          Efficient) SUFFIX=" (Eco)" ;;
          Quiet) SUFFIX=" (Quiet)" ;;
          High) SUFFIX="" ;;
        esac

        if [ -n "$SUFFIX" ]; then
          TUNED_PROFILE="${GPU_PROFILE}${SUFFIX}"
          if jq -e ".[\"$TUNED_PROFILE\"]" gpu_profiles.json > /dev/null; then
            echo "Tuning preset '$GPU_TUNING' enabled. Switching to $TUNED_PROFILE"
            GPU_PROFILE="$TUNED_PROFILE"
          else
            echo "Tuning preset '$GPU_TUNING' enabled, but no matching profile found for $TUNED_PROFILE. Using $GPU_PROFILE."
          fi
        fi
      fi

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

  echo "Dropping privileges to 'miner' user..."
  exec gosu miner "$0" "$@"
fi

# -- Below this line runs as non-root (miner) --

# Default to AUTO if GPU_DEVICES is not set
GPU_DEVICES=${GPU_DEVICES:-AUTO}
MULTI_PROCESS=${MULTI_PROCESS:-false}

# GPU Discovery for AUTO mode
if [ "$GPU_DEVICES" = "AUTO" ]; then
  echo "GPU_DEVICES is set to AUTO. Detecting GPUs..."
  if command -v nvidia-smi &> /dev/null; then
    DETECTED_GPU_IDS=$(nvidia-smi --query-gpu=index --format=csv,noheader | xargs | tr ' ' ',')
  elif command -v rocm-smi &> /dev/null; then
    DETECTED_GPU_IDS=$(rocm-smi --showtemp --csv | tail -n +2 | cut -d, -f1 | xargs | tr ' ' ',')
  fi

  if [ -n "$DETECTED_GPU_IDS" ]; then
    echo "Auto-detected GPUs: $DETECTED_GPU_IDS"
    export GPU_DEVICES=$DETECTED_GPU_IDS
  else
    echo "Warning: Could not auto-detect GPUs. Falling back to miner default."
  fi
else
  export GPU_DEVICES
fi

# Start the metrics exporter in the background
./metrics.sh &

# Start the dashboard in the background
streamlit run streamlit_app.py --server.port 5000 --server.address 0.0.0.0 --server.headless true &> "$DATA_DIR/streamlit.log" &

# Start the profit switcher in the background
python3 profit_switcher.py &

# Start report generator in the background
python3 report_generator.py &

# Start CUDA error monitor if enabled
if [ "$AUTO_RESTART_ON_CUDA_ERROR" = "true" ]; then
  ./cuda_monitor.sh &
fi

# Ergo Node Sync Check
if [ "$CHECK_NODE_SYNC" = "true" ]; then
  NODE_URL=${NODE_URL:-http://localhost:9053}
  echo "Ergo Node Sync Check enabled. Checking $NODE_URL..."

  until [ "$(curl -s "${NODE_URL}/info" | jq -r 'if .fullHeight != null and .headersHeight != null and .fullHeight >= .headersHeight then "true" else "false" end')" = "true" ]; do
    FULL_HEIGHT=$(curl -s "${NODE_URL}/info" | jq -r '.fullHeight // "null"')
    HEADERS_HEIGHT=$(curl -s "${NODE_URL}/info" | jq -r '.headersHeight // "null"')
    echo "Waiting for Ergo Node to sync... (Full: $FULL_HEIGHT, Headers: $HEADERS_HEIGHT)"
    sleep 60
  done
  echo "Ergo Node is synced! Proceeding to start miner."
fi

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

# Default to lolminer if MINER is not set
MINER=${MINER:-lolminer}
API_PORT=${API_PORT:-4444}

echo "Starting miner: $MINER (Multi-process: $MULTI_PROCESS)"

# Cleanup function for multi-process mode
cleanup() {
  echo "Shutting down miners..."
  # Kill all background jobs
  JOBS=$(jobs -p)
  if [ -n "$JOBS" ]; then
    kill $JOBS 2>/dev/null
  fi
  # Also pkill by process name as a secondary measure
  case "$MINER" in
    lolminer) pkill -x lolMiner 2>/dev/null ;;
    t-rex) pkill -x t-rex 2>/dev/null ;;
  esac
  exit 0
}

if [ "$MULTI_PROCESS" = "true" ] && [ "$GPU_DEVICES" != "AUTO" ]; then
  trap cleanup SIGTERM SIGINT

  IFS=',' read -ra ADDR <<< "$GPU_DEVICES"
  for i in "${!ADDR[@]}"; do
    GPU_ID="${ADDR[$i]}"
    CURRENT_PORT=$((API_PORT + i))
    echo "Launching miner for GPU $GPU_ID on port $CURRENT_PORT..."

    # Miner-specific configuration for individual GPU
    case "$MINER" in
      lolminer)
        MINER_BIN="/app/lolMiner"
        MINER_CONFIG="--algo AUTOLYKOS2 --pool ${POOL_ADDRESS} --user ${WALLET_ADDRESS}.${WORKER_NAME} --devices ${GPU_ID} --apiport ${CURRENT_PORT} --json-read-only --logfile $DATA_DIR/miner.log"
        [ -n "$BACKUP_POOL_ADDRESS" ] && MINER_CONFIG="$MINER_CONFIG --pool ${BACKUP_POOL_ADDRESS}"
        if [ -n "$DUAL_ALGO" ]; then
          MINER_CONFIG="$MINER_CONFIG --dualmode ${DUAL_ALGO} --dualpool ${DUAL_POOL} --dualuser ${DUAL_WALLET}.${DUAL_WORKER:-$WORKER_NAME}"
        fi
        ;;
      t-rex)
        MINER_BIN="/app/t-rex"
        MINER_CONFIG="-a AUTOLYKOS2 -o ${POOL_ADDRESS} -u ${WALLET_ADDRESS}.${WORKER_NAME} -d ${GPU_ID} --api-bind-http 127.0.0.1:${CURRENT_PORT} --log-path $DATA_DIR/miner.log"
        [ -n "$BACKUP_POOL_ADDRESS" ] && MINER_CONFIG="$MINER_CONFIG -o2 ${BACKUP_POOL_ADDRESS} -u2 ${WALLET_ADDRESS}.${WORKER_NAME}"
        ;;
    esac

    [ -n "$EXTRA_ARGS" ] && MINER_CONFIG="$MINER_CONFIG $EXTRA_ARGS"

    # Start miner in background
    $MINER_BIN $MINER_CONFIG >> "$DATA_DIR/miner.log" 2>&1 &
  done

  # Wait for all background miners
  wait
else
  # Single process mode (original behavior)
  case "$MINER" in
    lolminer)
      MINER_BIN="/app/lolMiner"
      DEVICE_FLAG=""
      [ "$GPU_DEVICES" != "AUTO" ] && DEVICE_FLAG="--devices ${GPU_DEVICES}"
      MINER_CONFIG="--algo AUTOLYKOS2 --pool ${POOL_ADDRESS} --user ${WALLET_ADDRESS}.${WORKER_NAME} ${DEVICE_FLAG} --apiport ${API_PORT} --json-read-only --logfile $DATA_DIR/miner.log"
      [ -n "$BACKUP_POOL_ADDRESS" ] && MINER_CONFIG="$MINER_CONFIG --pool ${BACKUP_POOL_ADDRESS}"
      if [ -n "$DUAL_ALGO" ]; then
        MINER_CONFIG="$MINER_CONFIG --dualmode ${DUAL_ALGO} --dualpool ${DUAL_POOL} --dualuser ${DUAL_WALLET}.${DUAL_WORKER:-$WORKER_NAME}"
      fi
      ;;
    t-rex)
      MINER_BIN="/app/t-rex"
      DEVICE_FLAG=""
      [ "$GPU_DEVICES" != "AUTO" ] && DEVICE_FLAG="-d ${GPU_DEVICES}"
      MINER_CONFIG="-a AUTOLYKOS2 -o ${POOL_ADDRESS} -u ${WALLET_ADDRESS}.${WORKER_NAME} ${DEVICE_FLAG} --api-bind-http 127.0.0.1:${API_PORT} --log-path $DATA_DIR/miner.log"
      [ -n "$BACKUP_POOL_ADDRESS" ] && MINER_CONFIG="$MINER_CONFIG -o2 ${BACKUP_POOL_ADDRESS} -u2 ${WALLET_ADDRESS}.${WORKER_NAME}"
      ;;
    *)
      echo "Unsupported miner: $MINER"
      exit 1
      ;;
  esac

  [ -n "$EXTRA_ARGS" ] && MINER_CONFIG="$MINER_CONFIG $EXTRA_ARGS"

  if [ -n "$TEST_MODE" ]; then
    $MINER_BIN $MINER_CONFIG &
    tail -f /dev/null
  else
    exec $MINER_BIN $MINER_CONFIG
  fi
fi
