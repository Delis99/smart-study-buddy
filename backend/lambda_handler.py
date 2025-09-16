import boto3
import json

def lambda_handler(event, context):
    # Bedrock runtime client
    client = boto3.client("bedrock-runtime", region_name="us-east-1")

    # Get prompt from API request or default
    body = json.loads(event.get("body", "{}"))
    user_prompt = body.get("prompt", "Explain recursion in simple steps.")

    # Call Claude 3.5 Sonnet
    response = client.invoke_model(
        modelId="anthropic.claude-3-5-sonnet-20240620-v2:0",
        body=json.dumps({
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": user_prompt}]}
            ],
            "max_tokens": 300,
            "temperature": 0.7
        }),
        accept="application/json",
        contentType="application/json"
    )

    result = json.loads(response["body"].read())
    answer = result["output"]["content"][0]["text"]

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"answer": answer})
    }
