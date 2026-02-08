# Builder Stage
FROM nvidia/cuda:11.8.0-base-ubuntu22.04 AS builder

# Miner versions - can be overridden during build
ARG LOLMINER_VERSION=1.98a
ARG T_REX_VERSION=0.26.8
ARG LOLMINER_URL=https://github.com/Lolliedieb/lolMiner-releases/releases/download/${LOLMINER_VERSION}/lolMiner_v${LOLMINER_VERSION}_Lin64.tar.gz
ARG T_REX_URL=https://github.com/trexminer/T-Rex/releases/download/${T_REX_VERSION}/t-rex-${T_REX_VERSION}-linux.tar.gz

WORKDIR /app

RUN apt-get update && \
    apt-get install -y wget && \
    wget -qO- "${LOLMINER_URL}" | tar -xvz --strip-components=1 && \
    wget -qO- "${T_REX_URL}" | tar -xvz && \
    chmod +x lolMiner t-rex && \
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
    xserver-xorg \
    procps \
    gosu && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -g 1000 miner && \
    useradd -u 1000 -g miner -m -s /bin/bash miner && \
    # Add miner to video and render groups for GPU access
    (groupadd -r video || true) && \
    (groupadd -r render || true) && \
    usermod -aG video,render miner

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy miner binaries from builder stage
COPY --from=builder /app/lolMiner /app/lolMiner
COPY --from=builder /app/t-rex /app/t-rex

# Copy scripts
COPY start.sh metrics.sh metrics.py miner_api.py healthcheck.sh restart.sh database.py gpu_profiles.json env_config.py profit_switcher.py cuda_monitor.sh report_generator.py ./
COPY streamlit_app.py .

RUN chmod +x start.sh metrics.sh healthcheck.sh restart.sh cuda_monitor.sh && \
    mkdir -p /app/data && \
    chown -R miner:miner /app/data && \
    chmod 755 /app

ENV DATA_DIR=/app/data

EXPOSE 4444 4455 4456 5000

HEALTHCHECK --interval=30s --timeout=3s \
    CMD ./healthcheck.sh

CMD ["./start.sh"]
