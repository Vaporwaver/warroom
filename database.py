import sqlite3
import os
import time
import json
import threading

DB_PATH = os.path.join(os.getcwd(), "db.sqlite")

db_lock = threading.Lock()

def with_db_lock(func):
    def wrapper(*args, **kwargs):
        with db_lock:
            return func(*args, **kwargs)
    return wrapper

@with_db_lock
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
    
    # Create clients table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        email TEXT,
        keywords TEXT,
        description TEXT,
        enabled INTEGER DEFAULT 1
    )
    """)
    
    # Migration for clients: check if enabled column exists
    cursor.execute("PRAGMA table_info(clients)")
    columns = [info[1] for info in cursor.fetchall()]
    if "enabled" not in columns:
        cursor.execute("ALTER TABLE clients ADD COLUMN enabled INTEGER DEFAULT 1")
        conn.commit()
    
    # Seed default client if empty
    cursor.execute("SELECT COUNT(*) FROM clients")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO clients (name, email, keywords, description, enabled)
        VALUES (?, ?, ?, ?, 1)
        """, ("Cliente General", "", "", "Monitoreo general de noticias y relaciones públicas."))
        conn.commit()

    # Check if alerts table needs migration (check if it exists and has client_id column)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alerts'")
    alerts_exists = cursor.fetchone() is not None
    
    has_client_id = False
    if alerts_exists:
        cursor.execute("PRAGMA table_info(alerts)")
        columns = [info[1] for info in cursor.fetchall()]
        if "client_id" in columns:
            has_client_id = True
            
    if alerts_exists and not has_client_id:
        # Migration is needed!
        # 1. Rename existing alerts table
        cursor.execute("ALTER TABLE alerts RENAME TO old_alerts")
        
        # 2. Create the new alerts table
        cursor.execute("""
        CREATE TABLE alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            identifier TEXT,
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
            status TEXT,
            UNIQUE(client_id, identifier)
        )
        """)
        
        # 3. Copy existing alerts assigning client_id = 1 (Cliente General)
        cursor.execute("""
        INSERT OR IGNORE INTO alerts (
            client_id, identifier, source, text, keywords, timestamp, sentiment, summary,
            simulated, metadata, audio_path, video_path, status
        )
        SELECT 1, identifier, source, text, keywords, timestamp, sentiment, summary,
               simulated, metadata, audio_path, video_path, status
        FROM old_alerts
        """)
        
        # 4. Drop the old table
        cursor.execute("DROP TABLE old_alerts")
        conn.commit()
    else:
        # Table doesn't exist, create it from scratch
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            identifier TEXT,
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
            status TEXT,
            UNIQUE(client_id, identifier)
        )
        """)
        conn.commit()
        
    conn.close()

@with_db_lock
def is_processed(identifier):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_content WHERE identifier = ?", (identifier,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

@with_db_lock
def mark_processed(identifier, source, has_mention=0):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO processed_content (identifier, source, scanned_at, has_mention)
    VALUES (?, ?, ?, ?)
    """, (identifier, source, time.time(), 1 if has_mention else 0))
    conn.commit()
    conn.close()

@with_db_lock
def get_state(key, default=None):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_state WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]
    return default

