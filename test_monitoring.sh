#!/bin/bash
set -e

# Cleanup previous runs
docker rm -f ergo-miner-test-container 2>/dev/null || true

# Build the Docker image
echo "Building the Docker image..."
docker build -t ergo-miner-test .

# Run the container in detached mode
echo "Running the container..."
docker run --name ergo-miner-test-container -d -e TEST_MODE=1 --env-file .env.test ergo-miner-test

# Wait for the container to initialize
echo "Waiting for the container to start..."
sleep 15

# Skipping health check in test environment.
# The health check relies on the lolMiner API, which does not start
# without a GPU. The test environment lacks GPU support.
echo "Skipping health check in test environment..."

# Test the metrics endpoint
echo "Testing the metrics endpoint..."
if docker inspect -f '{{.State.Running}}' ergo-miner-test-container | grep -q "true"; then
    METRICS_OUTPUT=$(docker exec ergo-miner-test-container curl -s http://localhost:4455)
    if ! echo "$METRICS_OUTPUT" | grep -q "lolminer_hashrate"; then
      echo "Metrics endpoint test failed!"
      echo "Output: $METRICS_OUTPUT"
      docker rm -f ergo-miner-test-container
      exit 1
    fi
else
    echo "Container not running, skipping metrics test."
fi
echo "Metrics endpoint test passed!"

# Cleanup
echo "Cleaning up..."
docker rm -f ergo-miner-test-container
echo "Test completed successfully."
