#!/bin/bash

# Test setup.sh
# We'll use a heredoc to simulate user input

echo "Running setup.sh test 1 (NVIDIA, Dual, OC, Extra Args)..."

# Back up existing .env if any
if [ -f .env ]; then
    mv .env .env.bak
fi

# Test Case 1: Complex configuration
# Wallet: MyTestWallet
# Worker: test-worker
# Pool: 2 (HeroMiners)
# Miner: 1 (lolMiner)
# GPU Type: 1 (NVIDIA)
# Run NVIDIA check: n
# GPU Count: 2 (0,1)
# Apply OC: y
# Profile: RTX 3070
# Tuning Preset: 2 (Efficient)
# Dual Mining: y
# Dual Algo: 1 (Kaspa)
# Dual Wallet: MyDualWallet
# Dual Pool: MyDualPool
# Dual Worker: test-worker-dual
# Extra Args: --extra-param 1
# Multi-Process: y
# Profit Switch: y
# Threshold: 0.01
# Interval: 7200
# Cooldown: 1200
# Telegram: y
# Telegram Token: MyToken
# Telegram ID: MyID
# Telegram Threshold: 600
# Auto-Restart: y
# Start now: n
./setup.sh <<EOF
MyTestWallet
test-worker
2
1
1
n
2
y
RTX 3070
2
y
1
MyDualWallet
MyDualPool
test-worker-dual
--extra-param 1
y
y
0.01
7200
1200
y
MyToken
MyID
600
y
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
    if ! grep -q "^$1$" .env; then
        echo "Failed: $1 not found in .env (exactly)"
        grep "${1%%=*}" .env || echo "Actual value: (not found)"
        EXIT_CODE=1
    fi
}

check_var "WALLET_ADDRESS=MyTestWallet"
check_var "WORKER_NAME=test-worker"
check_var "POOL_ADDRESS=stratum+tcp://herominers.com:1180"
check_var "MINER=lolminer"
check_var "GPU_DEVICES=0,1"
check_var "APPLY_OC=true"
check_var "GPU_TUNING=Efficient"
check_var "ECO_MODE=true"
check_var "GPU_PROFILE=RTX 3070"
check_var "DUAL_ALGO=KASPADUAL"
check_var "DUAL_WALLET=MyDualWallet"
check_var "DUAL_POOL=MyDualPool"
check_var "DUAL_WORKER=test-worker-dual"
check_var "EXTRA_ARGS=--extra-param 1"
check_var "MULTI_PROCESS=true"
check_var "AUTO_PROFIT_SWITCHING=true"
check_var "PROFIT_SWITCHING_THRESHOLD=0.01"
check_var "PROFIT_SWITCHING_INTERVAL=7200"
check_var "MIN_SWITCH_COOLDOWN=1200"
check_var "TELEGRAM_ENABLE=true"
check_var "TELEGRAM_BOT_TOKEN=MyToken"
check_var "TELEGRAM_CHAT_ID=MyID"
check_var "TELEGRAM_NOTIFY_THRESHOLD=600"
check_var "AUTO_RESTART_ON_CUDA_ERROR=true"

if [ $EXIT_CODE -eq 0 ]; then
    echo "setup.sh test 1 PASSED"
else
    echo "setup.sh test 1 FAILED"
fi

rm .env
EXIT_CODE=0

echo "Running setup.sh test 2 (AMD, Defaults)..."
# Wallet: AmdWallet
# Worker: default
# Pool: default
# Miner: default
# GPU Type: 2 (AMD)
# GPU Count: default (AUTO)
# Dual Mining: n
# Extra Args: empty
# Multi-Process: n
# Profit Switching: n
# Telegram: n
# Auto-Restart: n
# Node Sync: n
# Start now: n
./setup.sh <<EOF
AmdWallet

1
1
2


n
n

n
n
n
n
n
EOF

check_var "WALLET_ADDRESS=AmdWallet"
check_var "ECO_MODE=false"
check_var "WORKER_NAME=ergo-miner"
check_var "POOL_ADDRESS=stratum+tcp://erg.2miners.com:8080"
check_var "MINER=lolminer"
check_var "GPU_DEVICES=AUTO"
check_var "MULTI_PROCESS=false"
check_var "APPLY_OC=false"
check_var "AUTO_PROFIT_SWITCHING=false"
check_var "TELEGRAM_ENABLE=false"
check_var "AUTO_RESTART_ON_CUDA_ERROR=false"

if [ $EXIT_CODE -eq 0 ]; then
    echo "setup.sh test 2 PASSED"
else
    echo "setup.sh test 2 FAILED"
fi

rm .env
EXIT_CODE=0

echo "Running setup.sh test 3 (NVIDIA, Quiet)..."
# Wallet: QuietWallet
# Worker: quiet-rig
# Pool: 1
# Miner: 1
# GPU Type: 1
# Run NVIDIA check: n
# GPU Count: AUTO
# Apply OC: y
# Profile: RTX 4090
# Tuning Preset: 3 (Quiet)
# Dual Mining: n
# Extra Args: empty
# Multi-Process: n
# Profit Switching: n
# Telegram: n
# Auto-Restart: n
# Node Sync: n
# Start now: n
./setup.sh <<EOF
QuietWallet
quiet-rig
1
1
1
n

y
RTX 4090
3
n
n

n
n
n
n
n
EOF

check_var "WALLET_ADDRESS=QuietWallet"
check_var "WORKER_NAME=quiet-rig"
check_var "APPLY_OC=true"
check_var "GPU_TUNING=Quiet"
check_var "ECO_MODE=false"
check_var "GPU_PROFILE=RTX 4090"

if [ $EXIT_CODE -eq 0 ]; then
    echo "setup.sh test 3 PASSED"
else
    echo "setup.sh test 3 FAILED"
fi

# Cleanup
rm -f .env
if [ -f .env.bak ]; then
    mv .env.bak .env
fi

exit $EXIT_CODE
