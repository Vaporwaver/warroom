import sqlite3
import os
import time
import json

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
    
    # Table for persistent alerts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        identifier TEXT PRIMARY KEY,
        source TEXT,
        text TEXT,
        keywords TEXT,
        timestamp REAL,
        sentiment TEXT,
        summary TEXT,
        simulated INTEGER,
        metadata TEXT,
        audio_path TEXT,
        video_path TEXT,
        status TEXT
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
    cursor.execute("DELETE FROM alerts")
    conn.commit()
    conn.close()

def save_alert(alert, status='pending'):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    
    # Serialize keywords and metadata
    kws_str = ",".join(alert.get("keywords", []))
    metadata_str = json.dumps(alert.get("metadata", {}))
    
    cursor.execute("""
    INSERT OR REPLACE INTO alerts (
        identifier, source, text, keywords, timestamp, sentiment, summary, 
        simulated, metadata, audio_path, video_path, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        alert["identifier"],
        alert["source"],
        alert["text"],
        kws_str,
        alert["timestamp"],
        alert["sentimiento"],
        alert["resumen"],
        1 if alert.get("simulated", False) else 0,
        metadata_str,
        alert.get("audio_path"),
        alert.get("video_path"),
        status
    ))
    conn.commit()
    conn.close()

def update_alert_status(identifier, status):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("UPDATE alerts SET status = ? WHERE identifier = ?", (status, identifier))
    conn.commit()
    conn.close()

def get_alerts_by_status(status):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT identifier, source, text, keywords, timestamp, sentiment, summary, 
           simulated, metadata, audio_path, video_path, status 
    FROM alerts WHERE status = ? ORDER BY timestamp DESC
    """, (status,))
    rows = cursor.fetchall()
    conn.close()
    
    alerts = []
    for r in rows:
        kws = [k.strip() for k in r[3].split(",") if k.strip()]
        try:
            meta = json.loads(r[8])
        except Exception:
            meta = {}
            
        alerts.append({
            "identifier": r[0],
            "source": r[1],
            "text": r[2],
            "keywords": kws,
            "timestamp": r[4],
            "sentimiento": r[5],
            "resumen": r[6],
            "simulated": bool(r[7]),
            "metadata": meta,
            "audio_path": r[9],
            "video_path": r[10],
            "status": r[11]
        })
    return alerts

def delete_alerts_by_status(status):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM alerts WHERE status = ?", (status,))
    conn.commit()
    conn.close()

def get_sentiment_counts(status='pending'):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("SELECT sentiment, COUNT(*) FROM alerts WHERE status = ? GROUP BY sentiment", (status,))
    rows = cursor.fetchall()
    conn.close()
    
    counts = {"Positivo": 0, "Neutral": 0, "Negativo": 0}
    for r in rows:
        if r[0] in counts:
            counts[r[0]] = r[1]
    return counts

def get_source_counts(status='pending'):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("SELECT source, COUNT(*) FROM alerts WHERE status = ? GROUP BY source", (status,))
    rows = cursor.fetchall()
    conn.close()
    return dict(rows)
