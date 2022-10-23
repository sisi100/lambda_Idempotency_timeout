import os

import aws_cdk as cdk
from aws_cdk import Duration, RemovalPolicy
from aws_cdk.aws_dynamodb import Attribute, AttributeType, BillingMode, Table
from aws_cdk.aws_lambda import Code, Function, LayerVersion, Runtime
from aws_cdk.aws_lambda_event_sources import SqsEventSource
from aws_cdk.aws_sqs import Queue

app = cdk.App()
stack = cdk.Stack(app, "lambda-idempotency-timeout-stack")


# 冪等性に利用するテーブルを作成する
table = Table(
    stack,
    f"Table",
    partition_key=Attribute(name="id", type=AttributeType.STRING),
    time_to_live_attribute="expiration",
    billing_mode=BillingMode.PAY_PER_REQUEST,
    removal_policy=RemovalPolicy.DESTROY,
)

# Lambda本体
LAMBDA_POWERTOOLS_LAYER_ARN = (
    f"arn:aws:lambda:{os.getenv('CDK_DEFAULT_REGION')}:017000801446:layer:AWSLambdaPowertoolsPython:39"
)
powertools_layer = LayerVersion.from_layer_version_arn(stack, "powertoolsLayer", LAMBDA_POWERTOOLS_LAYER_ARN)
function = Function(
    stack,
    "Function",
    handler="app.handler",
    layers=[powertools_layer],
    code=Code.from_asset("runtime"),
    runtime=Runtime.PYTHON_3_9,
    environment={
        "TABLE_NAME": table.table_name,
        "RAISE_EXCEPTION": "False",  # False以外の文字列だったらERRORを出す想定
    },
)
table.grant_read_write_data(function)


# Lambdaをキックする用途のSQS
queue = Queue(stack, f"Queue", visibility_timeout=Duration.seconds(60))
function.add_event_source(SqsEventSource(queue))

app.synth()
