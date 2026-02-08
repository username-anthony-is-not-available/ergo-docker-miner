#!/bin/bash
set -e

# Create a temporary directory for the test
TEST_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_DIR"' EXIT

echo "Using test directory: $TEST_DIR"

# Create a dummy log file
LOG_FILE="$TEST_DIR/test.log"
echo "Dummy log content" > "$LOG_FILE"
# Make it larger than 10M
truncate -s 11M "$LOG_FILE"

# Create a dummy csv file
CSV_FILE="$TEST_DIR/test.csv"
echo "col1,col2" > "$CSV_FILE"
truncate -s 11M "$CSV_FILE"

# Create a custom logrotate config for the test
CAT_CONFIG="$TEST_DIR/logrotate.conf"
cat <<EOF > "$CAT_CONFIG"
$TEST_DIR/*.log $TEST_DIR/*.csv {
    size 10M
    rotate 3
    copytruncate
    missingok
    notifempty
    nocompress
}
EOF

# Run logrotate
# Note: logrotate might complain about permissions if the config is not owned by root,
# but usually it's fine when running as the same user.
/usr/sbin/logrotate -s "$TEST_DIR/status" "$CAT_CONFIG" --force

# Verify rotation
if [ -f "$LOG_FILE.1" ]; then
    echo "Log file was successfully rotated to $LOG_FILE.1"
else
    echo "FAILED: Log file was not rotated"
    ls -l "$TEST_DIR"
    exit 1
fi

if [ -f "$CSV_FILE.1" ]; then
    echo "CSV file was successfully rotated to $CSV_FILE.1"
else
    echo "FAILED: CSV file was not rotated"
    ls -l "$TEST_DIR"
    exit 1
fi

# Check original files are truncated
LOG_SIZE=$(stat -c%s "$LOG_FILE")
if [ "$LOG_SIZE" -eq 0 ]; then
    echo "Original log file was successfully truncated"
else
    echo "FAILED: Original log file was not truncated (size: $LOG_SIZE)"
    exit 1
fi

echo "Log rotation test passed!"
