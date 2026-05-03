import os
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("discord_notifier")

DISCORD_ENABLE = os.getenv('DISCORD_ENABLE', 'false').lower() == 'true'
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
DISCORD_NOTIFY_THRESHOLD = int(os.getenv('DISCORD_NOTIFY_THRESHOLD', 300))

def send_discord_notification(message: str) -> None:
    if not DISCORD_ENABLE or not DISCORD_WEBHOOK_URL:
        return

    payload = {
        "content": message,
        "username": "Ergo Miner Monitor"
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Discord notification sent successfully")
    except Exception as e:
        logger.error(f"Failed to send Discord notification: {e}")
