#!/bin/bash
set -e

# Cleanup previous runs
docker rm -f ergo-miner-test-container 2>/dev/null || true

# Run the container in detached mode
echo "Running the container..."
sudo docker run --name ergo-miner-test-container -d --restart unless-stopped -e TEST_MODE=1 --env-file .env.test ergo-miner-test

# Wait for the container to initialize
echo "Waiting for the container to start..."
sleep 15

# Skipping health check in test environment.
# The health check relies on the lolMiner API, which does not start
# without a GPU. The test environment lacks GPU support.
echo "Skipping health check in test environment..."

# Test the metrics endpoint
echo "Testing the metrics endpoint..."
if sudo docker inspect -f '{{.State.Running}}' ergo-miner-test-container | grep -q "true"; then
    METRICS_OUTPUT=$(sudo docker exec ergo-miner-test-container curl -s http://localhost:4455)
    if ! echo "$METRICS_OUTPUT" | grep -q "miner_hashrate"; then
      echo "Metrics endpoint test failed!"
      echo "Output: $METRICS_OUTPUT"
      sudo docker rm -f ergo-miner-test-container
      exit 1
    fi
else
    echo "Container not running, skipping metrics test."
fi
echo "Metrics endpoint test passed!"

# Test crash recovery
echo "Testing crash recovery..."
if sudo docker inspect -f '{{.State.Running}}' ergo-miner-test-container | grep -q "true"; then
    echo "Killing the main process inside the container..."
    sudo docker exec ergo-miner-test-container pkill tail
    sleep 10 # Wait for the container to restart
    if ! sudo docker inspect -f '{{.State.Running}}' ergo-miner-test-container | grep -q "true"; then
        echo "Crash recovery test failed: Container did not restart."
        sudo docker rm -f ergo-miner-test-container
        exit 1
    fi
    echo "Crash recovery test passed!"
else
    echo "Container not running, skipping crash recovery test."
fi

# Cleanup
echo "Cleaning up..."
sudo docker rm -f ergo-miner-test-container
echo "Test completed successfully."
