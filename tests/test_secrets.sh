#!/bin/bash

# tests/test_secrets.sh
# Test script to verify Docker secrets loading logic in start.sh

set -e

# Mock /run/secrets
MOCK_SECRETS_DIR=$(mktemp -d)
echo "secret_wallet_address" > "$MOCK_SECRETS_DIR/WALLET_ADDRESS"
echo "secret_dual_wallet" > "$MOCK_SECRETS_DIR/DUAL_WALLET"
echo "secret_tg_token" > "$MOCK_SECRETS_DIR/TELEGRAM_BOT_TOKEN"
echo "secret_tg_chat" > "$MOCK_SECRETS_DIR/TELEGRAM_CHAT_ID"
echo "https://discord.com/api/webhooks/secret" > "$MOCK_SECRETS_DIR/DISCORD_WEBHOOK_URL"
echo "custom_file_wallet" > "$MOCK_SECRETS_DIR/custom_wallet"

# Function from start.sh (adapted for test with MOCK_SECRETS_DIR)
load_secret() {
    local var=$1
    local file_var="${var}_FILE"
    local custom_file="${!file_var}"
    local file="$MOCK_SECRETS_DIR/$var"

    if [ -n "${!var}" ]; then
        echo "$var is already set, skipping secret."
        return 0
    fi

    if [ -n "$custom_file" ] && [ -f "$custom_file" ]; then
        file="$custom_file"
    fi

    if [ -f "$file" ]; then
        local secret_value
        secret_value=$(tr -d '\r\n' < "$file")
        if [ -n "$secret_value" ]; then
            export "$var=$secret_value"
            echo "Loaded $var from secret."
        fi
    fi
}

echo "Running Docker Secrets Tests..."

# Test 1: Load from secret when env var is empty
unset WALLET_ADDRESS WALLET_ADDRESS_FILE
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

# Test 4: Load notification secrets
unset TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID DISCORD_WEBHOOK_URL
load_secret TELEGRAM_BOT_TOKEN
load_secret TELEGRAM_CHAT_ID
load_secret DISCORD_WEBHOOK_URL
if [ "$TELEGRAM_BOT_TOKEN" == "secret_tg_token" ] && [ "$TELEGRAM_CHAT_ID" == "secret_tg_chat" ] && [ "$DISCORD_WEBHOOK_URL" == "https://discord.com/api/webhooks/secret" ]; then
    echo "✅ Test 4 Passed: Notification secrets loaded"
else
    echo "❌ Test 4 Failed: Notification secrets mismatch"
    exit 1
fi

# Test 5: Support <VAR>_FILE custom secret path
unset WALLET_ADDRESS
export WALLET_ADDRESS_FILE="$MOCK_SECRETS_DIR/custom_wallet"
load_secret WALLET_ADDRESS
if [ "$WALLET_ADDRESS" == "custom_file_wallet" ]; then
    echo "✅ Test 5 Passed: WALLET_ADDRESS loaded from WALLET_ADDRESS_FILE"
else
    echo "❌ Test 5 Failed: WALLET_ADDRESS is '$WALLET_ADDRESS', expected 'custom_file_wallet'"
    exit 1
fi

# Cleanup
rm -rf "$MOCK_SECRETS_DIR"
echo "All Docker Secrets tests passed!"
