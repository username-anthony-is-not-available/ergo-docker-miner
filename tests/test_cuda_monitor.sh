#!/bin/bash
# tests/test_cuda_monitor.sh

# Setup
TEST_LOG="test_miner.log"
MONITOR_SCRIPT="./cuda_monitor.sh"

echo "Setting up CUDA monitor test..."

# Mock restart.sh to avoid killing PID 1 during test
cat <<EOF > mock_restart.sh
#!/bin/bash
echo "RESTART_TRIGGERED" > restart_triggered.txt
EOF
chmod +x mock_restart.sh

# Start with a fresh log file
rm -f "$TEST_LOG"
touch "$TEST_LOG"

# Run monitor in background using environment variables for mocking
DATA_DIR="." LOG_PATTERN="$TEST_LOG" RESTART_SCRIPT="./mock_restart.sh" "$MONITOR_SCRIPT" &
MONITOR_PID=$!

echo "Monitor started with PID $MONITOR_PID. Waiting for initialization..."
sleep 2

# Test Case 1: Normal lines should NOT trigger restart
echo "Normal: Miner started" >> "$TEST_LOG"
echo "Normal: GPU 0: 45 MH/s" >> "$TEST_LOG"
sleep 1

if [ -f restart_triggered.txt ]; then
    echo "FAILURE: Restart triggered on normal log lines!"
    kill $MONITOR_PID 2>/dev/null || true
    rm -f "$TEST_LOG" mock_restart.sh restart_triggered.txt test_cuda_monitor.sh
    exit 1
fi

# Test Case 2: CUDA error should trigger restart
echo "Testing 'out of memory' detection..."
echo "Error: CUDA error: out of memory" >> "$TEST_LOG"

# Wait for monitor to react
sleep 3

if [ -f restart_triggered.txt ] && [ "$(cat restart_triggered.txt)" = "RESTART_TRIGGERED" ]; then
    echo "SUCCESS: 'out of memory' detected and restart triggered!"
else
    echo "FAILURE: 'out of memory' not detected."
    kill $MONITOR_PID 2>/dev/null || true
    rm -f "$TEST_LOG" mock_restart.sh restart_triggered.txt test_cuda_monitor.sh
    exit 1
fi

# Reset trigger file for next case
rm -f restart_triggered.txt

# Test Case 3: Illegal instruction detection
# We need to restart the monitor because it exits after first detection
DATA_DIR="." LOG_PATTERN="$TEST_LOG" RESTART_SCRIPT="./mock_restart.sh" "$MONITOR_SCRIPT" &
MONITOR_PID=$!
sleep 2

echo "Testing 'illegal instruction' detection..."
echo "CRITICAL: illegal instruction encountered" >> "$TEST_LOG"
sleep 3

if [ -f restart_triggered.txt ] && [ "$(cat restart_triggered.txt)" = "RESTART_TRIGGERED" ]; then
    echo "SUCCESS: 'illegal instruction' detected and restart triggered!"
else
    echo "FAILURE: 'illegal instruction' not detected."
    kill $MONITOR_PID 2>/dev/null || true
    rm -f "$TEST_LOG" mock_restart.sh restart_triggered.txt
    exit 1
fi

# Reset trigger file for next case
rm -f restart_triggered.txt

# Test Case 4: Detection in a newly created log file
DATA_DIR="." LOG_PATTERN="miner*.log" RESTART_SCRIPT="./mock_restart.sh" "$MONITOR_SCRIPT" &
MONITOR_PID=$!
sleep 2

echo "Testing detection in a newly created log file..."
NEW_LOG="miner_gpu1.log"
rm -f "$NEW_LOG"
echo "Normal: Startup" > "$NEW_LOG"
sleep 12 # Wait for monitor to detect new file (it checks every 10s)

echo "Error: CUDA error: GPU fell off the bus" >> "$NEW_LOG"
sleep 3

if [ -f restart_triggered.txt ] && [ "$(cat restart_triggered.txt)" = "RESTART_TRIGGERED" ]; then
    echo "SUCCESS: Detection in new log file successful!"
else
    echo "FAILURE: Detection in new log file failed."
    kill $MONITOR_PID 2>/dev/null || true
    rm -f "$TEST_LOG" "$NEW_LOG" mock_restart.sh restart_triggered.txt
    exit 1
fi

# Cleanup
kill $MONITOR_PID 2>/dev/null || true
rm -f "$TEST_LOG" "$NEW_LOG" mock_restart.sh restart_triggered.txt
echo "All CUDA monitor tests passed!"
exit 0
