import json
import uuid
import boto3
from datetime import datetime, UTC
from confluent_kafka import Consumer

# --- CONFIGURATION ---
S3_BUCKET = 'lat-skadi-lake-dev-a00475fc'
S3_FOLDER = 'bronze/telemetry/'
BATCH_SIZE = 5  # Collect 5 records before uploading

# Initialize AWS S3 Client
s3_client = boto3.client('s3', region_name='ap-southeast-2')

# Kafka Configuration
conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'flight_tracker_s3_loader',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(conf)
topic = 'flight-telemetry'
consumer.subscribe([topic])

print(f"🎧 Listening on '{topic}' and forwarding to S3 Bucket: {S3_BUCKET}...\n")

def upload_to_s3(batch_data):
    """Saves the batch to S3 as a JSON file."""
    # Create a unique filename based on the current time
    timestamp = datetime.now(UTC).strftime('%Y%m%d_%H%M%S')
    file_name = f"{S3_FOLDER}batch_{timestamp}_{uuid.uuid4().hex[:6]}.json"
    
    # Convert the list of dictionaries to a JSON string
    json_data = json.dumps(batch_data)
    
    # Upload directly to S3 from memory
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=file_name,
        Body=json_data
    )
    print(f"☁️ SUCCESS: Uploaded batch of {len(batch_data)} records to s3://{S3_BUCKET}/{file_name}")

# --- MAIN LOOP ---
current_batch = []

try:
    while True:
        msg = consumer.poll(timeout=1.0) 

        if msg is None:
            continue
        if msg.error():
            print(f"⚠️ Consumer error: {msg.error()}")
            continue

        # Decode and append to our current batch
        record_value = msg.value().decode('utf-8')
        flight_data = json.loads(record_value)
        current_batch.append(flight_data)
        
        print(f"📥 Buffered -> ID: {flight_data['flight_id']} | Alt: {flight_data.get('altitude_ft', 'N/A')}ft (Batch: {len(current_batch)}/{BATCH_SIZE})")

        # If the batch is full, upload it and clear the list!
        if len(current_batch) >= BATCH_SIZE:
            upload_to_s3(current_batch)
            current_batch = [] # Reset for the next batch

except KeyboardInterrupt:
    print("\n🛑 Stopping consumer...")
    # Upload any leftover records before shutting down
    if len(current_batch) > 0:
        print("Uploading final partial batch...")
        upload_to_s3(current_batch)
finally:
    consumer.close()