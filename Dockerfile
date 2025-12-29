# Builder Stage
FROM nvidia/cuda:11.8.0-base-ubuntu22.04 AS builder

ARG LOLMINER_VERSION=1.92
ARG LOLMINER_URL=https://github.com/Lolliedieb/lolMiner-releases/releases/download/${LOLMINER_VERSION}/lolMiner_v${LOLMINER_VERSION}_Lin64.tar.gz

WORKDIR /app

RUN apt-get update && \
    apt-get install -y wget && \
    wget -qO- "${LOLMINER_URL}" | tar -xvz --strip-components=1 && \
    chmod +x lolMiner && \
    rm -rf /var/lib/apt/lists/*

# Runtime Stage
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

WORKDIR /app

# Install only necessary runtime dependencies and apply security upgrades
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    gettext-base \
    curl \
    jq \
    python3 \
    python3-pip \
    nvidia-utils-525 \
    xserver-xorg && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy miner binary from builder stage
COPY --from=builder /app/lolMiner /app/lolMiner

# Copy scripts
COPY start.sh metrics.sh metrics.py healthcheck.sh ./
COPY dashboard.py .
COPY templates/ templates/
COPY static/ static/

RUN chmod +x start.sh metrics.sh healthcheck.sh

EXPOSE 4444 4455 4456 5000

HEALTHCHECK --interval=30s --timeout=3s \
    CMD ./healthcheck.sh

CMD ["./start.sh"]
