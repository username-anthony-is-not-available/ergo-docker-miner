#!/bin/bash
# tests/test_fetch_latest.sh

# Create a temporary directory for mocks
MOCK_DIR=$(mktemp -d)
trap 'rm -rf "$MOCK_DIR"' EXIT
PATH="$MOCK_DIR:$PATH"

# Mock curl
cat <<EOF > "$MOCK_DIR/curl"
#!/bin/bash
echo '{"tag_name": "1.99"}'
EOF
chmod +x "$MOCK_DIR/curl"

# Run the script
RESULT=$(./scripts/fetch_latest_release.sh "some/repo")

# Check the result
if [ "$RESULT" == "1.99" ]; then
    echo "Test passed: Found version 1.99"
else
    echo "Test failed: Expected 1.99, got $RESULT"
    exit 1
fi

# Test failure case
cat <<EOF > "$MOCK_DIR/curl"
#!/bin/bash
echo '{"message": "Not Found"}'
EOF

RESULT=$(./scripts/fetch_latest_release.sh "nonexistent/repo" 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "Test passed: Correctly handled error"
else
    echo "Test failed: Expected error for nonexistent repo"
    exit 1
fi
