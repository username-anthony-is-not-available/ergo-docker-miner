import sqlite3
from datetime import datetime, timedelta
import os

DB_FILE = 'miner_history.db'

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                hashrate REAL,
                avg_temp REAL,
                avg_fan_speed REAL,
                accepted_shares INTEGER,
                rejected_shares INTEGER
            )
        ''')
        conn.commit()

def log_history(hashrate, avg_temp, avg_fan_speed, accepted_shares, rejected_shares):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO history (timestamp, hashrate, avg_temp, avg_fan_speed, accepted_shares, rejected_shares)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), hashrate, avg_temp, avg_fan_speed, accepted_shares, rejected_shares))
        conn.commit()

def get_history(days=30):
    since = (datetime.now() - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, hashrate, avg_temp, avg_fan_speed, accepted_shares, rejected_shares
            FROM history
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        ''', (since,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def prune_history(days=30):
    since = (datetime.now() - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM history WHERE timestamp < ?', (since,))
        conn.commit()
