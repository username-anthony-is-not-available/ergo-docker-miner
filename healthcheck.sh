#!/bin/bash

# Configuration
MINER=${MINER:-lolminer}
API_PORT=${API_PORT:-4444}
STATE_FILE=${HEALTHCHECK_STATE_FILE:-/tmp/miner_unhealthy_since}
MAX_UNHEALTHY_TIME=300 # 5 minutes in seconds
GPU_DEVICES=${GPU_DEVICES:-AUTO}
MULTI_PROCESS=${MULTI_PROCESS:-false}

# Determine endpoint and process name based on miner
if [ "$MINER" = "lolminer" ]; then
    ENDPOINT="/"
    # lolMiner hashrate is in .Total_Performance[0]
    QUERY_HASHRATE=".Total_Performance[0]"
    QUERY_GPU_COUNT=".GPUs | length"
    QUERY_ACCEPTED=".GPUs | map(.Accepted_Shares // 0) | add"
    QUERY_REJECTED=".GPUs | map(.Rejected_Shares // 0) | add"
    PROCESS_NAME="lolMiner"
elif [ "$MINER" = "t-rex" ]; then
    ENDPOINT="/summary"
    # T-Rex hashrate is in .hashrate
    QUERY_HASHRATE=".hashrate"
    QUERY_GPU_COUNT=".gpus | length"
    QUERY_ACCEPTED=".accepted_count"
    QUERY_REJECTED=".rejected_count"
    PROCESS_NAME="t-rex"
else
    echo "Unsupported miner: $MINER"
    exit 0
fi

