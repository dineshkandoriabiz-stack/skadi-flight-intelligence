import json
import time
import random
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

# 1. Configure the Radio Transmitter (MQTT Client)
BROKER_ADDRESS = "localhost" # Pointing to your Docker container
PORT = 1883
TOPIC = "skadi/telemetry/live"

# V2 requires 'reason_code' and 'properties' in the signature
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("🟢 LINK ESTABLISHED: Connected to Mosquitto MQTT Broker")
    else:
        print(f"🔴 LINK FAILED: Return code {reason_code}")

# 2. Initialize the UAV Flight Controller
print("🚁 Booting SKADI-001 Flight Controller...")

# V2 requires explicitly passing the Callback API version
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="skadi_001_sensor")
client.on_connect = on_connect
client.connect(BROKER_ADDRESS, PORT)

client.loop_start() # Start the network loop in the background

# 3. Simulate Flight & Transmit Data
try:
    altitude = 500
    while True:
        # Generate slightly fluctuating telemetry
        altitude += random.randint(-10, 20)
        
        payload = {
            "flight_id": "SKADI-001",
            "altitude_ft": altitude,
            "latitude": 34.0522 + random.uniform(-0.01, 0.01),
            "longitude": -118.2437 + random.uniform(-0.01, 0.01),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Transmit (Publish) the data to the radio tower
        client.publish(TOPIC, json.dumps(payload), qos=1)
        print(f"📡 TRANSMITTED: Alt {altitude} ft")
        
        time.sleep(1) # Ping every 1 second

except KeyboardInterrupt:
    print("\n🛑 FLIGHT TERMINATED: Disconnecting radio...")
    client.loop_stop()
    client.disconnect()