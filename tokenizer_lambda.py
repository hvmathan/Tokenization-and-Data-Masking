import boto3
import base64
import csv
import io
import os

s3 = boto3.client('s3')

def lambda_handler(event, context):
    print("Event received:", event)

    # Extract metadata file details
    metadata_key = event['Records'][0]['s3']['object']['key']
    print("Triggered by metadata file:", metadata_key)

    # Infer raw and output paths
    filename_base = os.path.basename(metadata_key).replace('_pii_fields.json', '')
    raw_key = f"raw/{filename_base}.csv"
    output_key = f"tokenized/{filename_base}_tokenized.csv"
    bucket = event['Records'][0]['s3']['bucket']['name']

    print(f"Looking for raw CSV: {raw_key}")
    print(f"Output will be written to: {output_key}")

    # Load metadata file (PII field list)
    metadata_obj = s3.get_object(Bucket=bucket, Key=metadata_key)
    metadata_content = metadata_obj['Body'].read().decode('utf-8-sig').strip()
    pii_fields = eval(metadata_content)
    print("PII Fields:", pii_fields)

    # Load CSV file
    raw_obj = s3.get_object(Bucket=bucket, Key=raw_key)
    raw_csv = raw_obj['Body'].read().decode('utf-8-sig')

    # Detect delimiter
    sniffer = csv.Sniffer()
    dialect = sniffer.sniff(raw_csv.splitlines()[0])
    delimiter = dialect.delimiter
    print(f"Detected delimiter: '{delimiter}'")

    input_stream = io.StringIO(raw_csv)
    output_stream = io.StringIO()

    reader = csv.DictReader(input_stream, delimiter=delimiter)
    writer = csv.DictWriter(output_stream, fieldnames=reader.fieldnames, delimiter=delimiter)
    writer.writeheader()

    for row in reader:
        for field in pii_fields:
            if field in row and row[field]:
                row[field] = base64.b64encode(row[field].encode()).decode()
        writer.writerow(row)

    # Upload tokenized CSV
    s3.put_object(Bucket=bucket, Key=output_key, Body=output_stream.getvalue().encode('utf-8'))
    print(f"✅ Tokenized file uploaded to: {output_key}")