@with_db_lock
def set_state(key, value):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO system_state (key, value)
    VALUES (?, ?)
    """, (key, str(value)))
    conn.commit()
    conn.close()

@with_db_lock
def clear_cache_and_cooldowns():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM processed_content")
    cursor.execute("DELETE FROM system_state")
    cursor.execute("DELETE FROM alerts")
    conn.commit()
    conn.close()

@with_db_lock
def save_alert(alert, client_id, status='pending'):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    
    # Serialize keywords and metadata
    kws_str = ",".join(alert.get("keywords", []))
    metadata_str = json.dumps(alert.get("metadata", {}))
    
    cursor.execute("""
    INSERT OR REPLACE INTO alerts (
        client_id, identifier, source, text, keywords, timestamp, sentiment, summary, 
        simulated, metadata, audio_path, video_path, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        client_id,
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

@with_db_lock
def update_alert_status(client_id, identifier, status):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("UPDATE alerts SET status = ? WHERE client_id = ? AND identifier = ?", (status, client_id, identifier))
    conn.commit()
    conn.close()

@with_db_lock
def get_alerts_by_status(status, client_id):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT identifier, source, text, keywords, timestamp, sentiment, summary, 
           simulated, metadata, audio_path, video_path, status 
    FROM alerts WHERE status = ? AND client_id = ? ORDER BY timestamp DESC
    """, (status, client_id))
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

@with_db_lock
def delete_alerts_by_status(status, client_id):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM alerts WHERE status = ? AND client_id = ?", (status, client_id))
    conn.commit()
    conn.close()

@with_db_lock
def get_sentiment_counts(status='pending', client_id=None):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    if client_id is not None:
        cursor.execute("SELECT sentiment, COUNT(*) FROM alerts WHERE status = ? AND client_id = ? GROUP BY sentiment", (status, client_id))
    else:
        cursor.execute("SELECT sentiment, COUNT(*) FROM alerts WHERE status = ? GROUP BY sentiment", (status,))
    rows = cursor.fetchall()
    conn.close()
    
    counts = {"Positivo": 0, "Neutral": 0, "Negativo": 0}
    for r in rows:
        if r[0] in counts:
            counts[r[0]] = r[1]
    return counts

@with_db_lock
def get_source_counts(status='pending', client_id=None):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    if client_id is not None:
        cursor.execute("SELECT source, COUNT(*) FROM alerts WHERE status = ? AND client_id = ? GROUP BY source", (status, client_id))
    else:
        cursor.execute("SELECT source, COUNT(*) FROM alerts WHERE status = ? GROUP BY source", (status,))
    rows = cursor.fetchall()
    conn.close()
    return dict(rows)

@with_db_lock
def get_processed_counts():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    
    # Instagram count
    cursor.execute("SELECT COUNT(*) FROM processed_content WHERE source = 'instagram'")
    ig_count = cursor.fetchone()[0]
    
    # RSS count
    cursor.execute("SELECT COUNT(*) FROM processed_content WHERE source LIKE 'rss_%'")
    rss_count = cursor.fetchone()[0]
    
    # YouTube count
    cursor.execute("SELECT COUNT(*) FROM processed_content WHERE source LIKE 'youtube_%'")
    yt_count = cursor.fetchone()[0]
    
    conn.close()
    return {
        "instagram": ig_count,
        "rss": rss_count,
        "youtube": yt_count
    }

# --- Clients CRUD functions ---

@with_db_lock
def get_all_clients():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, keywords, description, enabled FROM clients ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    
    clients = []
    for r in rows:
        clients.append({
            "id": r[0],
            "name": r[1],
            "email": r[2],
            "keywords": r[3],
            "description": r[4],
            "enabled": r[5]
        })
    return clients

@with_db_lock
def update_client_enabled(client_id, enabled):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("UPDATE clients SET enabled = ? WHERE id = ?", (enabled, client_id))
    conn.commit()
    conn.close()

@with_db_lock
def save_client(client_id, name, email, keywords, description):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    if client_id is None:
        cursor.execute("""
        INSERT INTO clients (name, email, keywords, description)
        VALUES (?, ?, ?, ?)
        """, (name, email, keywords, description))
    else:
        cursor.execute("""
        UPDATE clients SET name = ?, email = ?, keywords = ?, description = ?
        WHERE id = ?
        """, (name, email, keywords, description, client_id))
    conn.commit()
    conn.close()

@with_db_lock
def delete_client(client_id):
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    cursor.execute("DELETE FROM alerts WHERE client_id = ?", (client_id,))
    conn.commit()
    conn.close()

@with_db_lock
def reset_entire_database():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM processed_content")
    cursor.execute("DELETE FROM alerts")
    cursor.execute("DELETE FROM clients")
    # Preserve config_%, smtp_config and github_token, delete others
    cursor.execute("""
    DELETE FROM system_state 
    WHERE key NOT LIKE 'config_%' AND key != 'smtp_config' AND key != 'github_token'
    """)
    # Re-seed default client
    cursor.execute("""
    INSERT INTO clients (id, name, email, keywords, description, enabled)
    VALUES (1, ?, ?, ?, ?, 1)
    """, ("Cliente General", "", "", "Monitoreo general de noticias y relaciones públicas."))
    conn.commit()
    conn.close()
