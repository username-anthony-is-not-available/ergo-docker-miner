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
    apt-get install -y gettext-base curl jq python3 && \
    rm -rf /var/lib/apt/lists/*

# Copy miner binary from builder stage
COPY --from=builder /app/lolMiner /app/lolMiner

# Copy scripts
COPY start.sh metrics.sh metrics.py ./

RUN chmod +x start.sh metrics.sh

EXPOSE 4444 4455

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl --fail http://localhost:4444/

CMD ["./start.sh"]
