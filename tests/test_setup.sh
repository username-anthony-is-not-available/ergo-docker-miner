#!/bin/bash

# Test setup.sh
# We'll use a heredoc to simulate user input

echo "Running setup.sh test 1 (NVIDIA, Dual, OC, Extra Args)..."

# Back up existing .env if any
if [ -f .env ]; then
    mv .env .env.bak
fi

# Test Case 1: Complex configuration
./setup.sh <<EOF
MyTestWallet
test-worker
2
1
1
2
y
RTX 3070
y
1
MyDualWallet
MyDualPool

--extra-param 1
n
EOF

# Verify .env
if [ ! -f .env ]; then
    echo "Test Failed: .env file not created"
    [ -f .env.bak ] && mv .env.bak .env
    exit 1
fi

EXIT_CODE=0

check_var() {
    if ! grep -q "$1" .env; then
        echo "Failed: $1 not found in .env"
        grep "$2" .env || echo "Actual value: (not found)"
        EXIT_CODE=1
    fi
}

check_var "WALLET_ADDRESS=MyTestWallet" "WALLET_ADDRESS"
check_var "WORKER_NAME=test-worker" "WORKER_NAME"
check_var "POOL_ADDRESS=stratum+tcp://herominers.com:1180" "POOL_ADDRESS"
check_var "MINER=lolminer" "MINER"
check_var "GPU_DEVICES=0,1" "GPU_DEVICES"
check_var "APPLY_OC=true" "APPLY_OC"
check_var "GPU_PROFILE=RTX 3070" "GPU_PROFILE"
check_var "DUAL_ALGO=KASPADUAL" "DUAL_ALGO"
check_var "DUAL_WALLET=MyDualWallet" "DUAL_WALLET"
check_var "DUAL_POOL=MyDualPool" "DUAL_POOL"
check_var "DUAL_WORKER=test-worker-dual" "DUAL_WORKER"
check_var "EXTRA_ARGS=--extra-param 1" "EXTRA_ARGS"

if [ $EXIT_CODE -eq 0 ]; then
    echo "setup.sh test 1 PASSED"
else
    echo "setup.sh test 1 FAILED"
fi

rm .env

echo "Running setup.sh test 2 (AMD, Defaults)..."
./setup.sh <<EOF
AmdWallet

1
1
2
AUTO


n
EOF

check_var "WALLET_ADDRESS=AmdWallet" "WALLET_ADDRESS"
check_var "WORKER_NAME=ergo-miner" "WORKER_NAME"
check_var "POOL_ADDRESS=stratum+tcp://erg.2miners.com:8080" "POOL_ADDRESS"
check_var "MINER=lolminer" "MINER"
check_var "GPU_DEVICES=AUTO" "GPU_DEVICES"
check_var "APPLY_OC=false" "APPLY_OC"

if [ $EXIT_CODE -eq 0 ]; then
    echo "setup.sh test 2 PASSED"
else
    echo "setup.sh test 2 FAILED"
fi

# Cleanup
rm -f .env
if [ -f .env.bak ]; then
    mv .env.bak .env
fi

exit $EXIT_CODE
