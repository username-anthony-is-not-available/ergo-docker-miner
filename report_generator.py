import os
import time
import logging
from datetime import datetime
import database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("report_generator")

DATA_DIR = os.getenv('DATA_DIR', '/app/data')
REPORT_FILE = os.path.join(DATA_DIR, 'weekly_report.txt')

def generate_weekly_report():
    try:
        logger.info("Generating weekly report...")
        history = database.get_history(days=7)
        if not history:
            logger.warning("No history data available for weekly report")
            return

        total_hashrate = 0
        total_dual_hashrate = 0
        total_power = 0
        total_efficiency = 0
        count = len(history)

        # Group by day for daily summary
        daily_stats = {}

        for entry in history:
            h = entry.get('hashrate', 0)
            dh = entry.get('dual_hashrate', 0)
            p = entry.get('total_power_draw', 0)

            total_hashrate += h
            total_dual_hashrate += dh
            total_power += p
            if p > 0:
                total_efficiency += h / p

            # Use timestamp string to get the day
            # Format is usually YYYY-MM-DDTHH:MM:SS.mmmmmm
            day = entry['timestamp'][:10]
            if day not in daily_stats:
                daily_stats[day] = {'hashrate': 0, 'power': 0, 'count': 0}
            daily_stats[day]['hashrate'] += h
            daily_stats[day]['power'] += p
            daily_stats[day]['count'] += 1

        avg_hashrate = total_hashrate / count if count > 0 else 0
        avg_dual_hashrate = total_dual_hashrate / count if count > 0 else 0
        avg_power = total_power / count if count > 0 else 0
        avg_efficiency = total_efficiency / count if count > 0 else 0

        report_content = f"""Mining Weekly Report
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Period: Last 7 days
--------------------------------------
Total Samples: {count}
Average Hashrate: {avg_hashrate:.2f} MH/s
Average Dual Hashrate: {avg_dual_hashrate:.2f} MH/s
Average Power Draw: {avg_power:.1f} W
Average Efficiency: {avg_efficiency:.3f} MH/W
--------------------------------------
Daily Summary:
"""
        # Sort days descending
        for day in sorted(daily_stats.keys(), reverse=True):
            stats = daily_stats[day]
            d_avg_h = stats['hashrate'] / stats['count']
            d_avg_p = stats['power'] / stats['count']
            report_content += f"{day}: {d_avg_h:.2f} MH/s | {d_avg_p:.1f} W\n"

        report_content += "--------------------------------------\n"

        # Ensure directory exists before writing
        os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)

        with open(REPORT_FILE, 'w') as f:
            f.write(report_content)
        logger.info(f"Weekly report generated at {REPORT_FILE}")

    except Exception as e:
        logger.error(f"Error generating weekly report: {e}")

def main():
    database.init_db()

    # Ensure DATA_DIR exists
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)

    logger.info("Starting report generator background process...")

    while True:
        # Generate report
        generate_weekly_report()

        # Run every hour, aligned to the hour
        now = time.time()
        sleep_time = 3600 - (now % 3600)
        if sleep_time < 60: # If we are very close to the hour, wait for the next one
            sleep_time += 3600

        logger.info(f"Next report generation in {sleep_time} seconds")
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()
