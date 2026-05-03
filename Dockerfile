ARG GPU_TYPE=nvidia
ARG LOLMINER_VERSION=1.98a
ARG T_REX_VERSION=0.26.8
ARG LOLMINER_URL=https://github.com/Lolliedieb/lolMiner-releases/releases/download/${LOLMINER_VERSION}/lolMiner_v${LOLMINER_VERSION}_Lin64.tar.gz
ARG T_REX_URL=https://github.com/trexminer/T-Rex/releases/download/${T_REX_VERSION}/t-rex-${T_REX_VERSION}-linux.tar.gz

# Builder Stage
FROM ubuntu:22.04 AS builder
ARG GPU_TYPE
ARG LOLMINER_VERSION
ARG T_REX_VERSION
ARG LOLMINER_URL
ARG T_REX_URL

WORKDIR /app

RUN apt-get update && \
    apt-get install -y wget && \
    rm -rf /var/lib/apt/lists/*

# Download lolMiner (always)
RUN wget -qO- "${LOLMINER_URL}" | tar -xvz --strip-components=1 && \
    chmod +x lolMiner

# Download T-Rex only for NVIDIA, create empty file for AMD to avoid COPY errors
RUN if [ "$GPU_TYPE" = "nvidia" ]; then \
      wget -qO- "${T_REX_URL}" | tar -xvz && \
      chmod +x t-rex; \
    else \
      touch t-rex; \
    fi

# Runtime Stage
FROM ubuntu:22.04
ARG GPU_TYPE

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    gettext-base \
    curl \
    jq \
    python3 \
    python3-pip \
    logrotate \
    procps \
    gosu && \
    rm -rf /var/lib/apt/lists/*

# Install GPU-specific packages
RUN if [ "$GPU_TYPE" = "nvidia" ]; then \
      apt-get update && \
      apt-get install -y --no-install-recommends nvidia-utils-525 xserver-xorg && \
      rm -rf /var/lib/apt/lists/*; \
    else \
      apt-get update && \
      apt-get install -y --no-install-recommends rocm-smi rocm-opencl-runtime clinfo && \
      rm -rf /var/lib/apt/lists/*; \
    fi

# Create non-root user
RUN groupadd -g 1000 miner && \
    useradd -u 1000 -g miner -m -s /bin/bash miner && \
    (groupadd -r video || true) && \
    (groupadd -r render || true) && \
    usermod -aG video,render miner

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy miner binaries from builder
COPY --from=builder /app/lolMiner /app/lolMiner
COPY --from=builder /app/t-rex /app/t-rex

# Copy application files
COPY start.sh metrics.py miner_api.py healthcheck.sh restart.sh database.py gpu_profiles.json env_config.py profit_switcher.py report_generator.py logrotate.conf log_monitor.py price_fetcher.py discord_notifier.py ./
COPY streamlit_app.py .

RUN chmod +x start.sh healthcheck.sh restart.sh log_monitor.py && \
    mkdir -p /app/data && \
    chown -R miner:miner /app/data && \
    chmod 755 /app

ENV DATA_DIR=/app/data

EXPOSE 4444 4455 4456 5000

HEALTHCHECK --interval=30s --timeout=3s \
    CMD ./healthcheck.sh

CMD ["./start.sh"]
