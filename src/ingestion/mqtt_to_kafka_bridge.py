import json
import paho.mqtt.client as mqtt
from kafka import KafkaProducer

# 1. Configure the Destination (Kafka)
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)
KAFKA_TOPIC = "flight-telemetry"

# 2. Configure the Source (MQTT Radio Tower)
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "skadi/telemetry/live"

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("🟢 BRIDGE ONLINE: Connected to MQTT. Listening for UAV signals...")
        # The moment we connect, subscribe to the drone's channel
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"🔴 CONNECTION FAILED: {reason_code}")

def on_message(client, userdata, msg):
    # 1. Receive the lightweight MQTT message
    payload = json.loads(msg.payload.decode('utf-8'))
    altitude = payload.get("altitude_ft")
    
    # 2. Forward it into the heavy Kafka pipeline
    producer.send(KAFKA_TOPIC, payload)
    print(f"🌉 FORWARDED to Kafka: {payload['flight_id']} at {altitude} ft")

# 3. Initialize the Bridge
print("🏗️ Booting Edge Gateway (MQTT -> Kafka Bridge)...")
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="skadi_gateway_001")
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT)

# Keep the bridge running forever
try:
    client.loop_forever()
except KeyboardInterrupt:
    print("\n🛑 BRIDGE TERMINATED: Shutting down gateway...")
    client.disconnect()
    producer.close()