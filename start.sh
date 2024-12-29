#!/bin/bash

envsubst < ./miner_config.template > miner_config.sh

chmod +x miner_config.sh

/app/1.92/lolMiner $(cat miner_config.sh)
