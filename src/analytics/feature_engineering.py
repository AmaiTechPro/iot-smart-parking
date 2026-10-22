import sqlite3
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import DB_PATH, TOTAL_SPOTS

def engineer_features():
    print("[PIPELINE] Loading raw events from SQLite...")
    with sqlite3.connect(DB_PATH) as conn:
        raw_df = pd.read_sql("SELECT * FROM parking_events", conn)
    
    raw_df["timestamp"] = pd.to_datetime(raw_df["timestamp"])
    pivoted = raw_df.pivot_table(index="timestamp", columns="slot_id", values="status", aggfunc="last")
    
    full_timeline = pivoted.resample("1min").ffill().fillna(0)
    full_timeline["total_occupied"] = full_timeline.sum(axis=1)
    
    hourly = full_timeline[["total_occupied"]].resample("1h").mean()
    hourly["occupancy_rate"] = hourly["total_occupied"] / TOTAL_SPOTS
    
    hourly["hour_of_day"] = hourly.index.hour
    hourly["day_of_week"] = hourly.index.dayofweek
    hourly["is_weekend"] = (hourly["day_of_week"] >= 5).astype(int)
    
    hourly["sin_hour"] = np.sin(2 * np.pi * hourly["hour_of_day"] / 24)
    hourly["cos_hour"] = np.cos(2 * np.pi * hourly["hour_of_day"] / 24)
    
    hourly["lag_1h"] = hourly["occupancy_rate"].shift(1)
    hourly["lag_2h"] = hourly["occupancy_rate"].shift(2)
    hourly["lag_24h"] = hourly["occupancy_rate"].shift(24)
    hourly["rolling_3h_mean"] = hourly["occupancy_rate"].rolling(window=3).mean()
    
    hourly["target_next_hour"] = hourly["occupancy_rate"].shift(-1)
    hourly = hourly.dropna()
    
    with sqlite3.connect(DB_PATH) as conn:
        hourly.to_sql("lot_occupancy_hourly", conn, if_exists="replace", index=True, index_label="interval_start")
    
    print(f"[PIPELINE] Dataset ready with shape: {hourly.shape}")

if __name__ == "__main__":
    engineer_features()