# 0. Check Ergo Node Sync if enabled
if [ "$CHECK_NODE_SYNC" = "true" ]; then
    NODE_URL=${NODE_URL:-http://localhost:9053}
    NODE_INFO=$(curl -s "${NODE_URL}/info")
    IS_SYNCED=$(echo "$NODE_INFO" | jq -r 'if .fullHeight != null and .headersHeight != null and .fullHeight >= .headersHeight then "true" else "false" end')

    if [ "$IS_SYNCED" != "true" ]; then
        # If node is out of sync, we check if miner is already running.
        # If it is running, we should restart (so it hits the wait loop in start.sh).
        # If it is NOT running, we are currently waiting, which is healthy.
        if pgrep -x "$PROCESS_NAME" > /dev/null; then
            echo "Node went out of sync while mining! Triggering restart to pause."
            ./restart.sh
            exit 1
        else
            echo "Node is not synced, but miner is not running. Waiting for sync..."
            exit 0
        fi
    fi
fi

# 1. Check if the miner process is running
if [ "$MULTI_PROCESS" = "true" ] && [ "$GPU_DEVICES" != "AUTO" ]; then
    EXPECTED_PROCESS_COUNT=$(echo "$GPU_DEVICES" | tr ',' '\n' | grep -v "^$" | wc -l)
    ACTUAL_PROCESS_COUNT=$(pgrep -x "$PROCESS_NAME" | wc -l)
    if [ "$ACTUAL_PROCESS_COUNT" -lt "$EXPECTED_PROCESS_COUNT" ]; then
        echo "Miner process count mismatch! Expected: $EXPECTED_PROCESS_COUNT, Actual: $ACTUAL_PROCESS_COUNT"
        ./restart.sh
        exit 1
    fi
else
    if ! pgrep -x "$PROCESS_NAME" > /dev/null; then
        echo "Miner process $PROCESS_NAME not found!"
        ./restart.sh
        exit 1
    fi
fi

# 2. Query the miner's API
if [ "$MULTI_PROCESS" = "true" ] && [ "$GPU_DEVICES" != "AUTO" ]; then
    TOTAL_HASHRATE=0
    TOTAL_ACTUAL_GPUS=0
    TOTAL_ACCEPTED=0
    TOTAL_REJECTED=0

    IFS=',' read -ra ADDR <<< "$GPU_DEVICES"
    for i in "${!ADDR[@]}"; do
        CURRENT_PORT=$((API_PORT + i))
        CUR_RESPONSE=$(curl -s "http://localhost:${CURRENT_PORT}${ENDPOINT}")
        CUR_HASHRATE=$(echo "$CUR_RESPONSE" | jq "$QUERY_HASHRATE" 2>/dev/null || echo 0)
        CUR_GPUS=$(echo "$CUR_RESPONSE" | jq "$QUERY_GPU_COUNT" 2>/dev/null || echo 0)
        CUR_ACCEPTED=$(echo "$CUR_RESPONSE" | jq "$QUERY_ACCEPTED" 2>/dev/null || echo 0)
        CUR_REJECTED=$(echo "$CUR_RESPONSE" | jq "$QUERY_REJECTED" 2>/dev/null || echo 0)

        # We use jq to handle potential float hashrates
        TOTAL_HASHRATE=$(jq -n "$TOTAL_HASHRATE + $CUR_HASHRATE")
        TOTAL_ACTUAL_GPUS=$((TOTAL_ACTUAL_GPUS + CUR_GPUS))
        TOTAL_ACCEPTED=$((TOTAL_ACCEPTED + CUR_ACCEPTED))
        TOTAL_REJECTED=$((TOTAL_REJECTED + CUR_REJECTED))
    done

    # Synthesize a response for the subsequent checks
    RESPONSE="{\"hashrate\": $TOTAL_HASHRATE, \"gpu_count\": $TOTAL_ACTUAL_GPUS, \"accepted\": $TOTAL_ACCEPTED, \"rejected\": $TOTAL_REJECTED}"
    QUERY_HASHRATE=".hashrate"
    QUERY_GPU_COUNT=".gpu_count"
    QUERY_ACCEPTED=".accepted"
    QUERY_REJECTED=".rejected"
else
    RESPONSE=$(curl -s "http://localhost:${API_PORT}${ENDPOINT}")
fi

# 3. Check GPU count if GPU_DEVICES is not AUTO
if [ "$GPU_DEVICES" != "AUTO" ]; then
    EXPECTED_GPU_COUNT=$(echo "$GPU_DEVICES" | tr ',' '\n' | grep -v "^$" | wc -l)
    ACTUAL_GPU_COUNT=$(echo "$RESPONSE" | jq "$QUERY_GPU_COUNT" 2>/dev/null || echo 0)

    if [ "$ACTUAL_GPU_COUNT" -lt "$EXPECTED_GPU_COUNT" ]; then
        echo "GPU count mismatch! Expected: $EXPECTED_GPU_COUNT, Actual: $ACTUAL_GPU_COUNT"
        ./restart.sh
        exit 1
    fi
fi

# 4. Check for high rejected share ratio
ACCEPTED_SHARES=$(echo "$RESPONSE" | jq "$QUERY_ACCEPTED" 2>/dev/null || echo 0)
REJECTED_SHARES=$(echo "$RESPONSE" | jq "$QUERY_REJECTED" 2>/dev/null || echo 0)
TOTAL_SHARES=$((ACCEPTED_SHARES + REJECTED_SHARES))

if [ "$TOTAL_SHARES" -ge 20 ]; then
    # Calculate ratio as percentage. Using bash arithmetic for simplicity.
    # We multiply by 100 first to avoid floating point issues.
    REJECT_RATIO=$(( (REJECTED_SHARES * 100) / TOTAL_SHARES ))
    if [ "$REJECT_RATIO" -gt 10 ]; then
        echo "High rejected share ratio detected! Rejected: $REJECTED_SHARES, Total: $TOTAL_SHARES ($REJECT_RATIO%)"
        ./restart.sh
        exit 1
    fi
fi

# 5. Check if hashrate is > 0
# We use jq to handle potential float values and ensure robust parsing.
if echo "$RESPONSE" | jq -e "$QUERY_HASHRATE > 0" >/dev/null 2>&1; then
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
        ./restart.sh
        exit 1
    else
        echo "Miner has been unhealthy for $ELAPSED seconds. (Grace period: $MAX_UNHEALTHY_TIME)"
        exit 0
    fi
fi
