import boto3
import json
import os
import uuid

s3 = boto3.client('s3')
BUCKET = os.environ['UPLOAD_BUCKET']
EXPIRY = int(os.environ.get('PRESIGN_EXPIRY', 300))


def lambda_handler(event, context):
    params = event.get('queryStringParameters') or {}
    file_name = params.get('fileName', 'finance.csv')
    content_type = params.get('contentType', 'text/csv')
    dataset_id = params.get('datasetId', os.environ.get('USER_ID', 'demo'))
    batch_id = str(uuid.uuid4())
    key = f"{dataset_id}/{batch_id}/{file_name}"

    upload_url = s3.generate_presigned_url(
        'put_object',
        Params={'Bucket': BUCKET, 'Key': key},
        ExpiresIn=EXPIRY,
    )

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'uploadUrl': upload_url, 'batchId': batch_id, 'key': key}),
    }
