#!/bin/bash

# tests/test_healthcheck.sh

# Cleanup previous state
export HEALTHCHECK_STATE_FILE="/tmp/test_miner_unhealthy_since"
rm -f "$HEALTHCHECK_STATE_FILE"
rm -f /tmp/mock_api_response /tmp/mock_process_running /tmp/restart_called /tmp/test_output

# Mocking restart.sh
if [ -f "restart.sh" ]; then
    mv restart.sh restart.sh.bak
fi

cat > restart.sh <<EOF
#!/bin/bash
echo "RESTART_CALLED" > /tmp/restart_called
EOF
chmod +x restart.sh

# Mock pgrep and curl
MOCK_BIN_DIR=$(mktemp -d)
export PATH="$MOCK_BIN_DIR:$PATH"

cat > "$MOCK_BIN_DIR/curl" <<EOF
#!/bin/bash
if [ -f /tmp/curl_fail ]; then
    exit 1
fi
cat /tmp/mock_api_response
EOF
chmod +x "$MOCK_BIN_DIR/curl"

cat > "$MOCK_BIN_DIR/pgrep" <<EOF
#!/bin/bash
if [ -f /tmp/mock_process_running ]; then
    echo "1234" # Dummy PID
    exit 0
else
    exit 1
fi
EOF
chmod +x "$MOCK_BIN_DIR/pgrep"

function run_test() {
    local name=$1
    local expected_exit=$2
    local expected_restart=$3

    echo -n "Running test: $name... "
    rm -f /tmp/restart_called
    ./healthcheck.sh > /tmp/test_output 2>&1
    local actual_exit=$?

    if [ "$actual_exit" -ne "$expected_exit" ]; then
        echo "FAILED: Expected exit $expected_exit, got $actual_exit"
        cat /tmp/test_output
        cleanup
        exit 1
    fi

    if [ "$expected_restart" = "yes" ]; then
        if [ ! -f /tmp/restart_called ]; then
            echo "FAILED: Expected restart.sh to be called, but it wasn't"
            cleanup
            exit 1
        fi
    else
        if [ -f /tmp/restart_called ]; then
            echo "FAILED: Did not expect restart.sh to be called, but it was"
            cleanup
            exit 1
        fi
    fi
    echo "PASSED"
}

function cleanup() {
    rm -rf "$MOCK_BIN_DIR"
    rm -f restart.sh
    if [ -f "restart.sh.bak" ]; then
        mv restart.sh.bak restart.sh
    fi
    rm -f /tmp/mock_api_response /tmp/mock_process_running /tmp/restart_called /tmp/test_output "$HEALTHCHECK_STATE_FILE" /tmp/curl_fail
}

function mock_metrics() {
    local hashrate=$1
    local api_up=${2:-1.0}
    local gpu_count=${3:-2.0}
    local accepted=${4:-100.0}
    local rejected=${5:-0.0}
    local miner=${6:-lolminer}
    local node_synced=${7:-1.0}

    cat > /tmp/mock_api_response <<EOF
miner_hashrate{worker="test"} $hashrate
miner_api_up{worker="test"} $api_up
miner_gpu_count{worker="test"} $gpu_count
miner_total_shares_accepted{worker="test"} $accepted
miner_total_shares_rejected{worker="test"} $rejected
miner_node_synced{worker="test"} $node_synced
miner_info{miner="$miner",version="1.0",worker="test"} 1.0
EOF
}

# --- Test Cases ---

# 1. Healthy lolminer
export GPU_DEVICES=AUTO
touch /tmp/mock_process_running
mock_metrics 100.5 1.0 2.0 100 0 lolminer 1.0
run_test "Healthy lolminer" 0 "no"

# 2. Healthy t-rex
mock_metrics 50.0 1.0 2.0 100 0 t-rex 1.0
run_test "Healthy t-rex" 0 "no"

# 3. 0 hashrate (Grace period starts)
mock_metrics 0 1.0 2.0 100 0 lolminer 1.0
run_test "0 hashrate (start grace)" 0 "no"
if [ ! -f "$HEALTHCHECK_STATE_FILE" ]; then
    echo "FAILED: State file not created"
    cleanup
    exit 1
fi

# 4. 0 hashrate (Within grace period)
echo $(($(date +%s) - 120)) > "$HEALTHCHECK_STATE_FILE"
run_test "0 hashrate (within grace)" 0 "no"

# 5. 0 hashrate (After grace period)
echo $(($(date +%s) - 360)) > "$HEALTHCHECK_STATE_FILE"
run_test "0 hashrate (after grace)" 1 "yes"

# 6. Recovery during grace period
echo $(($(date +%s) - 120)) > "$HEALTHCHECK_STATE_FILE"
mock_metrics 100.5 1.0 2.0 100 0 lolminer 1.0
run_test "Recovery during grace period" 0 "no"
if [ -f "$HEALTHCHECK_STATE_FILE" ]; then
    echo "FAILED: State file not removed after recovery"
    cleanup
    exit 1
fi

# 7. GPU count mismatch
export GPU_DEVICES="0,1"
mock_metrics 100.5 1.0 1.0 100 0 lolminer 1.0 # Only 1 GPU reported
run_test "GPU count mismatch" 1 "yes"

# 8. GPU count match
export GPU_DEVICES="0,1"
mock_metrics 100.5 1.0 2.0 100 0 lolminer 1.0
run_test "GPU count match" 0 "no"

# 9. High rejected share ratio
export GPU_DEVICES=AUTO
# 10 accepted, 11 rejected = 21 total, > 50% reject ratio
mock_metrics 100.5 1.0 2.0 10 11 lolminer 1.0
run_test "High rejected share ratio" 1 "yes"

# 10. Normal rejected share ratio
# 20 accepted, 1 rejected = 21 total, ~4.7% reject ratio
mock_metrics 100.5 1.0 2.0 20 1 lolminer 1.0
run_test "Normal rejected share ratio" 0 "no"

# 11. Node out of sync while mining
mock_metrics 100.5 1.0 2.0 100 0 lolminer 0.0 # Node not synced
touch /tmp/mock_process_running # Miner is running
run_test "Node out of sync while mining" 1 "yes"

# 12. Node out of sync but miner not running (Waiting)
mock_metrics 100.5 1.0 2.0 100 0 lolminer 0.0 # Node not synced
rm /tmp/mock_process_running # Miner NOT running
run_test "Node out of sync while waiting" 0 "no"

# 13. Metrics server unreachable
touch /tmp/curl_fail
run_test "Metrics server unreachable" 0 "no"

cleanup
echo "All healthcheck tests passed!"
