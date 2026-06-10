import sqlite3
import os
import time

DB_PATH = os.path.join(os.getcwd(), "db.sqlite")

def initialize_db():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    
    # Table for processed alerts (YouTube video IDs, Instagram post IDs)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processed_content (
        identifier TEXT PRIMARY KEY,
        source TEXT,
        scanned_at REAL,
        has_mention INTEGER
    )
    """)
    
    # Table for general persistent configuration/state (e.g. cooldown timestamps)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_state (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    conn.commit()
    conn.close()

def is_processed(identifier):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_content WHERE identifier = ?", (identifier,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_processed(identifier, source, has_mention=0):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO processed_content (identifier, source, scanned_at, has_mention)
    VALUES (?, ?, ?, ?)
    """, (identifier, source, time.time(), 1 if has_mention else 0))
    conn.commit()
    conn.close()

def get_state(key, default=None):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_state WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]
    return default

def set_state(key, value):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO system_state (key, value)
    VALUES (?, ?)
    """, (key, str(value)))
    conn.commit()
    conn.close()

def clear_cache_and_cooldowns():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM processed_content")
    cursor.execute("DELETE FROM system_state")
    conn.commit()
    conn.close()

