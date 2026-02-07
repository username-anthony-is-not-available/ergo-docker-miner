import sqlite3
from datetime import datetime, timedelta
import os

DB_FILE = 'miner_history.db'

def get_connection():
    return sqlite3.connect(DB_FILE, timeout=30)

def init_db():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    hashrate REAL,
                    dual_hashrate REAL DEFAULT 0,
                    avg_temp REAL,
                    avg_fan_speed REAL,
                    accepted_shares INTEGER,
                    rejected_shares INTEGER
                )
            ''')
            # Check if dual_hashrate column exists (for existing databases)
            cursor.execute("PRAGMA table_info(history)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'dual_hashrate' not in columns:
                cursor.execute('ALTER TABLE history ADD COLUMN dual_hashrate REAL DEFAULT 0')
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")

def log_history(hashrate, avg_temp, avg_fan_speed, accepted_shares, rejected_shares, dual_hashrate=0):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO history (timestamp, hashrate, dual_hashrate, avg_temp, avg_fan_speed, accepted_shares, rejected_shares)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (datetime.now().isoformat(), hashrate, dual_hashrate, avg_temp, avg_fan_speed, accepted_shares, rejected_shares))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error logging history: {e}")

def get_history(days=30):
    since = (datetime.now() - timedelta(days=days)).isoformat()
    try:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, hashrate, dual_hashrate, avg_temp, avg_fan_speed, accepted_shares, rejected_shares
                FROM history
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            ''', (since,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Error getting history: {e}")
        return []

def prune_history(days=30):
    since = (datetime.now() - timedelta(days=days)).isoformat()
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM history WHERE timestamp < ?', (since,))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error pruning history: {e}")
