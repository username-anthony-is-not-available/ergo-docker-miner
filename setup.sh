#!/bin/bash

# Exit on error
set -e

# Colors for better visibility
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Ergo Miner Setup Assistant          ${NC}"
echo -e "${BLUE}========================================${NC}"
echo "This script will help you configure your Ergo miner."
echo -e "${GREEN}Security Tip: This miner now runs as a non-root user (UID 1000)${NC}"
echo -e "${GREEN}inside the container for improved security.${NC}"

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Warning: docker is not installed. Please install it to run the miner.${NC}"
fi

# 1. Wallet Address
echo -e "\n${GREEN}1. Wallet Configuration${NC}"
read -p "Enter your Ergo Wallet Address (Required): " WALLET_ADDRESS
while [ -z "$WALLET_ADDRESS" ]; do
    echo -e "${YELLOW}Wallet address is required!${NC}"
    read -p "Enter your Ergo Wallet Address: " WALLET_ADDRESS
done

# 2. Worker Name
read -p "Enter Worker Name [ergo-miner]: " WORKER_NAME
WORKER_NAME=${WORKER_NAME:-ergo-miner}

# 3. Mining Pool
echo -e "\n${GREEN}2. Pool Configuration${NC}"
echo "Choose a Mining Pool:"
echo "1) 2Miners (stratum+tcp://erg.2miners.com:8080)"
echo "2) HeroMiners (stratum+tcp://herominers.com:1180)"
echo "3) Nanopool (stratum+tcp://erg-eu1.nanopool.org:11111)"
echo "4) WoolyPooly (stratum+tcp://pool.woolypooly.com:3100)"
echo "5) Custom"
read -p "Selection [1]: " POOL_CHOICE
case $POOL_CHOICE in
    2) POOL_ADDRESS="stratum+tcp://herominers.com:1180" ;;
    3) POOL_ADDRESS="stratum+tcp://erg-eu1.nanopool.org:11111" ;;
    4) POOL_ADDRESS="stratum+tcp://pool.woolypooly.com:3100" ;;
    5) read -p "Enter custom pool address: " POOL_ADDRESS ;;
    *) POOL_ADDRESS="stratum+tcp://erg.2miners.com:8080" ;;
esac

# 4. Miner Selection
echo -e "\n${GREEN}3. Miner Selection${NC}"
echo "1) lolMiner (Recommended, supports AMD/NVIDIA and Dual Mining)"
echo "2) T-Rex (NVIDIA only)"
read -p "Selection [1]: " MINER_CHOICE
if [ "$MINER_CHOICE" == "2" ]; then
    MINER="t-rex"
else
    MINER="lolminer"
fi

# Fetch latest miner versions
echo -e "\n${BLUE}Fetching latest miner versions...${NC}"
LOLMINER_VERSION="1.98a"
T_REX_VERSION="0.26.8"

