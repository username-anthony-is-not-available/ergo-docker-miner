#!/bin/bash

# Configuration
MINER=${MINER:-lolminer}
API_PORT=4444
STATE_FILE=${HEALTHCHECK_STATE_FILE:-/tmp/miner_unhealthy_since}
MAX_UNHEALTHY_TIME=300 # 5 minutes in seconds

# Helper to trigger restart
trigger_restart() {
    if [ "$TEST_MODE" = "1" ]; then
        echo "TEST_MODE is enabled. Skipping restart."
        return
    fi
    if [ -f "./restart.sh" ]; then
        ./restart.sh
    else
        echo "Error: restart.sh not found."
    fi
}

# Determine endpoint and process name based on miner
if [ "$MINER" = "lolminer" ]; then
    ENDPOINT="/"
    # lolMiner hashrate is in .Total_Performance[0]
    QUERY=".Total_Performance[0]"
    PROCESS_NAME="lolMiner"
elif [ "$MINER" = "t-rex" ]; then
    ENDPOINT="/summary"
    # T-Rex hashrate is in .hashrate
    QUERY=".hashrate"
    PROCESS_NAME="t-rex"
else
    echo "Unsupported miner: $MINER"
    exit 0
fi

# 1. Check if the miner process is running
if ! pgrep -x "$PROCESS_NAME" > /dev/null; then
    echo "Miner process $PROCESS_NAME not found!"
    trigger_restart
    exit 1
fi

# 2. Query the miner's API
RESPONSE=$(curl -s "http://localhost:${API_PORT}${ENDPOINT}")

# 3. Check if hashrate is > 0
# We use jq to handle potential float values and ensure robust parsing.
# If curl fails or RESPONSE is empty, jq will return false or error.
# We use -e to set exit code based on the result of the expression.
if echo "$RESPONSE" | jq -e "$QUERY > 0" >/dev/null 2>&1; then
    # Miner is producing hashrate
    if [ -f "$STATE_FILE" ]; then
        echo "Miner recovered. Clearing unhealthy state."
        rm -f "$STATE_FILE"
    fi
    exit 0
else
    # Miner is NOT producing hashrate (or API is down)
    CURRENT_TIME=$(date +%s)

    if [ ! -f "$STATE_FILE" ]; then
        echo "Miner unhealthy (hashrate 0 or API unreachable). Starting grace period."
        echo "$CURRENT_TIME" > "$STATE_FILE"
        exit 0 # Still returning 0 during grace period
    fi

    START_TIME=$(cat "$STATE_FILE")
    ELAPSED=$((CURRENT_TIME - START_TIME))

    if [ "$ELAPSED" -ge "$MAX_UNHEALTHY_TIME" ]; then
        echo "Miner has been unhealthy for $ELAPSED seconds (exceeds $MAX_UNHEALTHY_TIME). Restarting..."
        rm -f "$STATE_FILE"
        trigger_restart
        exit 1
    else
        echo "Miner has been unhealthy for $ELAPSED seconds. (Grace period: $MAX_UNHEALTHY_TIME)"
        exit 0
    fi
fi
