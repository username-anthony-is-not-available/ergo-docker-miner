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

# Create a test version of the monitor script with mocked components
# We use sed to replace the log file and the restart script call
sed -e "s|LOG_FILE=\"miner.log\"|LOG_FILE=\"$TEST_LOG\"|" \
    -e "s|./restart.sh|./mock_restart.sh|" \
    "$MONITOR_SCRIPT" > test_cuda_monitor.sh
chmod +x test_cuda_monitor.sh

# Start with a fresh log file
rm -f "$TEST_LOG"
touch "$TEST_LOG"

# Run monitor in background
./test_cuda_monitor.sh &
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
./test_cuda_monitor.sh &
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
    rm -f "$TEST_LOG" mock_restart.sh restart_triggered.txt test_cuda_monitor.sh
    exit 1
fi

# Cleanup
kill $MONITOR_PID 2>/dev/null || true
rm -f "$TEST_LOG" mock_restart.sh restart_triggered.txt test_cuda_monitor.sh
echo "All CUDA monitor tests passed!"
exit 0
