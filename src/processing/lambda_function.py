import urllib.parse
import awswrangler as wr
import pandas as pd
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    # 1. Extract the bucket name and file key from the S3 event trigger
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    
    logger.info(f"Processing new telemetry batch: s3://{bucket}/{key}")

    try:
        # 2. Read the raw JSON array from the Bronze layer into a Pandas DataFrame
        df = wr.s3.read_json(path=f"s3://{bucket}/{key}")
        
        # 3. Schema Enforcement & Data Cleaning 
        # Ensure altitude is always treated as a numeric value, handle missing data
        if 'altitude_ft' in df.columns:
            df['altitude_ft'] = pd.to_numeric(df['altitude_ft'], errors='coerce').fillna(0).astype(int)
        
        # Add a processing timestamp for auditing
        df['processed_at'] = pd.Timestamp.utcnow()

        # 4. Define the Silver layer destination
        # We replace 'bronze' with 'silver' and change the extension to .parquet
        silver_key = key.replace('bronze/', 'silver/').replace('.json', '.parquet')
        silver_path = f"s3://{bucket}/{silver_key}"

        # 5. Write the cleaned DataFrame to the Silver layer as a compressed Parquet file
        wr.s3.to_parquet(
            df=df,
            path=silver_path,
            dataset=False # Set to True later if we want to partition by date
        )
        
        logger.info(f"Successfully transformed and saved to: {silver_path}")
        return {'statusCode': 200, 'body': 'Transformation complete'}

    except Exception as e:
        logger.error(f"Error processing object {key} from bucket {bucket}. Error: {str(e)}")
        raise e