#!/bin/bash
# cuda_monitor.sh - Background monitor for CUDA errors in miner logs

DATA_DIR=${DATA_DIR:-/app/data}
LOG_PATTERN=${LOG_PATTERN:-"miner*.log"}
RESTART_SCRIPT=${RESTART_SCRIPT:-"./restart.sh"}
ERROR_PATTERN="out of memory|illegal instruction|CUDA error|GPU fell off the bus|an illegal memory access was encountered"

echo "Starting CUDA error monitor..."

CURRENT_TAIL_PID=""

cleanup() {
  if [ -n "$CURRENT_TAIL_PID" ]; then
    kill "$CURRENT_TAIL_PID" 2>/dev/null
  fi
}
trap cleanup EXIT

while true; do
  # Find all current log files
  LOG_FILES=$(ls $DATA_DIR/$LOG_PATTERN 2>/dev/null | sort)

  if [ -n "$LOG_FILES" ]; then
    echo "Monitoring log files: $(echo $LOG_FILES | tr '\n' ' ')"

    # Start tailing in the background.
    # -F follows by name and handles rotation.
    # -n 0 ensures we only see new lines.
    # -q suppresses headers which makes parsing easier.
    (
      tail -F -n 0 -q $LOG_FILES | while read -r line; do
        if echo "$line" | grep -Ei "$ERROR_PATTERN" > /dev/null; then
          echo "$(date): CRITICAL: CUDA error detected: $line"
          echo "$(date): Triggering auto-restart..."
          # Give it a second to log the error fully
          sleep 1
          $RESTART_SCRIPT
          # The parent will be killed by the container restart
        fi
      done
    ) &
    CURRENT_TAIL_PID=$!

    # Inner loop to check for new files or monitor death
    while true; do
      sleep 10
      # Check if the process is still running
      if ! kill -0 "$CURRENT_TAIL_PID" 2>/dev/null; then
        echo "Monitor process died, restarting..."
        break
      fi

      # Check for new log files
      CHECK_LOG_FILES=$(ls $DATA_DIR/$LOG_PATTERN 2>/dev/null | sort)
      if [ "$LOG_FILES" != "$CHECK_LOG_FILES" ]; then
        echo "Detected new log files, updating monitor..."
        kill "$CURRENT_TAIL_PID" 2>/dev/null
        break
      fi
    done
  else
    # No log files yet, wait and retry
    sleep 2
  fi
done
