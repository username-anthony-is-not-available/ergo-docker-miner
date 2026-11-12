import logging
import os

import requests

from env_config import get_secret

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("discord_notifier")

DISCORD_ENABLE = os.getenv('DISCORD_ENABLE', 'false').lower() == 'true'
DISCORD_WEBHOOK_URL = get_secret('DISCORD_WEBHOOK_URL')
DISCORD_NOTIFY_THRESHOLD = int(os.getenv('DISCORD_NOTIFY_THRESHOLD', '300'))

def send_discord_notification(message: str) -> None:
    """Send a Discord webhook alert without logging sensitive webhook URLs."""
    webhook_url = DISCORD_WEBHOOK_URL or get_secret('DISCORD_WEBHOOK_URL')
    if not DISCORD_ENABLE or not webhook_url:
        return

    payload = {
        "content": message,
        "username": "Ergo Miner Monitor"
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Discord notification sent successfully")
    except requests.exceptions.RequestException as e:
        safe_err = str(e).replace(webhook_url, "<redacted-webhook-url>")
        logger.error(f"Failed to send Discord notification: {safe_err}")
