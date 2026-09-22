# Design Document

## Overview

This design adds account-wide Amazon Bedrock model invocation logging infrastructure to
`templates/v2/account/account-wide-infrastructure.yml`. It provisions two new conditional
resources assembled from new `AWS::Include` module snippets:

1. `AWS::Logs::LogGroup` — the CloudWatch Logs destination for model invocation logs.
2. `AWS::IAM::Role` — the role Amazon Bedrock assumes to publish to that log group, carrying a
   least-privilege inline policy.

Three new optional parameters (`EnableBedrockInvocationLogs`,
`BedrockInvocationLogExpirationInDays`, `BedrockInvocationLogKmsKeyArn`), two new conditions,
and five new conditional outputs complete the template changes.

The feature is modeled on the existing account-wide API Gateway CloudWatch logging feature for
structure and on the S3 access log bucket feature for parameter style. It diverges from both
where AWS's documented requirements for Bedrock differ (see
[Deliberate Divergences](#deliberate-divergences)).

The change is additive and backward compatible: no existing parameters, resources, outputs, or
exports are renamed or removed. All new parameters have defaults.

## Non-Goals

Per Requirement 14.4, the following are explicitly out of scope:

- Any Lambda-backed custom resource or other in-template mechanism that calls
  `PutModelInvocationLoggingConfiguration`. Activation is a documented manual CLI step.
- An Amazon S3 logging destination (`s3Config`) and its bucket policy.
- Large data delivery to S3 (`cloudWatchConfig.largeDataDeliveryS3Config`) and the
  `s3:PutObject` permission it would require. Consequence: payloads over 100 KB and binary
  image/video outputs are not captured. This is accepted because the feature targets debugging.
- ABAC-scoped managed policies granting project pipelines permission to use Bedrock.
- Creation or modification of a KMS key or key policy (bring-your-own-key only).
- CloudWatch metric filters, alarms, or dashboards over the log group.

This feature introduces **no new resource types** beyond `AWS::Logs::LogGroup` and
`AWS::IAM::Role`, both already well-established CloudFormation-native types.

## Approach

### Why activation is a manual step

Amazon Bedrock's model invocation logging configuration is an account-and-region-level setting
reachable only through the `PutModelInvocationLoggingConfiguration` API. There is no
`AWS::Bedrock::*` CloudFormation resource type for it — unlike API Gateway, whose analogous
account-level CloudWatch role attachment *does* have a native resource
(`AWS::ApiGateway::Account`). AWS's own reference CloudFormation pattern reaches the setting
with a Lambda-backed custom resource.

This design intentionally stops at the CloudFormation-native prerequisites. Introducing a
Lambda function, its execution role, and a `Custom::` resource into a module system that
currently contains none would be a significant architectural expansion for a one-line API call.
The template instead follows the precedent already set by the GitHub CodeConnections connection
in this same template: create the resource, then document the manual completion step.

### Why the role policy constructs its log group ARN

`Fn::GetAtt` on an `AWS::Logs::LogGroup` returns an ARN with a trailing `:*` (for example
`arn:aws:logs:us-east-1:123456789012:log-group:/aws/bedrock/ACME-ModelInvocations:*`). That
trailing wildcard cannot be extended into the `:log-stream:aws/bedrock/modelinvocations` suffix
that AWS's documented role policy requires. The inline policy therefore builds the ARN from
`AWS::Partition`, `AWS::Region`, `AWS::AccountId`, and `OrgPrefix` using `Fn::Sub`, producing an
identical log group path to the one the log group module creates.

A useful side effect: because the policy does not reference the log group resource, no implicit
dependency is created between the two resources, and no `DependsOn` is needed (Req 7.5). The two
resources are independent and can be created in any order.

The cost of this approach is that the log group name pattern
`/aws/bedrock/${OrgPrefix}-ModelInvocations` appears in two module files and must stay in sync.
This is mitigated by a unit test asserting both modules resolve the same path (see
[Testing Strategy](#testing-strategy)).

### Why the condition name matches the parameter name

`EnableBedrockInvocationLogs` is used as both a parameter name and a condition name. CloudFormation
keeps parameters and conditions in separate namespaces, and this template already does exactly
this for `EnableS3ArtifactsBucket` and `EnableS3AccessLogBucket`. Following the established
convention keeps the module contract comments predictable.

## Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│  account-wide-infrastructure.yml  (v2.0.2)                                    │
│                                                                               │
│  Parameters:  EnableBedrockInvocationLogs      (default "true")               │
│               BedrockInvocationLogExpirationInDays (default 180)              │
│               BedrockInvocationLogKmsKeyArn     (default "")                  │
│                                                                               │
│  Conditions:  EnableBedrockInvocationLogs                                     │
│               HasBedrockInvocationLogKmsKey                                   │
│         │                                                                     │
│         │ AWS::Include                                                        │
│         ├──────────────────────────────────┬──────────────────────────────────┤
│         ▼                                  ▼                                  │
│  BedrockModelInvocationLogGroup      BedrockCloudWatchLogsRole                │
│  (bedrock-cloudwatch-log-group.yml)  (bedrock-cloudwatch-role.yml)            │
│   AWS::Logs::LogGroup                 AWS::IAM::Role                          │
│   /aws/bedrock/${OrgPrefix}-           trust: bedrock.amazonaws.com           │
│       ModelInvocations                   + aws:SourceAccount                  │
│   RetentionInDays (param)                + aws:SourceArn                      │
│   KmsKeyId (conditional)               inline policy:                         │
│   DeletionPolicy: Retain                 logs:CreateLogStream                 │
│                                          logs:PutLogEvents                    │
│                                        scoped to log-group + log-stream       │
│         │                                  │                                  │
│         └──────────────┬───────────────────┘                                  │
│                        ▼                                                      │
│  Outputs (all Condition: EnableBedrockInvocationLogs)                         │
│    LogGroup Name  → export ${OrgPrefix}-Bedrock-CloudWatch-LogGroup-Name      │
│    LogGroup Arn   → export ${OrgPrefix}-Bedrock-CloudWatch-LogGroup-Arn       │
│    Role Arn       → export ${OrgPrefix}-Bedrock-CloudWatch-Role-Arn           │
│    EnableCommand  → ready-to-run activation CLI (not exported)                │
│    Console link   → CloudWatch log group deep link (not exported)             │
└───────────────────────────────────────────────────────────────────────────────┘
                        │
                        │  MANUAL STEP (not CloudFormation)
                        ▼
      aws bedrock put-model-invocation-logging-configuration
          --logging-config '{"cloudWatchConfig":{...}, text+embedding only}'
                        │
                        ▼
      Amazon Bedrock assumes the role and writes to log stream
      aws/bedrock/modelinvocations within the log group
```

## Deliberate Divergences

These are intentional differences from the templates this feature is modeled on. They are
recorded so future maintainers do not "correct" them.

| # | Divergence | From | Reason |
|---|-----------|------|--------|
| 1 | Trust policy carries `aws:SourceAccount` + `aws:SourceArn` conditions | `apigw-cloudwatch-role.yml` has an unconditioned `sts:AssumeRole` | AWS's documented Bedrock logging trust policy includes both confused-deputy guards |
| 2 | Permissions via an **inline** policy | API Gateway role attaches the AWS managed policy `AmazonAPIGatewayPushToCloudWatchLogs` | No AWS managed policy exists for Bedrock invocation logging; inline keeps least privilege per `AGENTS.md` |
| 3 | `DeletionPolicy: Retain` on the log group | `promote-log-group.yml`, `codebuild-log-group.yml`, `postdeploy-log-group.yml` all use `Delete` | Invocation logs are audit records containing prompt/response content; build logs are transient |
| 4 | Retention constrained by `AllowedValues` | `LogExpirationInDays` uses `MinValue`/`MaxValue` | CloudWatch Logs accepts only an enumerated set; Min/Max would permit values that fail at deploy time |
| 5 | No `AWS::ApiGateway::Account`-equivalent activation resource | API Gateway feature includes `apigw-cloudwatch-account.yml` | No native Bedrock resource type exists; activation is a documented manual step |
| 6 | Role has an explicit `RoleName` | `apigw-cloudwatch-role.yml` lets CloudFormation generate the name | `AGENTS.md` mandates the naming convention for IAM roles; the template already requires `CAPABILITY_NAMED_IAM` for its named managed policies, so this adds no new deployment capability |

## Components and Changes

| Component | File | Change |
|-----------|------|--------|
| Account-Wide Template | `templates/v2/account/account-wide-infrastructure.yml` | 3 params, 2 conditions, 2 resources, 5 outputs, metadata group, header comment; version → v2.0.2 |
| Log Group Module | `templates/v2/modules/account-wide/bedrock-cloudwatch-log-group.yml` | **New** |
| Role Module | `templates/v2/modules/account-wide/bedrock-cloudwatch-role.yml` | **New** |
| Modules Inventory | `templates/v2/modules/README.md` | Add the two new modules to the inventory |
| Admin Ops Doc | `docs/admin-ops/bedrock-model-invocation-logging.md` | **New** — for copy-over to `atlantis-platform-admin` |
| Admin Ops Index | `docs/admin-ops/account-management.md` | Add link to the new doc |
| End-User Docs | `docs/templates/v2/account/account-wide-infrastructure-README.md` | Document params, resources, outputs; add activation blockquote |
| Category README | `docs/templates/v2/account/README.md` | Update only if descriptions are affected |
| Changelog | `CHANGELOG.md` | Entry under `v0.0.43 - unreleased` → `### Added` |
| Tests | `tests/test_bedrock_invocation_logs_unit.py` | **New** unit tests |

## Detailed Design

### 1. New parameters (parent template, YAML shorthand permitted)

Inserted after the existing `AllowLegacyCloudFrontLogs` parameter, under a new
`# Bedrock Model Invocation Logs` subsection comment.

```yaml
  # ---------------------------------------------------------------------------
  # Bedrock Model Invocation Logs

  EnableBedrockInvocationLogs:
    Type: String
    Description: "Set to 'true' to create the CloudWatch Logs log group and IAM role required for Amazon Bedrock model invocation logging. This is a one-time, per-account, per-region setup. IMPORTANT: Creating these resources does NOT enable logging. After deployment you must run the AWS CLI command provided in the BedrockModelInvocationLoggingEnableCommand stack output to activate logging, because Amazon Bedrock provides no CloudFormation resource for the logging configuration."
    Default: "true"
    AllowedValues: ["true", "false"]
    ConstraintDescription: "Must be 'true' or 'false'."

  BedrockInvocationLogExpirationInDays:
    Type: Number
    Description: "The number of days to retain Bedrock model invocation logs in CloudWatch Logs. Default is 180 days. Longer retention increases CloudWatch Logs storage cost. Invocation logs contain full prompt and response content, so consider your data retention policy. Only applies when EnableBedrockInvocationLogs is 'true'. Must be one of the retention periods supported by CloudWatch Logs."
    Default: 180
    AllowedValues: [1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653]
    ConstraintDescription: "Must be one of the CloudWatch Logs retention values: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, or 3653."

  BedrockInvocationLogKmsKeyArn:
    Type: String
    Description: "Optional ARN of an existing customer managed KMS key used to encrypt the Bedrock model invocation log group. Leave empty to use CloudWatch Logs default encryption. The key MUST be a symmetric key in the same region, and its key policy MUST grant the logs.<region>.amazonaws.com service principal kms:Encrypt, kms:Decrypt, kms:ReEncrypt*, kms:GenerateDataKey*, and kms:Describe*. This template does not create or modify the key or its policy. Only applies when EnableBedrockInvocationLogs is 'true'."
    Default: ""
    AllowedPattern: "^arn:[a-z0-9-]+:kms:[a-z0-9-]+:\\d{12}:(key|alias)\\/.+$|^$"
    MaxLength: 256
    ConstraintDescription: "Must be empty or a valid KMS key or alias ARN, for example arn:aws:kms:us-east-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab."
```

Notes:
- The `AllowedPattern` mirrors the pattern AWS documents for the `AWS::Logs::LogGroup`
  `KmsKeyId` property, so it accepts either a key ARN or an alias ARN.
- `MinLength` is intentionally omitted so the empty default validates.
- The symmetric-key requirement cannot be expressed as a regex; it is enforced by CloudWatch
  Logs at deploy time (`InvalidParameterException`) and documented in the parameter description
  and the Admin Ops Doc.

### 2. New conditions (parent template)

```yaml
  EnableBedrockInvocationLogs: !Equals [!Ref EnableBedrockInvocationLogs, "true"]
  HasBedrockInvocationLogKmsKey: !Not [!Equals [!Ref BedrockInvocationLogKmsKeyArn, ""]]
```

### 3. Metadata parameter group (parent template)

Inserted between the `"S3 Access Log Bucket"` and `"Promotion"` groups:

```yaml
      -
        Label:
          default: "Bedrock Model Invocation Logs"
        Parameters:
          - EnableBedrockInvocationLogs
          - BedrockInvocationLogExpirationInDays
          - BedrockInvocationLogKmsKeyArn
```

### 4. Log group module — `bedrock-cloudwatch-log-group.yml`

```yaml
# -- Bedrock Model Invocation Log Group (Account-Wide) --
# Parent template must define parameters:
#   OrgPrefix, BedrockInvocationLogExpirationInDays, BedrockInvocationLogKmsKeyArn
# Parent template must define conditions:
#   EnableBedrockInvocationLogs, HasBedrockInvocationLogKmsKey
# NOTE: AWS::Include does not support YAML shorthand tags (!Sub, !Ref, etc.)
#       All intrinsic functions must use long-form syntax (Fn::Sub, Ref, etc.)
#
# CloudWatch Logs destination for Amazon Bedrock model invocation logs. Amazon
# Bedrock writes to the log stream 'aws/bedrock/modelinvocations' within this
# log group once model invocation logging is activated.
#
# IMPORTANT: Creating this log group does NOT enable model invocation logging.
# Activation is a manual post-deployment step; see the parent template header
# and docs/admin-ops/bedrock-model-invocation-logging.md
#
# KEEP IN SYNC: the log group name below must match the log-group segment of the
# policy Resource ARN in bedrock-cloudwatch-role.yml
#
# DeletionPolicy/UpdateReplacePolicy are Retain (deliberate): invocation logs are
# audit records containing prompt and response content and must survive stack
# deletion, feature disablement, and log group replacement. This intentionally
# differs from the pipeline log group modules, which use Delete.
#
# See https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html

Type: AWS::Logs::LogGroup
Condition: EnableBedrockInvocationLogs
DeletionPolicy: Retain
UpdateReplacePolicy: Retain
Properties:
  LogGroupName:
    Fn::Sub: "/aws/bedrock/${OrgPrefix}-ModelInvocations"
  RetentionInDays:
    Ref: BedrockInvocationLogExpirationInDays
  KmsKeyId:
    Fn::If:
      - HasBedrockInvocationLogKmsKey
      - Ref: BedrockInvocationLogKmsKeyArn
      - Ref: "AWS::NoValue"
```

### 5. Role module — `bedrock-cloudwatch-role.yml`

```yaml
# -- Bedrock CloudWatch Logs Role (Account-Wide) --
# Parent template must define parameters: OrgPrefix, RolePath
# Parent template must define condition: EnableBedrockInvocationLogs
# NOTE: AWS::Include does not support YAML shorthand tags (!Sub, !Ref, etc.)
#       All intrinsic functions must use long-form syntax (Fn::Sub, Ref, etc.)
#
# In order for Amazon Bedrock to publish model invocation logs to CloudWatch
# Logs, a role must exist that Bedrock can assume, granting write access to the
# destination log group's 'aws/bedrock/modelinvocations' log stream. The role ARN
# is supplied to Bedrock via the PutModelInvocationLoggingConfiguration API as a
# manual post-deployment step (Bedrock has no CloudFormation resource for it).
#
# The trust policy includes aws:SourceAccount and aws:SourceArn conditions to
# prevent the confused deputy problem, per AWS's documented trust policy. This
# is intentionally tighter than apigw-cloudwatch-role.yml.
#
# Permissions are granted via an inline policy because AWS publishes no managed
# policy for Bedrock invocation logging.
#
# KEEP IN SYNC: the log-group segment of the policy Resource ARN below must match
# the LogGroupName in bedrock-cloudwatch-log-group.yml
#
# The Resource ARN is constructed rather than derived via Fn::GetAtt because
# Fn::GetAtt on a log group returns an ARN with a trailing ':*', which cannot be
# extended with the ':log-stream:' suffix. A consequence is that this module has
# no dependency on the log group resource, so the parent needs no DependsOn.
#
# See https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html

Type: AWS::IAM::Role
Condition: EnableBedrockInvocationLogs
Properties:
  RoleName:
    Fn::Sub: "${OrgPrefix}-Bedrock-CloudWatch-Role"
  Path:
    Ref: RolePath
  Description: "Allows Amazon Bedrock to publish model invocation logs to CloudWatch Logs"
  AssumeRolePolicyDocument:
    Version: "2012-10-17"
    Statement:
      - Sid: AllowBedrockToAssumeRole
        Effect: Allow
        Principal:
          Service: bedrock.amazonaws.com
        Action: sts:AssumeRole
        Condition:
          StringEquals:
            aws:SourceAccount:
              Ref: "AWS::AccountId"
          ArnLike:
            aws:SourceArn:
              Fn::Sub: "arn:${AWS::Partition}:bedrock:${AWS::Region}:${AWS::AccountId}:*"
  Policies:
    - PolicyName: BedrockModelInvocationLogsWrite
      PolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Sid: PutBedrockModelInvocationLogs
            Effect: Allow
            Action:
              - logs:CreateLogStream
              - logs:PutLogEvents
            Resource:
              Fn::Sub: "arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/bedrock/${OrgPrefix}-ModelInvocations:log-stream:aws/bedrock/modelinvocations"
```

Role name length: `OrgPrefix` is at most 20 characters, plus the 24-character suffix
`-Bedrock-CloudWatch-Role`, for a maximum of 44 — within the IAM 64-character limit. `Path` does
not count toward that limit.

### 6. Parent template resources

Placed immediately after `ApiGatewayAccount`, keeping the account-level logging resources
grouped:

```yaml
  # -- Bedrock Model Invocation Log Group (Conditional) --
  BedrockModelInvocationLogGroup:
    Fn::Transform:
      Name: AWS::Include
      Parameters:
        Location: !Sub "s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/account-wide/bedrock-cloudwatch-log-group.yml"

  # -- Bedrock CloudWatch Logs Role (Conditional) --
  # No DependsOn: the role's inline policy constructs the log group ARN as a string
  # rather than referencing the log group resource, so the two are independent.
  BedrockCloudWatchLogsRole:
    Fn::Transform:
      Name: AWS::Include
      Parameters:
        Location: !Sub "s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/account-wide/bedrock-cloudwatch-role.yml"
```

### 7. Parent template outputs

Placed after the API Gateway CloudWatch logging output block.

```yaml
  # ---------------------------------------------------------------------------
  # Bedrock Model Invocation Logging

  BedrockModelInvocationLogGroupName:
    Condition: EnableBedrockInvocationLogs
    Description: "Name of the CloudWatch log group that receives Bedrock model invocation logs. Supply this as cloudWatchConfig.logGroupName when activating model invocation logging."
    Value: !Ref BedrockModelInvocationLogGroup
    Export:
      Name: !Sub "${OrgPrefix}-Bedrock-CloudWatch-LogGroup-Name"

  BedrockModelInvocationLogGroupArn:
    Condition: EnableBedrockInvocationLogs
    Description: "ARN of the CloudWatch log group that receives Bedrock model invocation logs"
    Value: !GetAtt BedrockModelInvocationLogGroup.Arn
    Export:
      Name: !Sub "${OrgPrefix}-Bedrock-CloudWatch-LogGroup-Arn"

  BedrockCloudWatchLogsRoleArn:
    Condition: EnableBedrockInvocationLogs
    Description: "ARN of the IAM role Amazon Bedrock assumes to publish model invocation logs to CloudWatch. Supply this as cloudWatchConfig.roleArn when activating model invocation logging."
    Value: !GetAtt BedrockCloudWatchLogsRole.Arn
    Export:
      Name: !Sub "${OrgPrefix}-Bedrock-CloudWatch-Role-Arn"

  BedrockModelInvocationLoggingEnableCommand:
    Condition: EnableBedrockInvocationLogs
    Description: "REQUIRED MANUAL STEP: run this AWS CLI command to activate Bedrock model invocation logging. Deploying this stack alone does not enable logging. Text and embedding delivery are enabled deliberately; image and video are disabled because binary payloads cannot be delivered to CloudWatch Logs without an S3 large data delivery target. Must be run once per region."
    Value: !Sub '{"cloudWatchConfig":{"logGroupName":"${BedrockModelInvocationLogGroup}","roleArn":"${BedrockCloudWatchLogsRole.Arn}"},"textDataDeliveryEnabled":true,"embeddingDataDeliveryEnabled":true,"imageDataDeliveryEnabled":false,"videoDataDeliveryEnabled":false}'

  BedrockModelInvocationLogGroupConsole:
    Condition: EnableBedrockInvocationLogs
    Description: "CloudWatch console link to the Bedrock model invocation log group"
    Value: !Sub "https://${AWS::Region}.console.aws.amazon.com/cloudwatch/home?region=${AWS::Region}#logsV2:log-groups/log-group/$252Faws$252Fbedrock$252F${OrgPrefix}-ModelInvocations"
```

Design notes on the outputs:

- `!Ref` on an `AWS::Logs::LogGroup` returns the **log group name**, which is exactly what the
  activation command and the export need.
- The activation output emits the **`--logging-config` JSON payload** rather than the entire
  command line. A CloudFormation output value cannot safely carry the single-quote shell
  quoting needed around embedded JSON across platforms, and the JSON payload is the part that
  actually needs substitution. The full command, with the payload interpolated, is documented in
  the template header and the Admin Ops Doc. The output `Description` states the command to wrap
  it in.
- The console link double-encodes the forward slashes in the log group path as `$252F`, which is
  the encoding the CloudWatch console requires for log group deep links. `$2` is not a `Fn::Sub`
  variable reference (only `${` is), so these literals pass through unchanged.

### 8. Parent template header comment addition

Appended to the existing feature list in the header comment block, leaving all existing header
content intact apart from the version line:

```
#   - Bedrock model invocation logging prerequisites (log group + IAM role)
#
# BEDROCK MODEL INVOCATION LOGGING - MANUAL ACTIVATION REQUIRED
# -------------------------------------------------------------
# When EnableBedrockInvocationLogs is 'true', this template creates the
# CloudWatch log group and the IAM role that Amazon Bedrock needs in order to
# publish model invocation logs. Deploying this stack does NOT turn logging on.
# Model invocation logging remains DISABLED until you run the activation command
# below.
#
# Why: Amazon Bedrock exposes its model invocation logging configuration only
# through the PutModelInvocationLoggingConfiguration API. Unlike API Gateway
# (AWS::ApiGateway::Account), there is no CloudFormation resource for it. This
# template deliberately avoids a Lambda-backed custom resource, so activation is
# a one-time manual step per account, per region.
#
# After deployment, run (substituting the stack output values):
#
#   aws bedrock put-model-invocation-logging-configuration \
#     --region <REGION> \
#     --logging-config '<BedrockModelInvocationLoggingEnableCommand output>'
#
# Where the output BedrockModelInvocationLoggingEnableCommand already contains
# the log group name (BedrockModelInvocationLogGroupName) and role ARN
# (BedrockCloudWatchLogsRoleArn) substituted for you.
#
# Verify with:
#   aws bedrock get-model-invocation-logging-configuration --region <REGION>
#
# Repeat in every region where Bedrock is used. Text and embedding delivery are
# enabled; image and video are deliberately disabled (see docs).
#
# Full instructions: docs/admin-ops/bedrock-model-invocation-logging.md
# AWS docs: https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html
```

### 9. Admin Ops Doc structure — `docs/admin-ops/bedrock-model-invocation-logging.md`

Section outline satisfying Requirement 10:

1. **Title + copy-over note** — states the doc is authored for copy-over into
   `https://github.com/63Klabs/atlantis-platform-admin`.
2. **Overview** — what model invocation logging is; that it is per-account, per-region.
3. **What the stack creates / what it does not do** — log group, role, inline policy; explicitly
   not activation.
4. **Prerequisites** — account-wide stack deployed with `EnableBedrockInvocationLogs="true"`;
   caller IAM permissions (`bedrock:PutModelInvocationLoggingConfiguration`,
   `bedrock:GetModelInvocationLoggingConfiguration`, and `iam:PassRole` on the role);
   optional KMS key requirements (symmetric, same region, `logs.<region>.amazonaws.com` key
   policy grant).
5. **Activation** — the full CLI command with placeholders and the fixed delivery toggles.
6. **Verification** — `get-model-invocation-logging-configuration` and a sample response; how to
   confirm log events are arriving in the `aws/bedrock/modelinvocations` log stream.
7. **Disabling** — `delete-model-invocation-logging-configuration`; note the log group is
   retained so prior logs survive.
8. **Per-region operation** — repeat per region.
9. **Cost and data sensitivity** — logs contain full prompt/response content; CloudWatch
   ingestion and storage are billable; retention governed by
   `BedrockInvocationLogExpirationInDays`.
10. **Limitations (deliberate)** — `bedrock-runtime` endpoint only; 100 KB ceiling with binary
    and oversized payloads unsupported without an out-of-scope S3 large data delivery target;
    image/video delivery disabled by default and why; how to opt in and the caveat if you do.
11. **Troubleshooting** — `ValidationException`, `AccessDeniedException`, logs not appearing,
    `InvalidParameterException` from a bad KMS key, and the retained-log-group re-create
    conflict.
12. **References** — attributed inline links to AWS documentation.

## Data Models

No data models change. The log event schema written by Bedrock into the log group is defined and
owned by AWS (see the log entry format section of the AWS documentation); this template does not
transform or consume it.

## Error Handling

| Scenario | Behavior |
|----------|----------|
| `EnableBedrockInvocationLogs` is `"false"` | No log group, no role, no Bedrock outputs. Deployment succeeds. (Req 1.5) |
| Enabled in a region where Bedrock is unavailable | Deployment succeeds; `AWS::Logs::LogGroup` and `AWS::IAM::Role` are not Bedrock resources and require no Bedrock API call. The activation command later fails in that region. Documented. (Req 14.1) |
| Existing stack updated with the `"true"` default, account does not use Bedrock | Log group and role are created. An empty log group and an unused role incur no charges. Operators may set `"false"`. (Req 14.2) |
| Toggled `"true"` → `"false"` on an existing stack | Role is deleted; log group is **retained** by `DeletionPolicy`. Update succeeds. (Req 14.3) |
| Toggled `"false"` → `"true"` after a prior enable, same `OrgPrefix` and region | The retained log group still exists, so log group creation fails with an already-exists error. Operator must delete the retained log group or import it. Documented in the module comment, the Admin Ops Doc troubleshooting section, and the end-user README. (Req 5.7) |
| `OrgPrefix` changed on an existing stack | `LogGroupName` change forces replacement; `UpdateReplacePolicy: Retain` keeps the old log group with its data, and a new log group is created under the new name. The role's policy ARN follows the new name. Prior logs remain in the retained log group. |
| `BedrockInvocationLogKmsKeyArn` set to a nonexistent, disabled, or asymmetric key | CloudWatch Logs rejects the association with `InvalidParameterException` and the stack operation fails. No custom guard; the AllowedPattern cannot detect this. Documented. |
| `BedrockInvocationLogKmsKeyArn` key policy missing the `logs.<region>.amazonaws.com` grant | Log group creation fails. Documented as a prerequisite. (Req 3.6) |
| `BedrockInvocationLogExpirationInDays` set to an unsupported value | Rejected by `AllowedValues` at parameter validation, before any resource is touched. (Req 2.3) |
| Activation command run before the stack is deployed | Bedrock returns `ValidationException` because the log group or role does not exist. Documented in troubleshooting. |
| Activation command run by a caller lacking `iam:PassRole` on the role | `AccessDeniedException`. Documented in troubleshooting. |
| Activation never run | Logging stays disabled and the log group remains empty. This is the primary documented failure mode, called out in the template header, the enable-command output description, and the README blockquote. (Req 9.2) |

## Correctness Properties

These invariants must hold for the change to be considered correct. They are the properties the
Testing Strategy verifies.

Property 1: Additive and backward compatible. No existing parameter, condition, resource, output,
or export is renamed, removed, or altered. A stack deployed before this change and updated after
it, with the new parameters left at their defaults, gains exactly the log group, the role, and
the five outputs, and nothing else changes.
**Validates: Requirements 12.1, 14.2**

Property 2: Full conditional gating. When `EnableBedrockInvocationLogs` is `"false"`, neither
module's resource is created and none of the five outputs is emitted. No output references a
resource that does not exist, because every new output carries
`Condition: EnableBedrockInvocationLogs`.
**Validates: Requirements 1.5, 8.1**

Property 3: Least privilege. The role's inline policy grants exactly `logs:CreateLogStream` and
`logs:PutLogEvents`, on exactly one resource ARN scoped to both the specific log group and the
specific log stream `aws/bedrock/modelinvocations`. No wildcard action and no wildcard resource.
**Validates: Requirements 6.7, 6.8, 6.9**

Property 4: Confused-deputy protection. The trust policy permits only `bedrock.amazonaws.com`, and
only when `aws:SourceAccount` equals this account and `aws:SourceArn` matches
`arn:<partition>:bedrock:<region>:<account>:*`.
**Validates: Requirements 6.4, 6.5**

Property 5: Log group path consistency. The `LogGroupName` produced by the log group module and
the log-group segment of the role policy's `Resource` ARN resolve to the identical string
`/aws/bedrock/${OrgPrefix}-ModelInvocations` for any valid `OrgPrefix`. If they diverge, the role
cannot write and logging silently fails.
**Validates: Requirements 5.4, 6.8**

Property 6: Audit durability. The log group carries both `DeletionPolicy: Retain` and
`UpdateReplacePolicy: Retain`, so no stack deletion, feature disablement, or name-driven
replacement destroys previously collected invocation logs.
**Validates: Requirements 5.7**

Property 7: KMS optionality. When `BedrockInvocationLogKmsKeyArn` is empty, `KmsKeyId` is absent
from the synthesized resource entirely (via `AWS::NoValue`) rather than present-and-empty, which
would be rejected.
**Validates: Requirements 3.4, 3.5**

Property 8: Empty-default validity. `BedrockInvocationLogKmsKeyArn` accepts its empty default: the
`AllowedPattern` includes the `|^$` alternative and no `MinLength` is declared.
**Validates: Requirements 3.1, 3.2**

Property 9: Retention validity. Every value in `AllowedValues` for
`BedrockInvocationLogExpirationInDays` is accepted by `AWS::Logs::LogGroup.RetentionInDays`, and
the default `180` is a member of that set.
**Validates: Requirements 2.3**

Property 10: Module form. Each new module file contains exactly one resource body, with no logical
ID and no `Resources:` wrapper, and uses long-form intrinsics only, so it remains valid when
spliced by `AWS::Include`.
**Validates: Requirements 5.2, 5.8, 6.2, 6.10**

Property 11: Partition portability. All constructed ARNs use `${AWS::Partition}` rather than a
hardcoded `aws`, so the template functions outside the commercial partition.
**Validates: Requirements 6.5, 6.8**

Property 12: Activation payload correctness. The emitted `--logging-config` JSON is well-formed,
names the created log group and role, and sets text and embedding delivery true with image and
video false.
**Validates: Requirements 8.4**

## Testing Strategy

Per the repository testing guidelines: fast, concrete unit tests; no new property-based tests.
All assertions are static analysis of the template and module YAML — no AWS calls.

### New file: `tests/test_bedrock_invocation_logs_unit.py`

**Parent template — parameters and conditions**
- `EnableBedrockInvocationLogs`: type String, default `"true"`, `AllowedValues == ["true","false"]`,
  constraint description present.
- `BedrockInvocationLogExpirationInDays`: type Number, default `180`, `AllowedValues` equals the
  exact 22-value CloudWatch Logs set, default is a member of it, and no `MinValue`/`MaxValue` keys.
- `BedrockInvocationLogKmsKeyArn`: type String, default `""`, `MaxLength == 256`, no `MinLength`,
  `AllowedPattern` ends with `|^$`.
- Conditions `EnableBedrockInvocationLogs` and `HasBedrockInvocationLogKmsKey` exist with the
  expected shapes.

**Parent template — metadata**
- A parameter group labeled `"Bedrock Model Invocation Logs"` exists containing exactly the three
  new parameters in order.
- Its index falls between the `"S3 Access Log Bucket"` and `"Promotion"` groups.
- Every new parameter appears in exactly one group.

**Parent template — resources and outputs**
- `BedrockModelInvocationLogGroup` and `BedrockCloudWatchLogsRole` exist and each is an
  `AWS::Include` transform pointing at the expected module path.
- The five new outputs exist, each with `Condition: EnableBedrockInvocationLogs`, and the three
  exported ones carry the expected export names.
- The enable-command output value parses as valid JSON after stripping `Fn::Sub` placeholders, and
  asserts `textDataDeliveryEnabled`/`embeddingDataDeliveryEnabled` are `true` while
  `imageDataDeliveryEnabled`/`videoDataDeliveryEnabled` are `false`.
- Header `# Version:` line is `v2.0.2`.
- Header text contains the manual-activation warning and the
  `put-model-invocation-logging-configuration` command.

**Log group module**
- Single resource body: top-level keys are a subset of
  `{Type, Condition, DeletionPolicy, UpdateReplacePolicy, Properties}`; no `Resources` key; no
  logical-ID nesting.
- `Type == AWS::Logs::LogGroup`, `Condition == EnableBedrockInvocationLogs`,
  `DeletionPolicy == Retain`, `UpdateReplacePolicy == Retain`.
- `LogGroupName` is `Fn::Sub: "/aws/bedrock/${OrgPrefix}-ModelInvocations"`.
- `RetentionInDays` is `Ref: BedrockInvocationLogExpirationInDays`.
- `KmsKeyId` is an `Fn::If` on `HasBedrockInvocationLogKmsKey` whose false branch is
  `Ref: AWS::NoValue`.

**Role module**
- Single resource body; `Type == AWS::IAM::Role`, `Condition == EnableBedrockInvocationLogs`.
- Trust policy: single statement, `Effect: Allow`, `Principal.Service == bedrock.amazonaws.com`,
  `Action == sts:AssumeRole`, `Condition.StringEquals` contains `aws:SourceAccount`, and
  `Condition.ArnLike` contains `aws:SourceArn` whose `Fn::Sub` references `${AWS::Partition}`,
  `${AWS::Region}`, and `${AWS::AccountId}`.
- Exactly one inline policy; its statement `Action` equals
  `["logs:CreateLogStream", "logs:PutLogEvents"]`.
- `Resource` is a single `Fn::Sub` string ending in `:log-stream:aws/bedrock/modelinvocations`
  and containing `${AWS::Partition}`.
- Negative assertions: no `logs:*`, no `Action: "*"`, no `Resource: "*"`, and no
  `ManagedPolicyArns` key.
- `Path` is `Ref: RolePath`; `RoleName` is `Fn::Sub: "${OrgPrefix}-Bedrock-CloudWatch-Role"`.

**Cross-module consistency (guards Correctness Property 5)**
- Extract the log group path from the log group module's `LogGroupName` and the log-group segment
  from the role module's policy `Resource`, and assert the two strings are equal. This is the test
  that catches drift between the two files.

**Module hygiene (both modules)**
- Raw file text contains no YAML shorthand intrinsic tags (`!Sub`, `!Ref`, `!GetAtt`, `!If`,
  `!Join`, `!Not`, `!Equals`).
- Header comment declares the required parent parameters and conditions and contains the AWS
  documentation URL.

### Documentation test
- `docs/admin-ops/bedrock-model-invocation-logging.md` exists, contains the copy-over note naming
  the `atlantis-platform-admin` repository, and contains the activation, verification, and
  disable commands.
- `docs/admin-ops/account-management.md` links to the new doc.

### Linting
- Run the repository's `cfn-lint` flow over the modified parent template. Existing suppressions
  (E3001, E3005, E6101, W2001, W8001) are expected to be sufficient, since the template already
  uses `!Ref` and `!GetAtt` against `AWS::Include`-sourced resources
  (`ApiGatewayCloudWatchLogsRole`, `AccessLogBucketRegional`, `S3ArtifactsBucketRegional`). Add no
  new suppression unless a specific finding requires it, and justify any that is added.

### Regression
- Run the full existing suite. No existing test is expected to assert on the account-wide
  template's parameter count, group count, or output count; if any does, update it for the
  additions.

## Requirements Coverage

| Requirement | Addressed by |
|-------------|--------------|
| 1 (`EnableBedrockInvocationLogs`) | Detailed Design §1, §2 |
| 2 (`BedrockInvocationLogExpirationInDays`) | §1; Divergence 4 |
| 3 (optional KMS) | §1, §4; Error Handling |
| 4 (parameter grouping) | §3 |
| 5 (log group module) | §4; Divergence 3; Approach (name sync) |
| 6 (IAM role module) | §5; Divergences 1, 2, 6 |
| 7 (wiring into parent) | §6; Approach (why the ARN is constructed) |
| 8 (outputs and exports) | §7 |
| 9 (header documentation) | §8 |
| 10 (Admin Ops Doc) | §9 |
| 11 (end-user documentation) | Components and Changes table |
| 12 (versioning) | Components and Changes table; Testing Strategy (version assertion) |
| 13 (changelog) | Components and Changes table |
| 14 (deployment behavior, non-goals) | Non-Goals; Error Handling |
| 15 (validation and testing) | Testing Strategy |
