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
    python3-flask \
    nvidia-utils-525 \
    xserver-xorg && \
    pip3 install prometheus_client && \
    rm -rf /var/lib/apt/lists/*

# Copy miner binary from builder stage
COPY --from=builder /app/lolMiner /app/lolMiner

# Copy scripts
COPY start.sh metrics.sh metrics.py dashboard.py index.html ./

RUN chmod +x start.sh metrics.sh

EXPOSE 4444 4455 4456

HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl --fail http://localhost:4444/

CMD ["./start.sh"]
