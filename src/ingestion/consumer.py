import json
from confluent_kafka import Consumer

# 1. Configure the connection to your local Kafka engine
conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'flight_tracker_group',
    'auto.offset.reset': 'earliest' # Read from the beginning of the stream
}

# 2. Initialize the Consumer and target the topic
consumer = Consumer(conf)
topic = 'flight-telemetry'
consumer.subscribe([topic])

print(f"🎧 Listening for live flight data on topic: '{topic}'...\n")

# 3. Create a continuous loop to check for new messages
try:
    while True:
        # Wait up to 1 second for a new message
        msg = consumer.poll(timeout=1.0) 

        if msg is None:
            continue
        if msg.error():
            print(f"⚠️ Consumer error: {msg.error()}")
            continue

        # Decode the raw bytes back into a readable Python dictionary
        record_value = msg.value().decode('utf-8')
        flight_data = json.loads(record_value)
        
        # Print the caught data using the correct dictionary keys
        print(f"✅ Flight Intercepted -> ID: {flight_data['flight_id']} | Alt: {flight_data.get('altitude_ft', 'N/A')}ft | Lat: {flight_data.get('latitude', 'N/A')} | Lon: {flight_data.get('longitude', 'N/A')}")

except KeyboardInterrupt:
    print("\n🛑 Stopping consumer...")
finally:
    # Always close the connection cleanly
    consumer.close()