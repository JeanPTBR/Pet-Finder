import json


def health(event, context):
    body = {
        "message": "Go Serverless v4.0! Your function executed successfully!",
        "input": event,
    }

    response = {"statusCode": 200, "body": json.dumps(body), "headers": {"Content-Type": "application/json"}}

    return response


def v1_description(event, context):
    body = {
        "message": "API Pets version 1."
    }

    response = {"statusCode": 200, "body": json.dumps(body), "headers": {"Content-Type": "application/json"}}

    return response
