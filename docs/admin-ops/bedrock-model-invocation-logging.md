# Bedrock Model Invocation Logging

## Overview

Amazon Bedrock model invocation logging captures request and response data for calls made through the `bedrock-runtime` endpoint (`Converse`, `ConverseStream`, `InvokeModel`, `InvokeModelWithResponseStream`). It is configured per account and per region. When enabled, Bedrock publishes each invocation record to a CloudWatch Logs log group.

This guide covers the infrastructure provisioned by the `account-wide-infrastructure.yml` template (when `EnableBedrockInvocationLogs` is `"true"`) and the manual activation step required after deployment.

> **Default:** `EnableBedrockInvocationLogs` defaults to `"false"`. Bedrock model invocation logging infrastructure is opt-in — set the parameter to `"true"` to provision the log group and IAM role, then run the manual activation command below.

> **Note:** `EnableBedrockInvocationLogs` by default is set to `false` due to the sensitive nature of the content (entire incoming prompts and returned output is captured). It should only be enabled in limited contexts (mainly non-production accounts or accounts that don't receive user submitted prompts). This is an account-wide setting and not able to be turned off by individual applications based on the content they handle. This is a limitation/feature of AWS Bedrock Model-level logging.

## What the Stack Creates vs. What It Does Not Do

### What is provisioned

When `EnableBedrockInvocationLogs` is `"true"`, the account-wide stack creates:

- **CloudWatch Logs log group** - `/aws/bedrock/{OrgPrefix}-ModelInvocations` with a configurable retention period (`BedrockInvocationLogExpirationInDays`, default 180 days) and optional KMS encryption (`BedrockInvocationLogKmsKeyArn`). The log group uses `DeletionPolicy: Retain` and `UpdateReplacePolicy: Retain` so previously collected audit records are never destroyed by a stack operation.
- **IAM role** - `{OrgPrefix}-Bedrock-CloudWatch-Role` with an inline policy granting exactly `logs:CreateLogStream` and `logs:PutLogEvents` scoped to the `aws/bedrock/modelinvocations` log stream within the created log group. The trust policy is conditioned on `aws:SourceAccount` and `aws:SourceArn` to prevent confused-deputy attacks.

### What is NOT done

Deploying the stack **does not** activate model invocation logging. The `PutModelInvocationLoggingConfiguration` API — the only mechanism to turn the feature on — has no corresponding CloudFormation resource type. You must run the activation CLI command once per account, per region after the stack is deployed.

## Prerequisites

Before activating logging:

1. **Account-wide stack deployed** with `EnableBedrockInvocationLogs` set to `"true"`. Confirm the stack outputs `BedrockModelInvocationLogGroupName`, `BedrockCloudWatchLogsRoleArn`, and `BedrockModelInvocationLoggingEnableCommand` are present.

2. **Caller IAM permissions** for the operator running the activation command:
   - `bedrock:PutModelInvocationLoggingConfiguration`
   - `bedrock:GetModelInvocationLoggingConfiguration`
   - `iam:PassRole` on the specific role ARN (`{OrgPrefix}-Bedrock-CloudWatch-Role`)

3. **Optional KMS key** (only when `BedrockInvocationLogKmsKeyArn` is set):
   - The key must be a **symmetric** customer managed key in the same AWS region as the stack.
   - The key policy **must** grant the `logs.<region>.amazonaws.com` service principal the following actions: `kms:Encrypt`, `kms:Decrypt`, `kms:ReEncrypt*`, `kms:GenerateDataKey*`, and `kms:DescribeKey`.
   - The template does not create or modify the key or its policy. This is a bring-your-own-key requirement that must be satisfied before deploying with a non-empty `BedrockInvocationLogKmsKeyArn`.

## Activation

Logging is disabled until you run the following AWS CLI command. Substitute your AWS region and the value of the `BedrockModelInvocationLoggingEnableCommand` stack output (which already has the log group name and role ARN filled in for you).

```bash
aws bedrock put-model-invocation-logging-configuration \
  --region <REGION> \
  --logging-config '<BedrockModelInvocationLoggingEnableCommand stack output>'
```

### Full command with explicit placeholders

If you prefer to supply each field manually:

```bash
aws bedrock put-model-invocation-logging-configuration \
  --region <REGION> \
  --logging-config '{
    "cloudWatchConfig": {
      "logGroupName": "<BedrockModelInvocationLogGroupName output>",
      "roleArn": "<BedrockCloudWatchLogsRoleArn output>"
    },
    "textDataDeliveryEnabled": true,
    "embeddingDataDeliveryEnabled": true,
    "imageDataDeliveryEnabled": false,
    "videoDataDeliveryEnabled": false
  }'
```

### Text and embedding delivery (always on)

- **`textDataDeliveryEnabled: true`** and **`embeddingDataDeliveryEnabled: true`** capture the JSON request/response bodies for text generation and embedding calls, which are the primary debugging use case. These always go to CloudWatch Logs.
- **`imageDataDeliveryEnabled`** and **`videoDataDeliveryEnabled`** are `false` in the activation command **unless** you enable S3 large-object logging (see below). Image and video payloads are typically binary and larger than the 100 KB CloudWatch Logs ceiling, so they require an Amazon S3 large data delivery target (`cloudWatchConfig.largeDataDeliveryS3Config`). Enabling image or video delivery without an S3 target will not capture the binary content.

## Enabling S3 Large-Object (Media) Logging

Additionally, image/video/large-binary payloads can be delivered to S3 as a first-class, opt-in feature. Set **`EnableBedrockLargeObjectLogging="true"`** on the account-wide stack (this also requires `EnableBedrockInvocationLogs="true"`, since the S3 large-object target is nested inside `cloudWatchConfig`).

What the stack does when enabled:

- Chooses a destination bucket by precedence: an explicit `BedrockLargeObjectLogBucketName`, otherwise the account-wide access log bucket (requires `EnableS3AccessLogBucket="true"`).
- When the destination is the account-wide bucket, adds a bucket-policy statement granting the **`bedrock.amazonaws.com`** service principal `s3:PutObject` scoped to `bedrock/AWSLogs/<account-id>/BedrockModelInvocationLogs/*`, guarded by `aws:SourceAccount` and `aws:SourceArn`. Adds an S3 lifecycle rule on the `bedrock/` prefix using `BedrockLargeObjectLogExpirationInDays` (default 90).
- Emits a `BedrockModelInvocationLoggingEnableCommand` that includes `cloudWatchConfig.largeDataDeliveryS3Config` (bucket + `keyPrefix: bedrock`) and sets `imageDataDeliveryEnabled`/`videoDataDeliveryEnabled` to `true`.

> **Note:** S3 large-object delivery is authorized by the **destination bucket policy** on the `bedrock.amazonaws.com` service principal — **not** by the CloudWatch role. The role provisioned for CloudWatch delivery needs no S3 permissions.

> **External bucket:** If you set `BedrockLargeObjectLogBucketName` to a bucket outside this stack, the stack cannot attach the bucket policy for you. You must add the `bedrock.amazonaws.com` `s3:PutObject` statement (scoped to `bedrock/AWSLogs/<account-id>/BedrockModelInvocationLogs/*`) to that bucket yourself, and if the bucket uses SSE-KMS, grant `bedrock.amazonaws.com` `kms:GenerateDataKey` on the key.

Activation remains the same manual CLI step — run the emitted `BedrockModelInvocationLoggingEnableCommand` once per region. See the [AWS model invocation logging documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html) for the full `PutModelInvocationLoggingConfiguration` schema.

## Verification

After running the activation command, confirm the configuration was applied:

```bash
aws bedrock get-model-invocation-logging-configuration --region <REGION>
```

A correctly configured response looks like:

```json
{
  "loggingConfig": {
    "cloudWatchConfig": {
      "logGroupName": "/aws/bedrock/ACME-ModelInvocations",
      "roleArn": "arn:aws:iam::123456789012:role/ACME-Bedrock-CloudWatch-Role",
      "largeDataDeliveryS3Config": {
        "bucketName": "",
        "keyPrefix": ""
      }
    },
    "s3Config": {
      "bucketName": "",
      "keyPrefix": ""
    },
    "textDataDeliveryEnabled": true,
    "imageDataDeliveryEnabled": false,
    "videoDataDeliveryEnabled": false,
    "embeddingDataDeliveryEnabled": true
  }
}
```

To confirm log events are arriving, navigate to CloudWatch Logs in the AWS Console and look for the log stream `aws/bedrock/modelinvocations` inside the log group `/aws/bedrock/{OrgPrefix}-ModelInvocations`. Log events appear within a few minutes of the first Bedrock invocation after activation.

The `BedrockModelInvocationLogGroupConsole` stack output contains a direct deep link to the log group in your region.

## Disabling Logging

To turn off model invocation logging for an account and region:

```bash
aws bedrock delete-model-invocation-logging-configuration --region <REGION>
```

This disables logging at the Bedrock service level. It does **not** delete the IAM role or the CloudWatch log group. Because the log group uses `DeletionPolicy: Retain`, any previously collected invocation logs remain available for the configured retention period even after logging is disabled or the stack is deleted.

To remove the provisioned infrastructure, update the stack with `EnableBedrockInvocationLogs` set to `"false"`. The IAM role will be deleted; the log group will be retained.

## Per-Region Operation

Model invocation logging is scoped per account and per region. If you use Amazon Bedrock in multiple regions, you must:

1. Deploy the account-wide stack in each region with `EnableBedrockInvocationLogs="true"`.
2. Run the activation command once in each region.

Each region gets its own log group (`/aws/bedrock/{OrgPrefix}-ModelInvocations`) and its own IAM role (`{OrgPrefix}-Bedrock-CloudWatch-Role`).

## Cost and Data Sensitivity Considerations

- **Content sensitivity:** Invocation logs contain the **full prompt and response content** of every logged Bedrock call. Treat the log group as sensitive data and apply appropriate access controls. Consider enabling KMS encryption with `BedrockInvocationLogKmsKeyArn` for regulated workloads.
- **CloudWatch Logs ingestion cost:** Each invocation record is ingested as a log event. Costs scale with call volume and payload size. See [CloudWatch Logs pricing](https://aws.amazon.com/cloudwatch/pricing/).
- **CloudWatch Logs storage cost:** Retention is controlled by the `BedrockInvocationLogExpirationInDays` parameter (default 180 days). Shorter retention reduces storage cost; increase it if you need longer audit trails.
- **Empty log group cost:** An empty log group with no ingested data incurs no CloudWatch storage charges. If you enable the stack feature but never activate logging, the log group is free.

## Known Limitations

These are deliberate scope decisions, not defects:

| Limitation | Detail |
|-----------|--------|
| `bedrock-runtime` endpoint only | Only calls through the `bedrock-runtime` endpoint are logged. Management plane calls (e.g., `CreateModelCustomizationJob`) are not captured. |
| 100 KB CloudWatch ceiling | A CloudWatch Logs destination carries invocation metadata and input/output JSON bodies **only up to 100 KB**. Binary data and bodies larger than 100 KB require the S3 large-object target, which is available via `EnableBedrockLargeObjectLogging` (see "Enabling S3 Large-Object (Media) Logging"). |
| Image and video delivery off by default | `imageDataDeliveryEnabled` and `videoDataDeliveryEnabled` are `false` unless `EnableBedrockLargeObjectLogging` is `true`, which wires the S3 large data delivery target and flips both flags to `true` in the activation command. |
| `s3Config` (all-logs-to-S3) not used | The templates use the hybrid `cloudWatchConfig.largeDataDeliveryS3Config` (small data to CloudWatch, large/binary to S3), not the top-level `s3Config` that would send *all* logs to S3. |
| No metric filters or alarms | CloudWatch metric filters, alarms, and dashboards over the invocation log group are not included. Add them separately if needed. |
| Activation is manual | There is no CloudFormation-native resource type for `PutModelInvocationLoggingConfiguration`. Activation requires a CLI command after deployment. |

## Troubleshooting

### `ValidationException` when running the activation command

The role ARN or log group name is incorrect, or the resources do not yet exist.

- Confirm the account-wide stack has `EnableBedrockInvocationLogs="true"` and the deployment completed successfully.
- Copy the `BedrockModelInvocationLoggingEnableCommand` output directly — it already has the correct log group name and role ARN substituted.
- If you ran the activation command before the stack was deployed, wait for the stack to complete and retry.

### `AccessDeniedException` when running the activation command

The calling IAM principal is missing `bedrock:PutModelInvocationLoggingConfiguration` or `iam:PassRole` on the Bedrock CloudWatch role. Review the [Prerequisites](#prerequisites) section and ensure the operator's IAM policy includes both permissions.

### Logs not appearing after successful activation

- Wait a few minutes after the first Bedrock invocation; there is a brief delay before log events appear.
- Confirm the correct log stream: Bedrock writes to `aws/bedrock/modelinvocations` (not a random stream name).
- Verify `textDataDeliveryEnabled` is `true` in the response from `get-model-invocation-logging-configuration`.
- If using KMS encryption, confirm the key policy grants `logs.<region>.amazonaws.com` the required KMS actions. An incorrect key policy causes log group creation to fail, which would be visible as a stack CREATE_FAILED event.

### `InvalidParameterException` related to KMS key

The `BedrockInvocationLogKmsKeyArn` value points to a key that does not exist, is in a different region, is disabled, or is an asymmetric key. CloudWatch Logs requires a symmetric CMK in the same region. Fix the key ARN or key policy and redeploy.

### Re-enable conflict: log group already exists

Because the log group uses `DeletionPolicy: Retain`, if you previously enabled the feature, disabled it (which deletes the role but retains the log group), and then re-enable it for the same `OrgPrefix` and region, CloudFormation will attempt to create a log group that already exists and fail with a conflict error.

To resolve, either:
- Delete the retained log group manually in the AWS Console or with `aws logs delete-log-group --log-group-name /aws/bedrock/{OrgPrefix}-ModelInvocations`, or
- Import the existing log group into the stack using a CloudFormation resource import.

## References

- [Monitor model invocation using CloudWatch Logs and Amazon S3](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html) — AWS documentation on Bedrock model invocation logging, trust policy shape, and log entry format
- [PutModelInvocationLoggingConfiguration API reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_PutModelInvocationLoggingConfiguration.html) — API parameters and schema
- [Configure model invocation logging via CloudFormation (AWS Prescriptive Guidance)](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/configure-bedrock-invocation-logging-cloudformation.html) — AWS reference pattern confirming a custom resource is required for full activation via CloudFormation
- [Encrypt log data in CloudWatch Logs using AWS KMS](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html) — KMS key requirements and key policy setup for CloudWatch Logs
- [CloudWatch Logs pricing](https://aws.amazon.com/cloudwatch/pricing/) — ingestion and storage cost details
