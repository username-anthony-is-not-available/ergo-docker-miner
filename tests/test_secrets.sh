#!/bin/bash

# tests/test_secrets.sh
# Test script to verify Docker secrets loading logic in start.sh

set -e

# Mock /run/secrets
MOCK_SECRETS_DIR=$(mktemp -d)
echo "secret_wallet_address" > "$MOCK_SECRETS_DIR/WALLET_ADDRESS"
echo "secret_dual_wallet" > "$MOCK_SECRETS_DIR/DUAL_WALLET"

# Function from start.sh (adapted for test)
load_secret() {
    local var=$1
    local file="$MOCK_SECRETS_DIR/$var"
    if [ -f "$file" ]; then
        if [ -z "${!var}" ]; then
            export "$var"=$(cat "$file" | tr -d '\r\n')
            echo "Loaded $var from secret: ${!var}"
        else
            echo "$var is already set, skipping secret."
        fi
    fi
}

echo "Running Docker Secrets Tests..."

# Test 1: Load from secret when env var is empty
unset WALLET_ADDRESS
load_secret WALLET_ADDRESS
if [ "$WALLET_ADDRESS" == "secret_wallet_address" ]; then
    echo "✅ Test 1 Passed: WALLET_ADDRESS loaded from secret"
else
    echo "❌ Test 1 Failed: WALLET_ADDRESS is '$WALLET_ADDRESS', expected 'secret_wallet_address'"
    exit 1
fi

# Test 2: Do not override if env var is already set
export DUAL_WALLET="env_dual_wallet"
load_secret DUAL_WALLET
if [ "$DUAL_WALLET" == "env_dual_wallet" ]; then
    echo "✅ Test 2 Passed: DUAL_WALLET not overridden by secret"
else
    echo "❌ Test 2 Failed: DUAL_WALLET is '$DUAL_WALLET', expected 'env_dual_wallet'"
    exit 1
fi

# Test 3: Load DUAL_WALLET from secret when empty
unset DUAL_WALLET
load_secret DUAL_WALLET
if [ "$DUAL_WALLET" == "secret_dual_wallet" ]; then
    echo "✅ Test 3 Passed: DUAL_WALLET loaded from secret"
else
    echo "❌ Test 3 Failed: DUAL_WALLET is '$DUAL_WALLET', expected 'secret_dual_wallet'"
    exit 1
fi

# Cleanup
rm -rf "$MOCK_SECRETS_DIR"
echo "All Docker Secrets tests passed!"
