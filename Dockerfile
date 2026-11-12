ARG GPU_TYPE=nvidia
ARG LOLMINER_VERSION=1.98a
ARG T_REX_VERSION=0.26.8
ARG LOLMINER_URL=https://github.com/Lolliedieb/lolMiner-releases/releases/download/${LOLMINER_VERSION}/lolMiner_v${LOLMINER_VERSION}_Lin64.tar.gz
ARG T_REX_URL=https://github.com/trexminer/T-Rex/releases/download/${T_REX_VERSION}/t-rex-${T_REX_VERSION}-linux.tar.gz

# --- Miner Builder Stage ---
FROM ubuntu:22.04 AS miner-builder
ARG LOLMINER_URL
ARG T_REX_URL

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends wget ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Download lolMiner before GPU_TYPE ARG so nvidia/amd builds share this layer
RUN wget -qO- "${LOLMINER_URL}" | tar -xz --strip-components=1 && \
    chmod +x lolMiner

# Download T-Rex only for NVIDIA
ARG GPU_TYPE=nvidia
RUN if [ "$GPU_TYPE" = "nvidia" ]; then \
      wget -qO- "${T_REX_URL}" | tar -xz && \
      chmod +x t-rex; \
    else \
      touch t-rex; \
    fi

# --- Python Builder Stage ---
FROM ubuntu:22.04 AS python-builder

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip python3-venv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt && \
    find /opt/venv -type d -name '__pycache__' -exec rm -rf {} +

# --- Runtime Stage ---
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    DATA_DIR=/app/data \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install common runtime packages and create non-root user before GPU_TYPE divergence
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
      curl \
      jq \
      python3 \
      logrotate \
      procps \
      gosu && \
    groupadd -g 1000 miner && \
    useradd -u 1000 -g miner -m -s /bin/bash miner && \
    (groupadd -r video || true) && \
    (groupadd -r render || true) && \
    usermod -aG video,render miner && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install GPU-specific runtime packages
ARG GPU_TYPE=nvidia
RUN apt-get update && \
    if [ "$GPU_TYPE" = "nvidia" ]; then \
      apt-get install -y --no-install-recommends nvidia-utils-525 xserver-xorg; \
    else \
      apt-get install -y --no-install-recommends rocm-smi rocm-opencl-runtime clinfo; \
    fi && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy Python virtual environment and miner binaries (most stable artifacts first)
COPY --from=python-builder /opt/venv /opt/venv
COPY --from=miner-builder /app/lolMiner /app/lolMiner
COPY --from=miner-builder /app/t-rex /app/t-rex

# Copy application files last so code changes preserve upstream dependency layers
COPY start.sh config_validator.py metrics.py miner_api.py network_retry.py \
     healthcheck.sh restart.sh database.py gpu_profiles.json env_config.py \
     profit_switcher.py report_generator.py logrotate.conf log_monitor.py \
     price_fetcher.py discord_notifier.py streamlit_app.py ./

RUN chmod +x start.sh healthcheck.sh restart.sh log_monitor.py && \
    mkdir -p /app/data && \
    chown -R miner:miner /app/data && \
    chmod 755 /app

EXPOSE 4444 4455 4456 5000

HEALTHCHECK --interval=30s --timeout=3s \
    CMD ./healthcheck.sh

CMD ["./start.sh"]
