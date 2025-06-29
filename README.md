# PII Protection Serverless Pipeline

## The Real-World Problem

In 2017, Equifax suffered one of the worst data breaches in history, exposing the personal data of over 147 million people. The breach included names, Social Security numbers, dates of birth, and addresses. The aftermath? A $700 million penalty, irreparable reputational damage, and shattered customer trust. The root causes? A missed Apache patch, but more critically, a lack of layered, proactive data protection. Source : https://archive.epic.org/privacy/data-breach/equifax/

### What if...?

If even basic tokenization was applied to their sensitive data at the ingestion point, the stolen data would have been useless to attackers. That incident was the inspiration behind this PII Protection Serverless Pipeline.

## Project Goal

To build a lightweight, cost-effective, and automated pipeline to tokenize sensitive fields in uploaded CSVs, store tokenized results, optionally mask data for safe sharing, and allow detokenization when required.

## Architecture Overview

![image](https://github.com/user-attachments/assets/f6da56b4-50fb-4210-8ec8-5f17c34e82fd)



```
┌─────────────────┐    ┌───────────────────┐    ┌─────────────────┐
│  Raw CSV Upload │───▶│  PII Detector     │───▶│   Metadata      │
│   (S3 /raw)     │    │     Lambda        │    │  (S3 /metadata) │
└─────────────────┘    └───────────────────┘    └─────────────────┘
                                                           │
                                                           ▼
┌─────────────────┐    ┌───────────────────┐    ┌─────────────────┐
│   Detokenized   │◀───│   Detokenizer     │◀───│   Tokenizer     │
│  (S3 /detok)    │    │     Lambda        │    │     Lambda      │
└─────────────────┘    └───────────────────┘    └─────────────────┘
                                                           │
                                                           ▼
                                                ┌─────────────────┐
                                                │   Tokenized     │
                                                │ (S3 /tokenized) │
                                                └─────────────────┘
```

## S3 Bucket Structure

The pipeline uses a well-organized S3 bucket structure for different stages of data processing:

```
pii-project-harsha/
├── raw/                      # Original CSV files with PII data
│   └── customer_data.csv
├── metadata/                 # JSON files containing PII field information
│   └── customer_data_pii_fields.json
├── tokenized/               # CSV files with Base64 tokenized PII data
│   └── customer_data_tokenized.csv
└── detokenized/            # CSV files with decoded and optionally masked data
    └── customer_data_detokenized.csv
```
![image](https://github.com/user-attachments/assets/65ad941c-b428-495f-8121-385b978a5ebe)


## Lambda Functions

This serverless pipeline consists of 3 core Lambda functions:

### 1. `pii_detector_lambda.py`
- **Trigger**: S3 PUT events in the `/raw` folder
- **Purpose**: Identifies PII fields in uploaded CSV files
- **Output**: Creates metadata JSON files in `/metadata` folder
- **Technology**: Uses pattern matching and field name analysis to detect PII

### 2. `tokenizer_lambda.py`
- **Trigger**: S3 PUT events in the `/metadata` folder
- **Purpose**: Tokenizes identified PII fields using Base64 encoding
- **Input**: Raw CSV + metadata JSON
- **Output**: Tokenized CSV in `/tokenized` folder
- **Logic**: Replaces PII values with `TOKEN_1`, `TOKEN_2`, etc.

### 3. `detokenizer_lambda.py`
- **Trigger**: S3 PUT events in the `/tokenized` folder (optional)
- **Purpose**: Decodes tokenized data and optionally applies masking
- **Features**: 
  - Automatic CSV delimiter detection
  - Configurable masking (enabled/disabled via `masking_enabled` flag)
  - Field-specific masking patterns for names, emails, and phone numbers
- **Output**: Detokenized/masked CSV in `/detokenized` folder

![image](https://github.com/user-attachments/assets/dcfdcba6-530d-4867-b7dd-4d5b32f883fb)


## How the Pipeline Works — End-to-End Flow

### Step 1: CSV Upload to `/raw` Folder
The process begins when a raw CSV containing potential PII fields is uploaded to the S3 bucket's `raw/` folder.

### Step 2: PII Detection
- The `pii_detector_lambda` is automatically triggered by the S3 upload event
- It analyzes the CSV headers and content to identify PII fields
- Creates a metadata JSON file listing the detected PII columns
- Saves this metadata to the `metadata/` folder

### Step 3: Tokenization
- The metadata upload triggers the `tokenizer_lambda`
- Reads the original CSV and the PII fields metadata
- Tokenizes sensitive fields using a simple token counter (`TOKEN_1`, `TOKEN_2`, etc.)
- Stores the tokenized CSV in the `tokenized/` folder

### Step 4: Detokenization (Optional)
- If detokenization is needed, the `detokenizer_lambda` is triggered
- Decodes the Base64 tokens back to original values
- Optionally applies field-specific masking for safe viewing
- Saves the result in the `detokenized/` folder

### Step 5: Access Control
Only specific IAM roles or users are granted access to the `detokenized/` folder, ensuring strict separation of duties and compliance with least-privilege principles.

## Tokenization Logic

The pipeline uses Base64 encoding for tokenization, providing reversibility ideal for MVPs:

```python
import base64

# Encoding (tokenization)
original_value = "John Doe"
token = base64.b64encode(original_value.encode()).decode()
# Output: "Sm9obiBEb2U="

# Decoding (detokenization)
decoded_value = base64.b64decode(token).decode()
# Output: "John Doe"
```

### Pros:
- ✅ Reversible for trusted internal workflows
- ✅ Lightweight and fast
- ✅ Easy to implement with standard libraries
- ✅ No external dependencies

### Cons:
- ❌ Not cryptographically secure
- ❌ Easily decodable if token format is known
- ❌ Not suitable for production without additional encryption layers

## Masking Features

The detokenizer includes intelligent masking capabilities:

### Name Masking
```python
"John Doe" → "J*** D**"
```

### Email Masking
```python
"john@example.com" → "j**n@example.com"
```

### Phone Masking
```python
"9876543210" → "******3210"
```

## Sample Data Flow

### Input: Raw CSV (`raw/customer_data.csv`)
```csv
Name,Email,Phone,DOB,TransactionID
John Doe,john@example.com,9876543210,1990-01-01,TXN1001
Jane Smith,jane@gmail.com,9123456789,1991-03-22,TXN1002
```

### Metadata: PII Fields (`metadata/customer_data_pii_fields.json`)
```json
["Name", "Email", "Phone"]
```

### Tokenized Output (`tokenized/customer_data_tokenized.csv`)
```csv
Name,Email,Phone,DOB,TransactionID
TOKEN_1,TOKEN_2,TOKEN_3,1990-01-01,TXN1001
TOKEN_4,TOKEN_5,TOKEN_6,1991-03-22,TXN1002
```

### Detokenized with Masking (`detokenized/customer_data_detokenized.csv`)
```csv
Name,Email,Phone,DOB,TransactionID
J*** D**,j**n@example.com,******3210,1990-01-01,TXN1001
J*** S****,j**e@gmail.com,******6789,1991-03-22,TXN1002
```

## Project Structure

```
pii-protection-serverless/
├── lambdas/
│   ├── pii_detector_lambda.py     # Identifies PII fields in CSV files
│   ├── tokenizer_lambda.py        # Tokenizes PII data using Base64
│   └── detokenizer_lambda.py      # Decodes tokens and applies masking
├── python/                        # Dependencies layer
│   ├── cryptography/              # Cryptography library
│   ├── cffi/                      # CFFI dependency  
│   └── pycparser/                 # Parser dependency
├── sample-data/
│   └── customer_data.csv          # Sample CSV for testing
├── cryptography-layer.zip         # Lambda layer for dependencies
└── README.md                      # This documentation
```

## Getting Started

### Prerequisites
- AWS Account with appropriate permissions
- AWS CLI configured
- Python 3.8 or higher
- boto3 library

### Deployment Steps

1. **Create S3 Bucket**
   ```bash
   aws s3 mb s3://your-pii-project-bucket
   ```

2. **Create Folder Structure**
   ```bash
   aws s3api put-object --bucket your-pii-project-bucket --key raw/
   aws s3api put-object --bucket your-pii-project-bucket --key metadata/
   aws s3api put-object --bucket your-pii-project-bucket --key tokenized/
   aws s3api put-object --bucket your-pii-project-bucket --key detokenized/
   ```

3. **Deploy Lambda Layer**
   - Upload `cryptography-layer.zip` as a Lambda layer
   - Note the layer ARN for Lambda function configuration

4. **Deploy Lambda Functions**
   
   For each Lambda function:
   ```bash
   # Package the function
   zip -r pii_detector_lambda.zip pii_detector_lambda.py
   
   # Create the function
   aws lambda create-function \
     --function-name pii-detector \
     --runtime python3.9 \
     --handler pii_detector_lambda.lambda_handler \
     --zip-file fileb://pii_detector_lambda.zip \
     --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-s3-role \
     --layers arn:aws:lambda:region:account:layer:crypto-layer:1
   ```

5. **Configure S3 Event Triggers**
   
   Create S3 event notifications for each folder:
   ```json
   {
     "Rules": [
       {
         "Name": "trigger-pii-detector",
         "Filter": { "Key": { "FilterRules": [{ "Name": "prefix", "Value": "raw/" }] } },
         "Status": "Enabled",
         "Targets": [{ "Arn": "arn:aws:lambda:region:account:function:pii-detector" }]
       }
     ]
   }
   ```

6. **Test the Pipeline**
   ```bash
   # Upload a test CSV file
   aws s3 cp sample-data/customer_data.csv s3://your-bucket/raw/
   
   # Monitor CloudWatch logs
   aws logs describe-log-groups --log-group-name-prefix /aws/lambda/
   ```

## Configuration

### Environment Variables

Set these environment variables for your Lambda functions:

```bash
# For all functions
S3_BUCKET=your-pii-project-bucket
LOG_LEVEL=INFO

# For detokenizer function
MASKING_ENABLED=true  # Set to false to disable masking
```

### IAM Permissions

Your Lambda execution role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::your-pii-project-bucket/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

## Monitoring and Logging

### CloudWatch Metrics
- Lambda execution duration and errors
- S3 object count per folder
- Custom metrics for tokenization operations

### Logging Strategy
- All functions use structured logging with emoji indicators
- ✅ Success operations
- ❌ Error conditions
- 📊 Processing statistics

### Example Log Output
```
✅ Tokenized file uploaded to: tokenized/customer_data_tokenized.csv
❌ Failed to decode field Name: Invalid base64 encoding
📊 Processed 1000 records with 15 PII fields
```

## Security Considerations

### Data Protection
- **Encryption in Transit**: All S3 operations use HTTPS
- **Access Control**: IAM policies restrict folder access
- **Audit Trail**: CloudTrail logs all S3 and Lambda activities
- **Data Retention**: Implement S3 lifecycle policies for automatic cleanup

### Best Practices
- Use separate IAM roles for each Lambda function
- Enable S3 bucket versioning for data recovery
- Implement S3 bucket policies to prevent public access
- Regular security audits of IAM permissions

### Compliance Considerations
- The pipeline supports GDPR "right to be forgotten" through detokenization
- Audit trails provide compliance reporting capabilities
- Data lineage tracking through S3 object metadata

## Cost Optimization

### Serverless Benefits
- **Pay-per-use**: Only charged when processing files
- **Auto-scaling**: Handles variable workloads automatically
- **No idle costs**: No charges when not processing data

### Cost Estimation (Monthly)
- Lambda executions: $0.20 per 1M requests
- S3 storage: $0.023 per GB
- Data transfer: Minimal for internal processing
- **Total estimated cost**: <$10/month for typical workloads

## Performance Characteristics

### Processing Speed
- Small files (<1MB): ~2-3 seconds end-to-end
- Medium files (1-10MB): ~5-15 seconds
- Large files (>10MB): Consider chunking for optimal performance

### Scalability
- Concurrent Lambda executions: Up to 1000 (default limit)
- S3 throughput: Virtually unlimited
- Bottlenecks: Lambda cold starts (~1-2 seconds)

## Troubleshooting

### Common Issues

1. **Lambda timeout errors**
   - Increase timeout setting (default: 3 seconds)
   - Consider breaking large files into chunks

2. **Permission denied errors**
   - Verify IAM role has S3 access
   - Check bucket policies

3. **Base64 decode errors**
   - Ensure tokens weren't corrupted during processing
   - Verify character encoding consistency

### Debug Commands
```bash
# Check S3 object metadata
aws s3api head-object --bucket your-bucket --key path/to/file.csv

# View Lambda logs
aws logs filter-log-events --log-group-name /aws/lambda/your-function

# Test Lambda function
aws lambda invoke --function-name your-function --payload '{}' response.json
```

## Future Enhancements

### Short Term
- [ ] Support for additional file formats (JSON, XML, Parquet)
- [ ] Enhanced PII detection using regex patterns
- [ ] Custom masking rules per field type
- [ ] Batch processing for multiple files

### Medium Term
- [ ] Integration with AWS KMS for stronger encryption
- [ ] Machine learning-based PII detection using Amazon Comprehend
- [ ] Real-time streaming data processing with Kinesis
- [ ] REST API for programmatic access

### Long Term
- [ ] Integration with data catalogs (AWS Glue)
- [ ] Compliance reporting dashboard
- [ ] Multi-region deployment support
- [ ] Advanced analytics on PII patterns

## Key Learnings

- **Serverless architectures** can be both powerful and lightweight for data processing
- **Event-driven design** enables seamless automation without complex orchestration
- **Tokenization** provides effective privacy protection even with simple techniques
- **Separation of concerns** through folder-based organization improves security
- **Base64 encoding** is sufficient for MVPs but requires enhancement for production

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code style
- Add unit tests for new features
- Update documentation for any changes
- Test with sample data before submitting

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by the need for better data protection following major security breaches like Equifax
- Built as part of exploring Generative AI and Serverless Pipelines in real-world scenarios
- Thanks to the AWS community for serverless best practices

---

## Contact

**Author**: Harsha Mathan

---

*This project demonstrates the power of serverless architectures in building cost-effective, scalable data protection solutions. If you found this helpful, please ⭐ the repository and share your feedback!*