if [ -f "./scripts/fetch_latest_release.sh" ]; then
    # lolMiner
    LATEST_LOLMINER=$(./scripts/fetch_latest_release.sh "Lolliedieb/lolMiner-releases" 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$LATEST_LOLMINER" ]; then
        echo -e "Found latest lolMiner: ${GREEN}${LATEST_LOLMINER}${NC}"
        LOLMINER_VERSION=$LATEST_LOLMINER
    else
        echo -e "${YELLOW}Warning: Could not fetch latest lolMiner version. Using default.${NC}"
    fi

    # T-Rex
    LATEST_TREX=$(./scripts/fetch_latest_release.sh "trexminer/T-Rex" 2>/dev/null)
    if [ $? -eq 0 ] && [ -n "$LATEST_TREX" ]; then
        echo -e "Found latest T-Rex: ${GREEN}${LATEST_TREX}${NC}"
        T_REX_VERSION=$LATEST_TREX
    else
        echo -e "${YELLOW}Warning: Could not fetch latest T-Rex version. Using default.${NC}"
    fi
else
    echo -e "${YELLOW}Warning: fetch_latest_release.sh not found. Using default versions.${NC}"
fi

# 5. GPU Type & Count
echo -e "\n${GREEN}4. GPU Configuration${NC}"
echo "Select your GPU type:"
echo "1) NVIDIA"
echo "2) AMD"
read -p "Selection [1]: " GPU_TYPE_CHOICE
if [ "$GPU_TYPE_CHOICE" == "2" ]; then
    GPU_TYPE="AMD"
else
    GPU_TYPE="NVIDIA"
fi

read -p "Enter GPU count (e.g. 2) or specific IDs (e.g. 0,1) [AUTO]: " GPU_INPUT
if [ -z "$GPU_INPUT" ] || [ "$GPU_INPUT" == "AUTO" ]; then
    GPU_DEVICES="AUTO"
elif [[ "$GPU_INPUT" =~ ^[0-9]+$ ]]; then
    # If it's a single number, generate a list 0,1,...,N-1
    GPU_DEVICES=""
    for ((i=0; i<$GPU_INPUT; i++)); do
        if [ -z "$GPU_DEVICES" ]; then
            GPU_DEVICES="$i"
        else
            GPU_DEVICES="$GPU_DEVICES,$i"
        fi
    done
else
    # Assume it's already a comma-separated list
    GPU_DEVICES=$GPU_INPUT
fi

# 6. Overclocking (NVIDIA only)
APPLY_OC="false"
GPU_PROFILE=""
if [ "$GPU_TYPE" == "NVIDIA" ]; then
    read -p "Apply Overclocking? (y/n) [n]: " APPLY_OC_CHOICE
    if [[ "$APPLY_OC_CHOICE" =~ ^[Yy]$ ]]; then
        APPLY_OC="true"
        if [ -f "gpu_profiles.json" ]; then
            echo "Available GPU Profiles:"
            if command -v jq &> /dev/null; then
                jq -r 'keys[]' gpu_profiles.json
            else
                grep -o '"[^"]*": {' gpu_profiles.json | tr -d '": {'
            fi
            read -p "Enter a profile name (e.g. RTX 3070) or leave blank: " GPU_PROFILE
        fi
    fi
fi

# 7. Dual Mining (lolMiner only)
DUAL_ALGO=""
if [ "$MINER" == "lolminer" ]; then
    read -p "Enable Dual Mining? (y/n) [n]: " DUAL_CHOICE
    if [[ "$DUAL_CHOICE" =~ ^[Yy]$ ]]; then
        echo "Select Dual Algorithm:"
        echo "1) Kaspa (KASPADUAL)"
        echo "2) Alephium (ALEPHDUAL)"
        read -p "Selection [1]: " DUAL_ALGO_CHOICE
        if [ "$DUAL_ALGO_CHOICE" == "2" ]; then
            DUAL_ALGO="ALEPHDUAL"
        else
            DUAL_ALGO="KASPADUAL"
        fi
        read -p "Enter Dual Wallet Address: " DUAL_WALLET
        read -p "Enter Dual Pool Address: " DUAL_POOL
        read -p "Enter Dual Worker Name [$WORKER_NAME-dual]: " DUAL_WORKER
        DUAL_WORKER=${DUAL_WORKER:-$WORKER_NAME-dual}
    fi
fi

# 8. Extra Arguments
echo -e "\n${GREEN}8. Extra Arguments${NC}"
read -p "Enter any extra arguments for the miner (optional): " EXTRA_ARGS

# Generate .env file
echo -e "\n${BLUE}Generating .env file...${NC}"
cat <<EOF > .env
# Ergo Miner Configuration - Generated by setup.sh

# Primary Pool and Wallet
POOL_ADDRESS=${POOL_ADDRESS}
BACKUP_POOL_ADDRESS=stratum+tcp://herominers.com:1180
WALLET_ADDRESS=${WALLET_ADDRESS}
WORKER_NAME=${WORKER_NAME}

# Miner selection
MINER=${MINER}
LOLMINER_VERSION=${LOLMINER_VERSION}
T_REX_VERSION=${T_REX_VERSION}

# GPU Selection
GPU_DEVICES=${GPU_DEVICES}

# Overclocking
APPLY_OC=${APPLY_OC}
EOF

if [ -n "$GPU_PROFILE" ]; then
    echo "GPU_PROFILE=$GPU_PROFILE" >> .env
fi

if [ -n "$EXTRA_ARGS" ]; then
    echo "EXTRA_ARGS=${EXTRA_ARGS}" >> .env
fi

if [ -n "$DUAL_ALGO" ]; then
    cat <<EOF >> .env

# Dual Mining (lolMiner only)
DUAL_ALGO=${DUAL_ALGO}
DUAL_POOL=${DUAL_POOL}
DUAL_WALLET=${DUAL_WALLET}
DUAL_WORKER=${DUAL_WORKER}
EOF
fi

echo -e "${GREEN}Configuration complete! .env file created.${NC}"

# Final instructions
echo -e "\n${BLUE}========================================${NC}"
echo -e "To start mining, run:"
if [ "$GPU_TYPE" == "NVIDIA" ]; then
    START_CMD="docker compose up -d --build nvidia"
else
    START_CMD="docker compose up -d --build amd"
fi
echo -e "  ${YELLOW}$START_CMD${NC}"
echo -e "${BLUE}========================================${NC}"

read -p "Would you like to start the miner now? (y/n) [n]: " START_NOW
if [[ "$START_NOW" =~ ^[Yy]$ ]]; then
    $START_CMD
fi
