import sqlite3
import datetime
import random
import sys
from pathlib import Path

# Ensure the script can find the config folder
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import DB_PATH, LOT_ID, SLOT_IDS

def get_current_state():
    """Reads the most recent state of all parking bays from the database."""
    state = {s: 0 for s in SLOT_IDS}
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            for slot in SLOT_IDS:
                cursor.execute(
                    "SELECT status FROM parking_events WHERE slot_id = ? ORDER BY timestamp DESC LIMIT 1", 
                    (slot,)
                )
                row = cursor.fetchone()
                if row:
                    state[slot] = row[0]
    except Exception as e:
        print(f"Database read error: {e}")
    return state

def set_occupancy(target: int):
    """Calculates arrivals/departures needed to hit the target and writes to DB."""
    # Cap target at max available slots (8)
    if target >= len(SLOT_IDS):
        target = len(SLOT_IDS)
        
    current_state = get_current_state()
    current_occupied = sum(current_state.values())
    
    if current_occupied == target:
        print(f"Lot is already at {target} occupied bays. No changes needed.")
        return

    records = []
    now = datetime.datetime.now().isoformat()
    
    if current_occupied < target:
        # Fill vacant bays
        vacant = [s for s, status in current_state.items() if status == 0]
        to_fill = target - current_occupied
        for slot in random.sample(vacant, to_fill):
            records.append((now, f"NODE_{slot}", LOT_ID, slot, 1, "CLI_DEMO"))
            print(f"🚗 Car ARRIVED at {slot}")
    else:
        # Vacate occupied bays
        occupied = [s for s, status in current_state.items() if status == 1]
        to_vacate = current_occupied - target
        for slot in random.sample(occupied, to_vacate):
            records.append((now, f"NODE_{slot}", LOT_ID, slot, 0, "CLI_DEMO"))
            print(f"💨 Car DEPARTED from {slot}")

    # Write the new events to the database
    if records:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT INTO parking_events (timestamp, node_id, lot_id, slot_id, status, source_type) VALUES (?, ?, ?, ?, ?, ?)", 
                records
            )
            conn.commit()
        print("✅ Database updated successfully! Refresh your Streamlit dashboard.")

def main():
    print("=" * 55)
    print(" 🎮 IoT Smart Parking - Interactive CLI Controller")
    print("=" * 55)
    print("Enter a number between 0 and 20 to set exact occupied bays.")
    print("Enter 20 to simulate a 100% full lot surge (all 20 bays).")
    print("Type 'q' to quit.")
    print("-" * 55)
    
    while True:
        try:
            val = input("\n[CLI] Enter target occupancy (0-20) > ").strip().lower()
            if val == 'q':
                print("Exiting CLI...")
                break
            
            target = int(val)
            if 0 <= target <= 20:
                set_occupancy(target)
            else:
                print("⚠️ Please enter a number between 0 and 20.")
        except ValueError:
            print("⚠️ Invalid input. Enter a number or 'q'.")
if __name__ == "__main__":
    main()