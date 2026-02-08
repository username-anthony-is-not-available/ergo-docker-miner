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
            # 2Miners 'luck' is current round luck, can be very volatile.
            # For a 'simple' supervisor, we might just use the fee if no long-term effort is found.
            # But let's try to find something.
            pass

        elif pool["type"] == "herominers":
            # HeroMiners has 'effort_1d' (average effort over 24h)
            effort = data.get("effort_1d", 1.0)

        elif pool["type"] == "nanopool":
            # Nanopool API response structure varies, using default for now
            pass

        elif pool["type"] == "woolypooly":
            # WoolyPooly API response structure varies, using default for now
            pass

        score = (1.0 - fee) / max(effort, 0.01)
        return score
    except Exception as e:
        logger.error(f"Error fetching stats for {pool['name']}: {e}")
    return 0.0

def main():
    logger.info("Profit Switcher started")
    while True:
        try:
            env_vars = read_env_file()
            auto_switching = env_vars.get("AUTO_PROFIT_SWITCHING", "false").lower() == "true"
            threshold = float(env_vars.get("PROFIT_SWITCHING_THRESHOLD", "0.005"))
            interval = int(env_vars.get("PROFIT_SWITCHING_INTERVAL", "3600"))

            if not auto_switching:
                logger.info("Auto profit switching is disabled. Sleeping for 60s.")
                time.sleep(60)
                continue

            logger.info("Auto profit switching is enabled. Checking pools...")

            current_pool_address = env_vars.get("POOL_ADDRESS")
            best_pool = None
            max_score = -1.0

            for pool in POOLS:
                score = get_pool_profitability(pool)
                logger.info(f"Pool {pool['name']} score: {score:.4f}")
                if score > max_score:
                    max_score = score
                    best_pool = pool

            if best_pool and best_pool["stratum"] != current_pool_address:
                # We need to know the score of the current pool to compare.
                current_pool_score = 0.0
                for pool in POOLS:
                    if pool["stratum"] == current_pool_address:
                        current_pool_score = get_pool_profitability(pool)
                        break

                if max_score > current_pool_score * (1 + threshold):
                    logger.info(f"Better pool found: {best_pool['name']} with score {max_score:.4f} (current: {current_pool_score:.4f})")
                    logger.info(f"Switching to {best_pool['stratum']}")

                    env_vars["POOL_ADDRESS"] = best_pool["stratum"]
                    write_env_file(env_vars)

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
