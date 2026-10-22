from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "parking_system.db"

MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883
MQTT_KEEP_ALIVE = 60

LOT_ID = "LOT_01"
# Automatically generate 20 slots: A01, A02 ... A20
SLOT_IDS = [f"A{str(i).zfill(2)}" for i in range(1, 21)]
SIMULATED_SLOTS = SLOT_IDS
TOTAL_SPOTS = len(SLOT_IDS)