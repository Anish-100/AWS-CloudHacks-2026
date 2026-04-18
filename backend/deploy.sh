#!/bin/bash
set -e

REGION="us-east-1"
STACK="puran-dev"

# 1. deploy infra (safe to re-run, skips if nothing changed)
echo "deploying infra..."
aws cloudformation deploy \
  --template-file ../cloudformation.yaml \
  --stack-name $STACK \
  --capabilities CAPABILITY_NAMED_IAM \
  --region $REGION

# 2. package code
echo "packaging..."
rm -rf package deployment.zip
pip install -r requirements.txt -t package/ -q
cp main.py goals.py transactions.py csv_processor.py package/
cd package && zip -r ../deployment.zip . -q && cd ..

# 3. push to both lambdas
echo "deploying lambdas..."
aws lambda update-function-code --function-name puran-api-dev           --zip-file fileb://deployment.zip --region $REGION
aws lambda update-function-code --function-name puran-csv-processor-dev --zip-file fileb://deployment.zip --region $REGION

# 4. print the API URL for the frontend person
echo ""
echo "API URL:"
aws cloudformation describe-stacks --stack-name $STACK \
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
  --output text --region $REGION
