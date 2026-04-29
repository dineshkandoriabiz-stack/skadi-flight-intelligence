import json
import time
import random
from datetime import datetime
from confluent_kafka import Producer

KAFKA_CONFIG = {'bootstrap.servers': 'localhost:9092'}
TOPIC_NAME = 'flight-telemetry'

def delivery_report(err, msg):
    if err is not None:
        print(f"Failed: {err}")
    else:
        print(f"Telemetry sent to {msg.topic()}")

def generate_flight_data():
    return {
        "flight_id": "SKADI-001",
        "timestamp": datetime.utcnow().isoformat(),
        "latitude": round(random.uniform(-90.0, 90.0), 4),
        "longitude": round(random.uniform(-180.0, 180.0), 4),
        "altitude_ft": random.randint(10000, 40000),
        "speed_knots": random.randint(400, 550)
    }

def start_streaming():
    producer = Producer(KAFKA_CONFIG)
    try:
        while True:
            data = generate_flight_data()
            producer.produce(TOPIC_NAME, value=json.dumps(data).encode('utf-8'), on_delivery=delivery_report)
            producer.poll(0)
            time.sleep(2)
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        producer.flush()

if __name__ == "__main__":
    start_streaming()