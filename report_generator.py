import os
import time
import csv
import logging
from datetime import datetime, timedelta
import database
from miner_api import get_full_miner_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("report_generator")

DATA_DIR = os.getenv('DATA_DIR', '/app/data')
CSV_FILE = os.path.join(DATA_DIR, 'hashrate_history.csv')
REPORT_FILE = os.path.join(DATA_DIR, 'weekly_report.txt')

def log_to_csv():
    try:
        data = get_full_miner_data()
        if not data:
            return

        timestamp = datetime.now().isoformat()
        hashrate = data.get('total_hashrate', 0)
        dual_hashrate = data.get('total_dual_hashrate', 0)

        file_exists = os.path.isfile(CSV_FILE)
        with open(CSV_FILE, mode='a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['timestamp', 'hashrate', 'dual_hashrate'])
            writer.writerow([timestamp, hashrate, dual_hashrate])
    except Exception as e:
        logger.error(f"Error logging to CSV: {e}")

def generate_weekly_report():
    try:
        logger.info("Generating weekly report...")
        history = database.get_history(days=7)
        if not history:
            logger.warning("No history data available for weekly report")
            return

        total_hashrate = 0
        total_dual_hashrate = 0
        count = len(history)

        for entry in history:
            total_hashrate += entry.get('hashrate', 0)
            total_dual_hashrate += entry.get('dual_hashrate', 0)

        avg_hashrate = total_hashrate / count if count > 0 else 0
        avg_dual_hashrate = total_dual_hashrate / count if count > 0 else 0

        report_content = f"""Mining Weekly Report
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Period: Last 7 days
--------------------------------------
Total Samples: {count}
Average Hashrate: {avg_hashrate:.2f} MH/s
Average Dual Hashrate: {avg_dual_hashrate:.2f} MH/s
--------------------------------------
"""
        with open(REPORT_FILE, 'w') as f:
            f.write(report_content)
        logger.info(f"Weekly report generated at {REPORT_FILE}")

    except Exception as e:
        logger.error(f"Error generating weekly report: {e}")

def main():
    database.init_db()
    last_report_time = 0

    # Ensure DATA_DIR exists
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)

    logger.info("Starting report generator background process...")

    while True:
        # Log to CSV every minute
        log_to_csv()

        # Generate report every 24 hours (for the last 7 days)
        if time.time() - last_report_time > 86400:
            generate_weekly_report()
            last_report_time = time.time()

        time.sleep(60)

if __name__ == "__main__":
    main()
