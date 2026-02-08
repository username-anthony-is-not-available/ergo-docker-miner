#!/bin/bash

# Configuration
METRICS_PORT=${METRICS_PORT:-4455}
METRICS_URL="http://localhost:${METRICS_PORT}/metrics"
STATE_FILE=${HEALTHCHECK_STATE_FILE:-/tmp/miner_unhealthy_since}
MAX_UNHEALTHY_TIME=300 # 5 minutes in seconds
GPU_DEVICES=${GPU_DEVICES:-AUTO}

# 1. Query the metrics server
METRICS=$(curl -s --fail "$METRICS_URL")
if [ $? -ne 0 ]; then
    echo "Metrics server at $METRICS_URL is unreachable!"
    # During startup or if metrics service crashed, we don't want to immediately
    # restart the whole container. Docker will retry the healthcheck.
    exit 0
fi

# Helper to extract metric values
get_metric() {
    local name=$1
    # Extracts the first value for the given metric name, ignoring labels
    echo "$METRICS" | grep "^${name}{" | head -n 1 | sed -n 's/.*} //p'
}

# Extracts a label value from a metric
get_label() {
    local name=$1
    local label=$2
    echo "$METRICS" | grep "^${name}{" | head -n 1 | sed -n "s/.*${label}=\"\([^\"]*\)\".*/\1/p"
}

# 2. Extract standardized metrics
HASHRATE=$(get_metric "miner_hashrate")
API_UP=$(get_metric "miner_api_up")
GPU_COUNT=$(get_metric "miner_gpu_count")
ACCEPTED_SHARES=$(get_metric "miner_total_shares_accepted")
REJECTED_SHARES=$(get_metric "miner_total_shares_rejected")
NODE_SYNCED=$(get_metric "miner_node_synced")
MINER_TYPE=$(get_label "miner_info" "miner")

# Determine process name for checks
if [ "$MINER_TYPE" = "lolminer" ]; then
    PROCESS_NAME="lolMiner"
elif [ "$MINER_TYPE" = "t-rex" ]; then
    PROCESS_NAME="t-rex"
else
    PROCESS_NAME=""
fi

# 3. Check Ergo Node Sync
if [ -n "$NODE_SYNCED" ] && [ "$(awk -v ns="$NODE_SYNCED" 'BEGIN {if (ns == 0) print "1"; else print "0"}')" = "1" ]; then
    if [ -n "$PROCESS_NAME" ] && pgrep -x "$PROCESS_NAME" > /dev/null; then
        echo "Node went out of sync while mining! Triggering restart to pause."
        ./restart.sh
        exit 1
    else
        echo "Node is not synced, but miner is not running. Waiting for sync..."
        exit 0
    fi
fi

# 4. Check GPU count if GPU_DEVICES is not AUTO
if [ "$GPU_DEVICES" != "AUTO" ] && [ -n "$GPU_COUNT" ]; then
    EXPECTED_GPU_COUNT=$(echo "$GPU_DEVICES" | tr ',' '\n' | grep -v "^$" | wc -l)

    # Use awk for robust numeric comparison
    IS_COUNT_OK=$(awk -v act="$GPU_COUNT" -v expected="$EXPECTED_GPU_COUNT" 'BEGIN {if (act >= expected) print "1"; else print "0"}')

    if [ "$IS_COUNT_OK" = "0" ]; then
        echo "GPU count mismatch! Expected: $EXPECTED_GPU_COUNT, Actual: $GPU_COUNT"
        ./restart.sh
        exit 1
    fi
fi

# 5. Check for high rejected share ratio
if [ -n "$ACCEPTED_SHARES" ] && [ -n "$REJECTED_SHARES" ]; then
    TOTAL_SHARES=$(awk -v acc="$ACCEPTED_SHARES" -v rej="$REJECTED_SHARES" 'BEGIN {print acc + rej}')

    # Only check if we have enough shares to be statistically significant (>= 20 shares)
    if [ "$(awk -v ts="$TOTAL_SHARES" 'BEGIN {if (ts >= 20) print "1"; else print "0"}')" = "1" ]; then
        REJECT_RATIO=$(awk -v rej="$REJECTED_SHARES" -v ts="$TOTAL_SHARES" 'BEGIN {print (rej * 100) / ts}')
        if [ "$(awk -v rr="$REJECT_RATIO" 'BEGIN {if (rr > 10) print "1"; else print "0"}')" = "1" ]; then
            echo "CRITICAL: High rejected share ratio detected!"
            echo "  Accepted: $ACCEPTED_SHARES"
            echo "  Rejected: $REJECTED_SHARES"
            echo "  Total: $TOTAL_SHARES"
            echo "  Ratio: $REJECT_RATIO% (Threshold: 10%)"
            echo "Triggering automated restart..."
            ./restart.sh
            exit 1
        else
            echo "Health check: Share ratio healthy ($REJECT_RATIO% rejected)."
        fi
    fi
fi

# 6. Check if hashrate is > 0
if [ -n "$HASHRATE" ] && [ "$(awk -v hr="$HASHRATE" 'BEGIN {if (hr > 0) print "1"; else print "0"}')" = "1" ]; then
    # Miner is producing hashrate
    if [ -f "$STATE_FILE" ]; then
        echo "Miner recovered. Clearing unhealthy state."
        rm -f "$STATE_FILE"
    fi
    exit 0
else
    # Miner is NOT producing hashrate (or metrics empty)
    CURRENT_TIME=$(date +%s)

    if [ ! -f "$STATE_FILE" ]; then
        echo "Miner unhealthy (hashrate 0 or API unreachable). Starting grace period."
        echo "$CURRENT_TIME" > "$STATE_FILE"
        exit 0
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
