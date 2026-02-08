import os
import time
import logging
import requests
import subprocess
from typing import Dict, List, Optional
from env_config import read_env_file, write_env_file

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("profit_switcher")

# Cooldown settings
DEFAULT_MIN_RUNTIME = 900 # 15 minutes
last_switch_time = 0.0
start_time = time.time()

POOLS = [
    {
        "name": "2Miners",
        "url": "https://erg.2miners.com/api/stats",
        "stratum": "stratum+tcp://erg.2miners.com:8080",
        "type": "2miners",
        "fee": 0.01
    },
    {
        "name": "HeroMiners",
        "url": "https://ergo.herominers.com/api/stats",
        "stratum": "stratum+tcp://herominers.com:1180",
        "type": "herominers",
        "fee": 0.009
    },
    {
        "name": "Nanopool",
        "url": "https://api.nanopool.org/v1/erg/pool/stats",
        "stratum": "stratum+tcp://erg-eu1.nanopool.org:11111",
        "type": "nanopool",
        "fee": 0.01
    },
    {
        "name": "WoolyPooly",
        "url": "https://api.woolypooly.com/stats/ergo",
        "stratum": "stratum+tcp://pool.woolypooly.com:3100",
        "type": "woolypooly",
        "fee": 0.009
    }
]

def get_pool_profitability(pool: Dict) -> float:
    """
    Calculates a profitability score for a pool.
    Score = (1 - Fee) / Effort
    Effort is estimated from the pool API if available.
    """
    try:
        response = requests.get(pool["url"], timeout=10)
        response.raise_for_status()
        data = response.json()

        fee = pool["fee"]
        effort = 1.0 # Default effort (100% luck)

        if pool["type"] == "2miners":
            # 2Miners 'luck' is current round luck in percentage.
            # We convert it to a factor (100% = 1.0)
            luck = data.get("luck", 100.0)
            if isinstance(luck, str):
                luck = float(luck)
            effort = luck / 100.0

        elif pool["type"] == "herominers":
            # HeroMiners has 'effort_1d' (average effort over 24h)
            effort = data.get("effort_1d", 1.0)

        elif pool["type"] == "nanopool":
            # Nanopool has 'luck' in some responses, but the stats endpoint is currently 404ing or different.
            # For now, we'll use a more robust way to handle the data if it exists.
            if "luck" in data:
                effort = float(data["luck"]) / 100.0

        elif pool["type"] == "woolypooly":
            # WoolyPooly 'luck' or 'effort' might be in the response.
            if "luck" in data:
                effort = float(data["luck"]) / 100.0

        score = (1.0 - fee) / max(effort, 0.01)
        return score
    except Exception as e:
        logger.error(f"Error fetching stats for {pool['name']}: {e}")
    return 0.0

def main():
    global last_switch_time
    logger.info("Profit Switcher started")
    while True:
        try:
            env_vars = read_env_file()
            auto_switching = env_vars.get("AUTO_PROFIT_SWITCHING", "false").lower() == "true"
            threshold = float(env_vars.get("PROFIT_SWITCHING_THRESHOLD", "0.005"))
            interval = int(env_vars.get("PROFIT_SWITCHING_INTERVAL", "3600"))
            min_runtime_cfg = int(env_vars.get("MIN_SWITCH_COOLDOWN", DEFAULT_MIN_RUNTIME))

            if not auto_switching:
                logger.info("Auto profit switching is disabled. Sleeping for 60s.")
                time.sleep(60)
                continue

            # Safety check: ensure miner has been running for a minimum duration
            current_time = time.time()
            runtime = current_time - start_time
            time_since_last_switch = current_time - last_switch_time if last_switch_time > 0 else runtime

            if runtime < min_runtime_cfg:
                logger.info(f"Miner in initial grace period ({int(runtime)}s / {min_runtime_cfg}s). Skipping check.")
                time.sleep(60)
                continue

            if time_since_last_switch < min_runtime_cfg:
                logger.info(f"Cooldown active since last switch ({int(time_since_last_switch)}s / {min_runtime_cfg}s). Skipping check.")
                time.sleep(60)
                continue

            logger.info("Auto profit switching is enabled. Checking pools...")

            current_pool_address = env_vars.get("POOL_ADDRESS")
            best_pool = None
            max_score = -1.0
            pool_scores = {}

            for pool in POOLS:
                score = get_pool_profitability(pool)
                logger.info(f"Pool {pool['name']} score: {score:.4f}")
                pool_scores[pool["stratum"]] = score
                if score > max_score:
                    max_score = score
                    best_pool = pool

            if best_pool and best_pool["stratum"] != current_pool_address:
                # Use cached score for the current pool
                current_pool_score = pool_scores.get(current_pool_address, 0.0)

                # If current pool was not in POOLS (custom pool), fetch it once
                if current_pool_score == 0.0:
                   logger.info(f"Current pool {current_pool_address} not in standard list, fetching score...")
                   # We don't have the API URL for custom pools easily,
                   # but if it matches one of the known pools by address, we can use it.
                   for pool in POOLS:
                       if pool["stratum"] == current_pool_address:
                           current_pool_score = get_pool_profitability(pool)
                           break

                   # Still 0? Assume it's a generic pool with default luck (score 0.99 for 1% fee)
                   if current_pool_score == 0.0:
                       current_pool_score = 0.99

                if max_score > current_pool_score * (1 + threshold):
                    logger.info(f"Better pool found: {best_pool['name']} with score {max_score:.4f} (current: {current_pool_score:.4f})")
                    logger.info(f"Switching to {best_pool['stratum']}")

                    env_vars["POOL_ADDRESS"] = best_pool["stratum"]
                    write_env_file(env_vars)
                    last_switch_time = time.time()

                    logger.info("Restarting miner...")
                    subprocess.run(["./restart.sh"], check=True)
                    # Wait for restart to complete and miner to stabilize
                    time.sleep(300)
                else:
                    logger.info("Better pool found but gain is below threshold. Staying on current pool.")
            else:
                logger.info("Currently on the most profitable pool.")

        except Exception as e:
            logger.error(f"Error in profit switcher loop: {e}")
            interval = 60 # Retry sooner on error

        time.sleep(interval)

if __name__ == "__main__":
    main()
