#!/bin/bash

while true; do
  {
    # Check if the API is available
    if curl -s http://localhost:4444/ > /dev/null; then
      METRICS=$(curl -s http://localhost:4444/)
      HASHRATE=$(echo "$METRICS" | jq -r '.Total_Performance[0]')
      AVG_TEMPERATURE=$(echo "$METRICS" | jq -r '[.GPUs[].Temperature] | add / length')
      AVG_FAN_SPEED=$(echo "$METRICS" | jq -r '[.GPUs[].Fan_Speed] | add / length')

      echo "{\"hashrate\": \"$HASHRATE\", \"avg_temperature\": \"$AVG_TEMPERATURE\", \"avg_fan_speed\": \"$AVG_FAN_SPEED\"}"
    else
      echo "{\"hashrate\": \"N/A\", \"avg_temperature\": \"N/A\", \"avg_fan_speed\": \"N/A\"}"
    fi
  } | nc -l -p 4455 -q 1
done
