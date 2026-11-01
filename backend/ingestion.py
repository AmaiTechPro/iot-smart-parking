import json
import paho.mqtt.client as mqtt
import database

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "dekut/iotds/smartparking/GROUP_10/telemetry"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"\n[MQTT] Successfully connected to {MQTT_BROKER}")
        client.subscribe(MQTT_TOPIC)
        print(f"[MQTT] Subscribed to topic: {MQTT_TOPIC}\nWaiting for ESP32 sensor data...\n")
    else:
        print(f"[MQTT] Connection failed with error code {rc}")

def on_message(client, userdata, msg):
    payload = msg.payload.decode('utf-8')
    print(f"[MQTT] Incoming data on {msg.topic}:\n  ├── Payload: {payload}")
    try:
        data = json.loads(payload)
        if data.get("project_id") == "smart_parking":
            database.insert_reading(data)
    except Exception as e:
        print(f"  └── [ERROR] Processing failure: {e}")

if __name__ == "__main__":
    print("=== Smart Parking Ingestion Service Starting ===")
    database.init_db()
    client = mqtt.Client(client_id="DeKUT_Python_Backend")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Ingestion service shut down.")