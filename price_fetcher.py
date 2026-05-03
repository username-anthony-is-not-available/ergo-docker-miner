import os
import time
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("price_fetcher")

USE_LIVE_PRICE = os.getenv('USE_LIVE_PRICE', 'true').lower() == 'true'
PRICE_CACHE_TTL = int(os.getenv('PRICE_CACHE_TTL', 300))
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price?ids=ergo&vs_currencies=usd"

_cache = {
    'price': None,
    'timestamp': 0.0
}

def fetch_erg_price():
    if not USE_LIVE_PRICE:
        logger.debug("Live price disabled, returning None")
        return None

    current_time = time.time()
    if _cache['price'] is not None and (current_time - _cache['timestamp']) < PRICE_CACHE_TTL:
        logger.debug(f"Using cached ERG price: {_cache['price']}")
        return _cache['price']

    try:
        response = requests.get(COINGECKO_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        price = data.get('ergo', {}).get('usd')
        if price is not None:
            _cache['price'] = price
            _cache['timestamp'] = current_time
            logger.info(f"Fetched ERG price: ${price}")
            return price
        else:
            logger.error("Ergo price not found in CoinGecko response")
            return _cache['price']
    except Exception as e:
        logger.error(f"Failed to fetch ERG price: {e}")
        return _cache['price']
