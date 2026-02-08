import sqlite3
from datetime import datetime, timedelta
import os

DB_FILE = os.path.join(os.getenv('DATA_DIR', '.'), 'miner_history.db')

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                hashrate REAL,
                dual_hashrate REAL DEFAULT 0,
                avg_temp REAL,
                avg_fan_speed REAL,
                total_power_draw REAL DEFAULT 0,
                accepted_shares INTEGER,
                rejected_shares INTEGER
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gpu_history (
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                gpu_index INTEGER,
                hashrate REAL,
                dual_hashrate REAL DEFAULT 0,
                temperature REAL,
                power_draw REAL,
                fan_speed REAL,
                accepted_shares INTEGER,
                rejected_shares INTEGER
            )
        ''')

        # Migrations for existing databases
        # 1. history table
        cursor.execute("PRAGMA table_info(history)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'dual_hashrate' not in columns:
            cursor.execute('ALTER TABLE history ADD COLUMN dual_hashrate REAL DEFAULT 0')
        if 'total_power_draw' not in columns:
            cursor.execute('ALTER TABLE history ADD COLUMN total_power_draw REAL DEFAULT 0')

        # 2. gpu_history table
        cursor.execute("PRAGMA table_info(gpu_history)")
        gpu_columns = [column[1] for column in cursor.fetchall()]
        if 'dual_hashrate' not in gpu_columns:
            cursor.execute('ALTER TABLE gpu_history ADD COLUMN dual_hashrate REAL DEFAULT 0')
        if 'power_draw' not in gpu_columns:
            cursor.execute('ALTER TABLE gpu_history ADD COLUMN power_draw REAL DEFAULT 0')

        conn.commit()

def log_history(hashrate, avg_temp, avg_fan_speed, accepted_shares, rejected_shares, dual_hashrate=0, total_power_draw=0, gpus=None):
    now = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO history (timestamp, hashrate, dual_hashrate, avg_temp, avg_fan_speed, total_power_draw, accepted_shares, rejected_shares)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (now, hashrate, dual_hashrate, avg_temp, avg_fan_speed, total_power_draw, accepted_shares, rejected_shares))

        if gpus:
            for gpu in gpus:
                cursor.execute('''
                    INSERT INTO gpu_history (timestamp, gpu_index, hashrate, dual_hashrate, temperature, power_draw, fan_speed, accepted_shares, rejected_shares)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    now,
                    gpu.get('index', 0),
                    gpu.get('hashrate', 0),
                    gpu.get('dual_hashrate', 0),
                    gpu.get('temperature', 0),
                    gpu.get('power_draw', 0),
                    gpu.get('fan_speed', 0),
                    gpu.get('accepted_shares', 0),
                    gpu.get('rejected_shares', 0)
                ))
        conn.commit()

def get_history(days=30):
    since = (datetime.now() - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, hashrate, dual_hashrate, avg_temp, avg_fan_speed, total_power_draw, accepted_shares, rejected_shares
            FROM history
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        ''', (since,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_gpu_history(gpu_index=None, days=30):
    since = (datetime.now() - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if gpu_index is not None:
            cursor.execute('''
                SELECT timestamp, gpu_index, hashrate, dual_hashrate, temperature, power_draw, fan_speed, accepted_shares, rejected_shares
                FROM gpu_history
                WHERE gpu_index = ? AND timestamp >= ?
                ORDER BY timestamp ASC
            ''', (gpu_index, since))
        else:
            cursor.execute('''
                SELECT timestamp, gpu_index, hashrate, dual_hashrate, temperature, power_draw, fan_speed, accepted_shares, rejected_shares
                FROM gpu_history
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
        cursor.execute('DELETE FROM gpu_history WHERE timestamp < ?', (since,))
        conn.commit()
