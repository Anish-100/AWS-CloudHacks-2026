#!/bin/bash
set -e

REGION="us-west-2"
ROLE="arn:aws:iam::133177652556:role/LambdaCSVIngestionRole"
LAMBDA_DIR="$(dirname "$0")/lambda"

deploy_lambda() {
    local name=$1
    local file=$2
    echo "Deploying $name..."
    zip -j /tmp/${name}.zip ${LAMBDA_DIR}/${file}
    if aws lambda get-function --function-name $name --region $REGION &>/dev/null; then
        aws lambda update-function-code \
            --function-name $name \
            --zip-file fileb:///tmp/${name}.zip \
            --region $REGION --query 'LastModified' --output text
    else
        aws lambda create-function \
            --function-name $name \
            --runtime python3.12 \
            --handler pipeline.lambda_handler \
            --role $ROLE \
            --zip-file fileb:///tmp/${name}.zip \
            --timeout 30 \
            --region $REGION --query 'FunctionName' --output text
    fi
}

# Deploy pipeline as Recommendations-handler
echo "Packaging pipeline..."
zip -j /tmp/Recommendations-handler.zip "$(dirname "$0")/Recommendations-handler.py"
if aws lambda get-function --function-name Recommendations-handler --region $REGION &>/dev/null; then
    aws lambda update-function-code \
        --function-name Recommendations-handler \
        --zip-file fileb:///tmp/Recommendations-handler.zip \
        --region $REGION --query 'LastModified' --output text
else
    aws lambda create-function \
        --function-name Recommendations-handler \
        --runtime python3.12 \
        --handler pipeline.lambda_handler \
        --role $ROLE \
        --zip-file fileb:///tmp/Recommendations-handler.zip \
        --timeout 30 \
        --region $REGION --query 'FunctionName' --output text
fi

deploy_lambda "GetGoals-handler"              "GetGoals-handler.py"
deploy_lambda "FinancialTransactions-handler" "FinancialTransactions-handler.py"
deploy_lambda "UserGoals-handler"             "UserGoals-handler.py"

echo ""
echo "All Lambdas deployed."
echo ""
echo "Test recommendations:"
echo "  aws lambda invoke --function-name Recommendations-handler --region $REGION --cli-binary-format raw-in-base64-out --payload '{\"body\":\"{\\\"user_id\\\":\\\"demo\\\",\\\"monthly_income\\\":4500}\"}' /tmp/out.json && cat /tmp/out.json"
