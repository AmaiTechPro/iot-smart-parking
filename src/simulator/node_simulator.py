import argparse, datetime, random, sqlite3, sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import DB_PATH, LOT_ID, SLOT_IDS

def get_target_occupancy_probability(timestamp: datetime.datetime) -> float:
    hour = timestamp.hour + timestamp.minute / 60.0
    is_weekend = timestamp.weekday() >= 5
    if is_weekend:
        if 10.0 <= hour < 17.0: return 0.50
        elif 8.0 <= hour < 10.0 or 17.0 <= hour < 20.0: return 0.30
        else: return 0.05
    if 0.0 <= hour < 6.5: return 0.05
    elif 6.5 <= hour < 8.0: return 0.40
    elif 8.0 <= hour < 11.5: return 0.85
    elif 11.5 <= hour < 14.0: return 0.75
    elif 14.0 <= hour < 17.0: return 0.70
    elif 17.0 <= hour < 19.5: return 0.35
    elif 19.5 <= hour < 22.0: return 0.15
    else: return 0.05

def backfill_history(days: int):
    print(f"[SIMULATOR] Generating {days} days of telemetry for {SLOT_IDS}...")
    now = datetime.datetime.now().replace(second=0, microsecond=0)
    current_time = (now - datetime.timedelta(days=days)).replace(minute=0, second=0, microsecond=0)
    slot_states = {slot: 0 for slot in SLOT_IDS}
    records = []
    step = datetime.timedelta(minutes=5)
    
    while current_time < now:
        p_target = get_target_occupancy_probability(current_time)
        if p_target >= 0.80: desired_occupied = random.choice([6, 7, 7, 8])
        elif p_target >= 0.65: desired_occupied = random.choice([5, 6, 6, 7])
        elif p_target >= 0.35: desired_occupied = random.choice([2, 3, 3, 4])
        elif p_target >= 0.15: desired_occupied = random.choice([1, 1, 2])
        else: desired_occupied = 0 if random.random() < 0.80 else 1

        current_occupied = sum(slot_states.values())
        if current_occupied < desired_occupied:
            vacant = [s for s, state in slot_states.items() if state == 0]
            for slot_id in random.sample(vacant, min(len(vacant), desired_occupied - current_occupied)):
                slot_states[slot_id] = 1
        elif current_occupied > desired_occupied:
            occupied = [s for s, state in slot_states.items() if state == 1]
            for slot_id in random.sample(occupied, min(len(occupied), current_occupied - desired_occupied)):
                slot_states[slot_id] = 0

        iso_ts = current_time.isoformat()
        for slot_id, status in slot_states.items():
            records.append((iso_ts, f"NODE_{slot_id}", LOT_ID, slot_id, status, "SIMULATED"))
        current_time += step

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parking_events (
                timestamp TEXT, node_id TEXT, lot_id TEXT, slot_id TEXT, status INTEGER, source_type TEXT)
        """)
        cursor.executemany("INSERT INTO parking_events VALUES (?, ?, ?, ?, ?, ?)", records)
        conn.commit()
    print(f"[SIMULATOR] Backfilled {len(records)} events.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--backfill-days", type=int, default=14)
    args = parser.parse_args()
    backfill_history(args.backfill_days)