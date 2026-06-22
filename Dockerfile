ARG GPU_TYPE=nvidia
ARG LOLMINER_VERSION=1.98a
ARG T_REX_VERSION=0.26.8
ARG LOLMINER_URL=https://github.com/Lolliedieb/lolMiner-releases/releases/download/${LOLMINER_VERSION}/lolMiner_v${LOLMINER_VERSION}_Lin64.tar.gz
ARG T_REX_URL=https://github.com/trexminer/T-Rex/releases/download/${T_REX_VERSION}/t-rex-${T_REX_VERSION}-linux.tar.gz

# --- Miner Builder Stage ---
FROM ubuntu:22.04 AS miner-builder
ARG GPU_TYPE
ARG LOLMINER_URL
ARG T_REX_URL

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends wget ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Download lolMiner
RUN wget -qO- "${LOLMINER_URL}" | tar -xvz --strip-components=1 && \
    chmod +x lolMiner

# Download T-Rex only for NVIDIA
RUN if [ "$GPU_TYPE" = "nvidia" ]; then \
      wget -qO- "${T_REX_URL}" | tar -xvz && \
      chmod +x t-rex; \
    else \
      touch t-rex; \
    fi

# --- Python Builder Stage ---
FROM ubuntu:22.04 AS python-builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip python3-venv && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# --- Runtime Stage ---
FROM ubuntu:22.04
ARG GPU_TYPE

WORKDIR /app

# Install runtime dependencies and GPU-specific packages in a single layer
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    curl \
    jq \
    python3 \
    logrotate \
    procps \
    gosu && \
    if [ "$GPU_TYPE" = "nvidia" ]; then \
      apt-get install -y --no-install-recommends nvidia-utils-525 xserver-xorg; \
    else \
      apt-get install -y --no-install-recommends rocm-smi rocm-opencl-runtime clinfo; \
    fi && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1000 miner && \
    useradd -u 1000 -g miner -m -s /bin/bash miner && \
    (groupadd -r video || true) && \
    (groupadd -r render || true) && \
    usermod -aG video,render miner

# Copy Python virtual environment
COPY --from=python-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy miner binaries
COPY --from=miner-builder /app/lolMiner /app/lolMiner
COPY --from=miner-builder /app/t-rex /app/t-rex

# Copy application files
COPY start.sh metrics.py miner_api.py healthcheck.sh restart.sh database.py gpu_profiles.json env_config.py profit_switcher.py report_generator.py logrotate.conf log_monitor.py price_fetcher.py discord_notifier.py streamlit_app.py ./

RUN chmod +x start.sh healthcheck.sh restart.sh log_monitor.py && \
    mkdir -p /app/data && \
    chown -R miner:miner /app/data && \
    chmod 755 /app

ENV DATA_DIR=/app/data
ENV PYTHONUNBUFFERED=1

EXPOSE 4444 4455 4456 5000

HEALTHCHECK --interval=30s --timeout=3s \
    CMD ./healthcheck.sh

CMD ["./start.sh"]
