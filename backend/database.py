import sqlite3
from datetime import datetime
import os

DB_NAME = os.path.join(os.path.dirname(__file__), "smart_parking.db")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS occupancy_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            bay_id TEXT,
            occupancy_status TEXT,
            distance_cm REAL,
            device_id TEXT,
            timestamp TEXT,
            received_at TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print(f"[DB] Initialized database table successfully.")

def insert_reading(data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    received_at = datetime.now().isoformat()
    record_timestamp = data.get("timestamp")
    
    if record_timestamp == "pending_backend_sync":
        record_timestamp = received_at
        
    cursor.execute('''
        INSERT INTO occupancy_readings 
        (project_id, bay_id, occupancy_status, distance_cm, device_id, timestamp, received_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get("project_id"), data.get("bay_id"), data.get("occupancy_status"),
        data.get("distance_cm"), data.get("device_id"), record_timestamp, received_at
    ))
    conn.commit()
    conn.close()
    print(f"  └── [DB] Successfully saved {data.get('bay_id')} status ({data.get('occupancy_status')}) to SQLite.")