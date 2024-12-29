FROM nvidia/cuda:11.8.0-base-ubuntu22.04

RUN apt-get update && apt-get install -y curl wget gettext

WORKDIR /app

ENV LOLMINER_URL=https://github.com/Lolliedieb/lolMiner-releases/releases/download/1.92/lolMiner_v1.92_Lin64.tar.gz

RUN wget -q "$LOLMINER_URL" && \
    tar -xvf $(basename "$LOLMINER_URL") && \
    chmod +x 1.92/lolMiner

COPY start.sh miner_config.template ./

CMD ["./start.sh"]
