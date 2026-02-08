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
cat /tmp/mock_api_response
EOF
chmod +x "$MOCK_BIN_DIR/curl"

cat > "$MOCK_BIN_DIR/pgrep" <<EOF
#!/bin/bash
if [ -f /tmp/mock_process_running ]; then
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
    rm -f /tmp/mock_api_response /tmp/mock_process_running /tmp/restart_called /tmp/test_output "$HEALTHCHECK_STATE_FILE"
}

# --- Test Cases ---

# 1. Healthy lolminer
export MINER=lolminer
export GPU_DEVICES=AUTO
touch /tmp/mock_process_running
echo '{"Total_Performance": [100.5], "GPUs": [{}, {}]}' > /tmp/mock_api_response
run_test "Healthy lolminer" 0 "no"

# 2. Healthy t-rex
export MINER=t-rex
echo '{"hashrate": 50000000, "gpus": [{}, {}]}' > /tmp/mock_api_response
run_test "Healthy t-rex" 0 "no"

# 3. lolminer 0 hashrate (Grace period starts)
export MINER=lolminer
echo '{"Total_Performance": [0], "GPUs": [{}, {}]}' > /tmp/mock_api_response
run_test "lolminer 0 hashrate (start grace)" 0 "no"
if [ ! -f "$HEALTHCHECK_STATE_FILE" ]; then
    echo "FAILED: State file not created"
    cleanup
    exit 1
fi

# 4. lolminer 0 hashrate (Within grace period)
echo $(($(date +%s) - 120)) > "$HEALTHCHECK_STATE_FILE"
run_test "lolminer 0 hashrate (within grace)" 0 "no"

# 5. lolminer 0 hashrate (After grace period)
echo $(($(date +%s) - 360)) > "$HEALTHCHECK_STATE_FILE"
run_test "lolminer 0 hashrate (after grace)" 1 "yes"

# 6. Recovery during grace period
echo $(($(date +%s) - 120)) > "$HEALTHCHECK_STATE_FILE"
echo '{"Total_Performance": [100.5], "GPUs": [{}, {}]}' > /tmp/mock_api_response
run_test "Recovery during grace period" 0 "no"
if [ -f "$HEALTHCHECK_STATE_FILE" ]; then
    echo "FAILED: State file not removed after recovery"
    cleanup
    exit 1
fi

# 7. Process not running (immediate failure)
rm /tmp/mock_process_running
run_test "Process not running" 1 "yes"
touch /tmp/mock_process_running

# 8. GPU count mismatch (lolminer)
export MINER=lolminer
export GPU_DEVICES="0,1"
echo '{"Total_Performance": [100.5], "GPUs": [{}]}' > /tmp/mock_api_response
run_test "GPU count mismatch (lolminer)" 1 "yes"

# 9. GPU count match (lolminer)
export GPU_DEVICES="0,1"
echo '{"Total_Performance": [100.5], "GPUs": [{}, {}]}' > /tmp/mock_api_response
run_test "GPU count match (lolminer)" 0 "no"

# 10. GPU count mismatch (t-rex)
export MINER=t-rex
export GPU_DEVICES="0,1,2"
echo '{"hashrate": 50000000, "gpus": [{}, {}]}' > /tmp/mock_api_response
run_test "GPU count mismatch (t-rex)" 1 "yes"

# 11. Multi-process healthy
export MULTI_PROCESS=true
export GPU_DEVICES="0,1"
export MINER=lolminer
# We need to mock pgrep to return multiple lines for MULTI_PROCESS check
cat > "$MOCK_BIN_DIR/pgrep" <<EOF
#!/bin/bash
if [ -f /tmp/mock_process_running ]; then
    echo "123"
    echo "456"
    exit 0
else
    exit 1
fi
EOF
chmod +x "$MOCK_BIN_DIR/pgrep"
echo '{"Total_Performance": [50.0], "GPUs": [{}]}' > /tmp/mock_api_response
run_test "Multi-process healthy" 0 "no"

# 12. Multi-process process count mismatch
cat > "$MOCK_BIN_DIR/pgrep" <<EOF
#!/bin/bash
if [ -f /tmp/mock_process_running ]; then
    echo "123"
    exit 0
else
    exit 1
fi
EOF
chmod +x "$MOCK_BIN_DIR/pgrep"
run_test "Multi-process process count mismatch" 1 "yes"

# 13. High rejected share ratio (lolminer)
export MULTI_PROCESS=false
export GPU_DEVICES=AUTO
export MINER=lolminer
cat > "$MOCK_BIN_DIR/pgrep" <<EOF
#!/bin/bash
if [ -f /tmp/mock_process_running ]; then
    echo "123"
    exit 0
else
    exit 1
fi
EOF
chmod +x "$MOCK_BIN_DIR/pgrep"
# 10 accepted, 11 rejected = 21 total, > 50% reject ratio
echo '{"Total_Performance": [100.5], "GPUs": [{"Accepted_Shares": 10, "Rejected_Shares": 11}]}' > /tmp/mock_api_response
run_test "High rejected share ratio (lolminer)" 1 "yes"

# 14. Normal rejected share ratio (lolminer)
# 20 accepted, 1 rejected = 21 total, ~4.7% reject ratio
echo '{"Total_Performance": [100.5], "GPUs": [{"Accepted_Shares": 20, "Rejected_Shares": 1}]}' > /tmp/mock_api_response
run_test "Normal rejected share ratio (lolminer)" 0 "no"

cleanup
echo "All healthcheck tests passed!"
