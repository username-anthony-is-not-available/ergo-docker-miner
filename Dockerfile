# Builder Stage
FROM nvidia/cuda:11.8.0-base-ubuntu22.04 AS builder

RUN apt-get update && \
    apt-get install -y curl wget && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV LOLMINER_URL=https://github.com/Lolliedieb/lolMiner-releases/releases/download/1.92/lolMiner_v1.92_Lin64.tar.gz

RUN wget -q "$LOLMINER_URL" && \
    tar -xvf $(basename "$LOLMINER_URL") && \
    chmod +x 1.92/lolMiner

# Runtime Stage
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

WORKDIR /app

# Install only necessary runtime dependencies and apply security upgrades
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y gettext-base curl jq netcat && \
    rm -rf /var/lib/apt/lists/*

# Copy miner binary from builder stage
COPY --from=builder /app/1.92 /app/1.92

# Copy scripts
COPY start.sh metrics.sh ./

RUN chmod +x start.sh metrics.sh

EXPOSE 4444 4455

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl --fail http://localhost:4444/

CMD ["./start.sh"]
