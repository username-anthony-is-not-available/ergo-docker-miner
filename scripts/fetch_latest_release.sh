#!/bin/bash

# Fetch the latest release tag from a GitHub repository.
# Usage: ./fetch_latest_release.sh <owner/repo>

REPO=$1

if [ -z "$REPO" ]; then
    echo "Usage: $0 <owner/repo>" >&2
    exit 1
fi

# Try to use curl and jq to fetch the latest release tag
if command -v jq &> /dev/null; then
    LATEST_TAG=$(curl -s "https://api.github.com/repos/${REPO}/releases/latest" | jq -r .tag_name)
else
    # Fallback to grep if jq is not available
    LATEST_TAG=$(curl -s "https://api.github.com/repos/${REPO}/releases/latest" | grep -oP '"tag_name":\s*"\K[^"]+')
fi

if [ "$LATEST_TAG" == "null" ] || [ -z "$LATEST_TAG" ]; then
    echo "Error: Could not fetch latest release for ${REPO}" >&2
    exit 1
fi

echo "$LATEST_TAG"
