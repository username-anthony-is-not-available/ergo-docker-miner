#!/bin/bash

# tests/test_healthcheck_e2e.sh
# E2E test for healthcheck.sh using real metrics.py and mock_miner_api.py

export HEALTHCHECK_STATE_FILE="/tmp/test_miner_unhealthy_since_e2e"
export METRICS_PORT=4456
export API_PORT=4445
export GPU_MOCK=false
export MINER=lolminer
export MOCK_STATE_FILE="/tmp/mock_miner_state.json"
export WORKER_NAME="e2e-test-worker"

# Mock pgrep to always return success for the miner process
MOCK_BIN_DIR=$(mktemp -d)
export PATH="$MOCK_BIN_DIR:$PATH"

cat > "$MOCK_BIN_DIR/pgrep" <<EOF
#!/bin/bash
if [ "\$1" = "-x" ] && ([ "\$2" = "lolMiner" ] || [ "\$2" = "t-rex" ]); then
    echo "1234"
    exit 0
fi
# Call real pgrep for other things if needed
/usr/bin/pgrep "\$@"
EOF
chmod +x "$MOCK_BIN_DIR/pgrep"

rm -f "$HEALTHCHECK_STATE_FILE"
rm -f /tmp/restart_called_e2e
rm -f "$MOCK_STATE_FILE"

# Mock restart.sh
if [ -f "restart.sh" ]; then
    mv restart.sh restart.sh.bak
fi

cat > restart.sh <<EOF
#!/bin/bash
echo "RESTART_CALLED" > /tmp/restart_called_e2e
EOF
chmod +x restart.sh

# Start Mock Miner API
python3 tests/mock_miner_api.py $API_PORT > /tmp/mock_miner.log 2>&1 &
MOCK_MINER_PID=$!

# Give mock miner a moment to start
sleep 2

function cleanup() {
    echo "Cleaning up..."
    kill $MOCK_MINER_PID 2>/dev/null
    # Kill any metrics.py that might be running
    pkill -f "python3 metrics.py" 2>/dev/null

    rm -f restart.sh
    if [ -f "restart.sh.bak" ]; then
        mv restart.sh.bak restart.sh
    fi
    rm -rf "$MOCK_BIN_DIR"
    rm -f "$HEALTHCHECK_STATE_FILE" /tmp/restart_called_e2e /tmp/mock_miner.log /tmp/metrics_e2e.log "$MOCK_STATE_FILE" /tmp/test_output_e2e
}

trap cleanup EXIT

function set_mock_state() {
    local hashrate=$1
    local accepted=$2
    local rejected=$3
    local uptime=${4:-3600}

    cat > "$MOCK_STATE_FILE" <<EOF
{
    "hashrate": $hashrate,
    "accepted": $accepted,
    "rejected": $rejected,
    "uptime": $uptime
}
EOF
}

function run_test() {
    local name=$1
    local expected_exit=$2
    local expected_restart=$3

    echo -n "Running E2E test: $name... "

    # Start metrics.py for this test case
    # We start it fresh so it picks up the current mock state immediately
    PYTHONPATH=. python3 metrics.py > /tmp/metrics_e2e.log 2>&1 &
    METRICS_PID=$!

    # Wait for metrics.py to be ready
    local timeout=10
    while [ $timeout -gt 0 ]; do
        if curl -s "http://localhost:$METRICS_PORT/metrics" | grep -q "miner_hashrate"; then
            break
        fi
        sleep 1
        timeout=$((timeout - 1))
    done

    if [ $timeout -eq 0 ]; then
        echo "FAILED: metrics.py failed to start or serve metrics"
        cat /tmp/metrics_e2e.log
        exit 1
    fi

    rm -f /tmp/restart_called_e2e
    ./healthcheck.sh > /tmp/test_output_e2e 2>&1
    local actual_exit=$?

    # Stop metrics.py
    kill $METRICS_PID 2>/dev/null
    wait $METRICS_PID 2>/dev/null

    if [ "$actual_exit" -ne "$expected_exit" ]; then
        echo "FAILED: Expected exit $expected_exit, got $actual_exit"
        cat /tmp/test_output_e2e
        exit 1
    fi

    if [ "$expected_restart" = "yes" ]; then
        if [ ! -f /tmp/restart_called_e2e ]; then
            echo "FAILED: Expected restart.sh to be called, but it wasn't"
            exit 1
        fi
    else
        if [ -f /tmp/restart_called_e2e ]; then
            echo "FAILED: Did not expect restart.sh to be called, but it was"
            exit 1
        fi
    fi
    echo "PASSED"
}

# --- Test Cases ---

# 1. Healthy state
set_mock_state 100.0 100 0
run_test "Healthy" 0 "no"

# 2. High rejected shares (10 accepted, 11 rejected = >10% ratio)
set_mock_state 100.0 10 11
run_test "High rejected shares" 1 "yes"

# 3. Zero hashrate (Grace period starts)
rm -f "$HEALTHCHECK_STATE_FILE"
set_mock_state 0.0 100 0
run_test "Zero hashrate (start grace)" 0 "no"
if [ ! -f "$HEALTHCHECK_STATE_FILE" ]; then
    echo "FAILED: State file not created for grace period"
    exit 1
fi

# 4. Zero hashrate (Within grace period)
# Manually set state file to 2 minutes ago
echo $(($(date +%s) - 120)) > "$HEALTHCHECK_STATE_FILE"
set_mock_state 0.0 100 0
run_test "Zero hashrate (within grace)" 0 "no"

# 5. Zero hashrate (After grace period)
# Manually set state file to 6 minutes ago
echo $(($(date +%s) - 360)) > "$HEALTHCHECK_STATE_FILE"
set_mock_state 0.0 100 0
run_test "Zero hashrate (after grace)" 1 "yes"

echo "All E2E healthcheck tests passed!"
