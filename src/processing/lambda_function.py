import json
import urllib.parse
import boto3
import pandas as pd
import awswrangler as wr
from datetime import datetime, timezone

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    try:
        # 1. Extract the S3 Bucket and File Key from the trigger event
        source_bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
        
        print(f"📥 Processing incoming batch: s3://{source_bucket}/{key}")

        # 2. Download and read the raw JSON file from the Bronze layer
        response = s3_client.get_object(Bucket=source_bucket, Key=key)
        file_content = response['Body'].read().decode('utf-8')
        
        # Handle the JSON batch (Depending on your consumer, it's a JSON array or newline-delimited)
        try:
            data = json.loads(file_content)
        except json.JSONDecodeError:
            data = [json.loads(line) for line in file_content.strip().split('\n')]

        # 3. Convert to a Pandas DataFrame
        df = pd.DataFrame(data)

        # 4. Enforce Schema & Data Types (Data Quality Check)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['altitude_ft'] = df['altitude_ft'].astype(int)
        df['latitude'] = df['latitude'].astype(float)
        df['longitude'] = df['longitude'].astype(float)
        df['flight_id'] = df['flight_id'].astype(str)

        # 5. V2 UPGRADE: Add UTC partition columns explicitly to the DataFrame
        now = datetime.now(timezone.utc)
        df['year'] = now.strftime('%Y')
        df['month'] = now.strftime('%m')
        df['day'] = now.strftime('%d')
        
        print("🔀 Routing compressed Parquet file to Silver layer...")

        # 6. Write to the Silver Layer using AWS Data Wrangler
        wr.s3.to_parquet(
            df=df,
            path="s3://lat-skadi-lake-dev-a00475fc/silver/telemetry/",  
            dataset=True,                                               
            mode="append",                                              
            database="skadi_flight_intelligence",
            table="silver_telemetry",
            partition_cols=["year", "month", "day"]                    
        )
        
        print("✅ SUCCESS: Telemetry batch partitioned and registered in Glue.")
        return {
            'statusCode': 200,
            'body': json.dumps('Medallion architecture processing complete')
        }

    except Exception as e:
        print(f"❌ ERROR processing object {key} from bucket {source_bucket}. Exception: {e}")
        raise e