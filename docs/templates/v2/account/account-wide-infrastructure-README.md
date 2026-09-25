# account-wide-infrastructure

Account-wide resources: ABAC-scoped managed policies, shared connections, optional S3 artifacts bucket, and optional shared S3 access log bucket — Assembled from reusable modules.

**Version:** v2.1.0/2026-09-23  
**Template:** [templates/v2/account/account-wide-infrastructure.yml](../../../../templates/v2/account/account-wide-infrastructure.yml)

## Overview

This template creates account-wide infrastructure for the Atlantis DevOps Platform. It assembles shared resources from reusable module snippets stored in S3 using `AWS::Include` transforms. Resources include ABAC-scoped managed policies for CloudFormation service roles, shared GitHub connections, optional API Gateway CloudWatch logging, optional Bedrock model invocation logging, an optional shared S3 artifacts bucket, and an optional shared S3 access log bucket.

### Use Cases

- Deploy ABAC-scoped managed policies (CodeBuild CRUD, Cognito CRUD) for CloudFormation service roles
- Create a shared GitHub connection for all pipeline templates in the account
- Enable account-level API Gateway CloudWatch logging (one-time per-region setup)
- Enable Bedrock model invocation logging prerequisites (one-time per-region setup)
- Provision a shared S3 artifacts bucket accessible by all pipeline roles
- Provision a shared S3 access log bucket that receives server access logs (and optionally legacy CloudFront standard logs) — used automatically as the artifacts bucket's log destination

### Prerequisites

- S3 bucket containing the Atlantis module snippets (provided by 63klabs regional buckets or your own)
- IAM permissions to create managed policies, IAM roles, CodeConnections, and S3 buckets
- (Optional) An existing external S3 access log bucket if you prefer to override the shared access log bucket via `S3LogBucketName`

### Important Notes

- This template should be deployed **once per account per region** before any project-specific templates
- The GitHub connection requires manual authorization in the AWS Console after deployment
- All optional resources are disabled by default — enable them via parameters

## v0.0.44 Changes (Log Prefix Segmentation, Service Lockdown, and Bedrock Media Logging)

v2.1.0 reorganizes the account-wide logging bucket into a provider-prefixed, per-prefix-lifecycle, per-principal-locked-down design, adds a dedicated CloudFront legacy logging bucket, and adds opt-in Bedrock large-object (media) delivery to S3. These are breaking changes applied in place (see the repository CHANGELOG).

### New parameters

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `S3AccessLogExpirationInDays` | Number (1-365) | 180 | Retention for the four `s3access/*` sub-prefix lifecycle rules on the main log bucket |
| `EnableBedrockLargeObjectLogging` | String (`true`/`false`) | `false` | Opt in to delivering Bedrock image/video/large-binary payloads to S3 under `bedrock/`. Requires `EnableBedrockInvocationLogs=true` and a destination (see Rules) |
| `BedrockLargeObjectLogExpirationInDays` | Number (1-365) | 90 | S3 lifecycle retention for the `bedrock/` prefix (distinct from the CloudWatch `BedrockInvocationLogExpirationInDays`) |
| `BedrockLargeObjectLogBucketName` | String (S3 name or empty) | `""` | Optional external destination for Bedrock media logs; takes precedence over the account-wide bucket. The stack cannot attach a policy to an external bucket (you must add the `bedrock.amazonaws.com` statement yourself) |

`AllowLegacyCloudFrontLogs` is **repurposed**: it no longer toggles ACLs on the main bucket. When `true` it now provisions a **separate** ACL-enabled `cloudfront-logs-legacy` bucket (see below). `LogExpirationInDays` now applies to the main bucket's `cloudfront/` prefix and to the legacy bucket.

### Two-bucket logging model

- **Main access log bucket** (`AccessLogBucketRegional`, ownership `BucketOwnerEnforced`, ACLs disabled): holds S3 server access logs under `s3access/<type>/<bucket-name>/` (`cf-artifacts`, `cloudfront-oac`, `devops`, `apps`), CloudFront **v2** logs under `cloudfront/`, and Bedrock media under `bedrock/`.
- **CloudFront legacy bucket** (`CloudFrontLegacyLogBucket`, ownership `BucketOwnerPreferred`, ACLs enabled, created only when `AllowLegacyCloudFrontLogs=true`): holds CloudFront **v1** standard logs under `cloudfront/`. Isolating ACLs in a second bucket lets CloudFront v1 keep working (from any region) without weakening the main bucket, which must keep ACLs disabled for Bedrock S3 delivery.

### Per-prefix lifecycle (main bucket)

`cloudfront/` uses `LogExpirationInDays`; the four `s3access/*` sub-prefixes use `S3AccessLogExpirationInDays`; `bedrock/` uses `BedrockLargeObjectLogExpirationInDays` (only when Bedrock media targets the account-wide bucket).

### Per-principal, per-prefix bucket policy (main bucket)

- `logging.s3.amazonaws.com` -> `s3access/*` (condition `aws:SourceAccount` + `aws:SourceArn arn:aws:s3:::*-an`)
- `delivery.logs.amazonaws.com` -> `cloudfront/*` (CloudFront v2 vended-log delivery)
- `bedrock.amazonaws.com` -> `bedrock/AWSLogs/<account>/BedrockModelInvocationLogs/*` (conditional)

> **Note:** S3 server access log delivery cannot bind the `<bucket-name>` path segment to the actual source bucket, and cannot gate a prefix by source-bucket tag. The `s3access/<type>/<bucket-name>/` structure is enforced organizationally by each producer's `LogFilePrefix`, plus account-level and naming-convention (`*-an`) scoping on the shared policy.

### New Rules (validation)

- `EnableBedrockLargeObjectLogging=true` requires `EnableS3AccessLogBucket=true` **or** a non-empty `BedrockLargeObjectLogBucketName`.
- `EnableBedrockLargeObjectLogging=true` requires `EnableBedrockInvocationLogs=true` (the S3 large-object target is nested inside `cloudWatchConfig`).

### New outputs (exports)

- `${OrgPrefix}-CloudFront-Legacy-Log-Bucket-Name` and `-Arn` (when `AllowLegacyCloudFrontLogs=true`) — imported by the network template for CloudFront v1 logging.

### Bedrock activation command

When `EnableBedrockLargeObjectLogging=true`, `BedrockModelInvocationLoggingEnableCommand` includes `cloudWatchConfig.largeDataDeliveryS3Config` (bucket + `keyPrefix: bedrock`) and sets `imageDataDeliveryEnabled`/`videoDataDeliveryEnabled` to `true`. When `false`, the command is unchanged from v0.0.43. Activation remains a manual per-region CLI step. See [docs/admin-ops/bedrock-model-invocation-logging.md](../../../admin-ops/bedrock-model-invocation-logging.md).

### Migration

Deploy this stack first, then update producer stacks (artifacts, OAC, devops, network) to the new `s3access/<type>/` prefixes; until a producer is updated it may be briefly denied delivery to a now-disallowed prefix. No bucket is replaced (main bucket name unchanged; legacy bucket is additive).
- Module snippets are loaded from S3 at deploy time via `AWS::Include` transforms
- Resources use conditions for optional creation — no errors occur when features are disabled

## Parameters

### Organization Naming

Parameters that define the organization-level naming for exported resources.

- [OrgPrefix](#orgprefix)

### IAM Configuration

IAM path configuration for managed policies and roles.

- [RolePath](#rolepath)

### GitHub Connection

Configuration for the shared GitHub connection via AWS CodeConnections.

- [GitHubOrg](#githuborg)

### API Gateway

Optional API Gateway CloudWatch logging configuration.

- [EnableApiGwCloudWatchLogs](#enableapigwcloudwatchlogs)

### S3 Artifacts Bucket

Optional shared S3 artifacts bucket for pipeline build artifacts.

- [EnableS3ArtifactsBucket](#enables3artifactsbucket)
- [S3BucketNameOrgPrefix](#s3bucketnameorgprefix)
- [S3LogBucketName](#s3logbucketname)

### S3 Access Log Bucket

Optional shared S3 access log bucket for storing S3 server access logs (and optionally legacy CloudFront standard logs).

- [EnableS3AccessLogBucket](#enables3accesslogbucket)
- [LogExpirationInDays](#logexpirationindays)
- [AllowLegacyCloudFrontLogs](#allowlegacycloudfrontlogs)

### Bedrock Model Invocation Logs

Optional CloudWatch Logs log group and IAM role required for Amazon Bedrock model invocation logging. This is a one-time, per-account, per-region setup. **Deploying this stack does not activate logging** — a post-deployment CLI step is required.

- [EnableBedrockInvocationLogs](#enablebedrockinvocationlogs)
- [BedrockInvocationLogExpirationInDays](#bedrockinvocationlogexpirationindays)
- [BedrockInvocationLogKmsKeyArn](#bedrockinvocationlogkmskeyarn)

> **Important:** Creating these resources does NOT enable Bedrock model invocation logging. After deployment you must run the activation command in the `BedrockModelInvocationLoggingEnableCommand` stack output. See [docs/admin-ops/bedrock-model-invocation-logging.md](../../../../docs/admin-ops/bedrock-model-invocation-logging.md) for full instructions.

### Promotion

Optional, additive, default-off parameters that grant cross-account write access to the artifacts bucket's `promotions/*` prefix and enable EventBridge notifications so this account can act as a promotion receiver.

- [PromotionSourceAccountIds](#promotionsourceaccountids)
- [EnablePromotionTrigger](#enablepromotiontrigger)

### Module Source

Configuration for where module snippets are loaded from.

- [S3ModuleLocation](#s3modulelocation)
- [S3ModuleNamespace](#s3modulenamespace)

---

#### OrgPrefix

Organization-level prefix prepended to managed policy names for identification and grouping. For example, 'ACME' would produce policy names like 'ACME-ProjectPipeline-CodeBuildCrud'.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | ACME |
| Allowed Pattern | `^[A-Z][A-Z0-9-]{0,18}[A-Z0-9]$` |
| Min Length | 2 |
| Max Length | 20 |
| Constraint Description | 2 to 20 characters. Upper case alphanumeric and dashes. Must start with a letter and end with a letter or number. |

#### RolePath

Path to use for IAM Managed Policies created by this template. Use to organize policies within your IAM structure.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\/([a-zA-Z0-9-_]+[\/])+$\|^\/$` |
| Constraint Description | May only contain alphanumeric characters, forward slashes, underscores, and dashes. Must begin and end with a slash. |

#### GitHubOrg

GitHub organization or username to connect to. Leave empty to skip creating a GitHub connection.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |

> **Note:** After deployment, you must manually authorize the GitHub connection in the AWS Console at CodeConnections → Connections. The connection will remain in PENDING status until authorized.

#### EnableApiGwCloudWatchLogs

Set to 'true' to create the account-level IAM role and API Gateway Account configuration required for API Gateway to push logs to CloudWatch. This is a one-time, per-account, per-region setup.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | true |
| Allowed Values | true, false |
| Constraint Description | Must be 'true' or 'false'. |

#### EnableS3ArtifactsBucket

Set to 'true' to create a shared, account-wide S3 artifacts bucket for pipeline build artifacts. This bucket is accessible by all pipeline roles in the account.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | true |
| Allowed Values | true, false |
| Constraint Description | Must be 'true' or 'false'. |

> **Note:** When enabled, this creates an S3 bucket with a bucket policy that uses `Principal: "*"` with `aws:PrincipalArn` `ArnLike` conditions to grant access to all CodePipeline, CodeBuild, and CloudFormation service roles matching the suffix convention (`*-CodePipelineServiceRole`, `*-CodeBuildServiceRole`, `*-CloudFormationSvcRole`). Roles do not need to exist at deploy time. This is an alternative to per-project artifacts buckets created by `template-storage-s3-artifacts.yml`.

#### S3BucketNameOrgPrefix

Optional lowercase organization prefix prepended to the S3 artifacts bucket name for uniqueness. Leave empty to omit. Example: 'acme' would produce 'acme-cf-artifacts-123456789012-us-east-1-an'.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,18}[a-z0-9]$\|^$` |
| Constraint Description | May be empty or 2 to 20 characters (8 or less recommended). Lower case alphanumeric and dashes. Must start and end with a letter or number. |

> **Tip:** Keep this prefix short (8 characters or less) to avoid exceeding the 63-character S3 bucket name limit. The full bucket name follows the pattern: `[S3BucketNameOrgPrefix-]cf-artifacts-{AccountId}-{Region}-an`.

#### S3LogBucketName

Optional S3 bucket name for server access logging of the artifacts bucket. When set, this bucket takes precedence over the account-wide access log bucket. Leave empty to fall back to the access log bucket (when `EnableS3AccessLogBucket` is `'true'`), or to disable logging entirely (when `EnableS3AccessLogBucket` is `'false'`).

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$\|^$` |
| Constraint Description | Must be a valid S3 bucket name or empty. Must be between 3 and 63 characters long. Lower case alphanumeric and dashes. Must start and end with a letter or number. |

> **Important:** If you supply `S3LogBucketName`, that external log bucket must already exist before deploying this template and must have appropriate permissions to receive S3 server access logs. If you instead rely on the shared access log bucket (`EnableS3AccessLogBucket=true`), the log bucket and its delivery policy are created for you by this template.

> **Precedence:** An explicitly supplied `S3LogBucketName` always wins. When both `S3LogBucketName` is set and `EnableS3AccessLogBucket=true`, the access log bucket is still created but the artifacts bucket logs to `S3LogBucketName`; the redundant value is silently ignored.

#### EnableS3AccessLogBucket

Set to 'true' to create a shared, account-wide S3 bucket for storing S3 server access logs. When enabled, the account-wide artifacts bucket logs to this bucket unless `S3LogBucketName` is set (an explicitly supplied `S3LogBucketName` always takes precedence).

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | true |
| Allowed Values | true, false |
| Constraint Description | Must be 'true' or 'false'. |

> **Note:** The bucket name follows the pattern `[S3BucketNameOrgPrefix-]access-logs-{AccountId}-{Region}-an` (no Prefix/ProjectId, since this is account-wide). It uses `DeletionPolicy: Retain` and `UpdateReplacePolicy: Retain` so logs are preserved if the stack is deleted or the bucket is replaced.

#### LogExpirationInDays

The number of days to keep logs in the access log bucket. Default is 90 days, max is 365. Consider exporting for longer retention. Only applies when `EnableS3AccessLogBucket` is `'true'`.

| Attribute | Setting |
|-----------|---------|
| Type | Number |
| Default | 180 |
| Min Value | 1 |
| Max Value | 365 |
| Constraint Description | Must be between 1 and 365 days. |

#### AllowLegacyCloudFrontLogs

Set to 'true' to enable legacy CloudFront standard logging support on the access log bucket. When enabled, `BlockPublicAcls` is set to false, `ObjectOwnership` is set to `BucketOwnerPreferred`, and a bucket policy statement is added for the CloudFront log delivery service (`delivery.logs.amazonaws.com`). Default is 'false' to maintain the secure configuration. Only applies when `EnableS3AccessLogBucket` is `'true'`.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | false |
| Allowed Values | true, false |
| Constraint Description | Must be 'true' or 'false'. |

> **Security Note:** Enabling legacy CloudFront logging relaxes the bucket's ACL and ownership controls (`BlockPublicAcls: false`, `ObjectOwnership: BucketOwnerPreferred`) to satisfy the legacy CloudFront log delivery mechanism. Leave this `false` unless you specifically need legacy CloudFront standard logging into this bucket.

#### EnableBedrockInvocationLogs

Set to 'true' to create the CloudWatch Logs log group and IAM role required for Amazon Bedrock model invocation logging. This is a one-time, per-account, per-region setup. Creating these resources does NOT enable logging — a post-deployment CLI step is required.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | false |
| Allowed Values | true, false |
| Constraint Description | Must be 'true' or 'false'. |

> **Important:** Deploying with `EnableBedrockInvocationLogs="true"` creates the infrastructure prerequisites but does **not** activate logging. After deployment run: `aws bedrock put-model-invocation-logging-configuration --region <REGION> --logging-config '<BedrockModelInvocationLoggingEnableCommand output>'`. See [docs/admin-ops/bedrock-model-invocation-logging.md](../../../../docs/admin-ops/bedrock-model-invocation-logging.md) for full instructions.

#### BedrockInvocationLogExpirationInDays

The number of days to retain Bedrock model invocation logs in CloudWatch Logs. Invocation logs contain full prompt and response content — consider your data retention policy. Longer retention increases CloudWatch Logs storage cost. Only applies when `EnableBedrockInvocationLogs` is `'true'`. Must be one of the retention periods supported by CloudWatch Logs.

| Attribute | Setting |
|-----------|---------|
| Type | Number |
| Default | 180 |
| Allowed Values | 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653 |
| Constraint Description | Must be one of the CloudWatch Logs retention values listed above. |

> **Note:** Unlike `LogExpirationInDays` (which uses `MinValue`/`MaxValue`), this parameter uses `AllowedValues` because CloudWatch Logs only accepts an enumerated set of retention periods — arbitrary day counts are rejected at deploy time.

#### BedrockInvocationLogKmsKeyArn

Optional ARN of an existing customer managed KMS key used to encrypt the Bedrock model invocation log group. Leave empty to use CloudWatch Logs default encryption.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | Valid KMS key or alias ARN, or empty |
| Max Length | 256 |
| Constraint Description | Must be empty or a valid KMS key or alias ARN. |

> **KMS Prerequisites:** The key must be a **symmetric** customer managed key in the same AWS region. Its key policy must grant `logs.<region>.amazonaws.com` the actions `kms:Encrypt`, `kms:Decrypt`, `kms:ReEncrypt*`, `kms:GenerateDataKey*`, and `kms:DescribeKey`. This template does not create or modify the key or its policy.

#### PromotionSourceAccountIds

Optional list of AWS account IDs permitted to write cross-account promotion artifacts to the account-wide artifacts bucket. When set, a bucket policy statement grants the listed accounts' `*-PromoteServiceRole` roles write/read access scoped to the `promotions/*` prefix only. Leave empty to omit the cross-account statement entirely.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | "" (empty) |

> **Note:** This parameter has no effect unless `EnableS3ArtifactsBucket` is `'true'`. It only widens the `S3ArtifactBucketPolicy` to allow the listed accounts' `*-PromoteServiceRole` roles to `s3:PutObject`, `s3:GetObject`, and `s3:GetObjectVersion` under `promotions/*` in this account's artifacts bucket — no other prefix or principal is affected.

#### EnablePromotionTrigger

Set to 'true' to let this account's artifacts bucket automatically trigger receiving (promotion) pipelines when a promoted artifact arrives. Enable this on the receiving account when using same-account or cross-account promotion. Under the hood this turns on S3 EventBridge notifications on the bucket, which the promotion source event rule depends on. This does not automatically approve incoming artifacts to run the pipeline.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | true |
| Allowed Values | true, false |
| Constraint Description | Must be 'true' or 'false'. |

> **Note:** This parameter has no effect unless `EnableS3ArtifactsBucket` is `'true'`. Set this to `'true'` on the account that hosts `template-pipeline-s3-source.yml` receiving pipelines so their `PromotionSourceEvent` EventBridge rules can react to new promotion artifacts.

#### S3ModuleLocation

S3 bucket name containing module snippets. Modules are loaded from `s3://<S3ModuleLocation>/<S3ModuleNamespace>/templates/v2/modules/*`.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None (required) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$` |
| Min Length | 3 |
| Max Length | 63 |
| Constraint Description | Must be a valid S3 bucket name between 3 and 63 characters containing only lowercase letters, numbers, and hyphens. |

**Regional buckets provided by 63klabs:**
- `63klabs-atlas-us-east-1` (US East - N. Virginia)
- `63klabs-zenith-us-east-2` (US East - Ohio)
- `63klabs-fabric-us-west-1` (US West - N. California)
- `63klabs-orbit-us-west-2` (US West - Oregon)

Admins must supply their own bucket if deploying outside these regions.

#### S3ModuleNamespace

Namespace prefix within the S3 module bucket. This is the path prefix where modules are stored. Modules are loaded from `s3://<BucketName>/<S3ModuleNamespace>/templates/v2/modules/*`.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | atlantis |
| Allowed Pattern | `^[a-z0-9][a-z0-9\-]*(/[a-z0-9][a-z0-9\-]*)*$` |
| Min Length | 1 |
| Max Length | 128 |
| Constraint Description | Must be 1 to 128 characters containing only lowercase alphanumeric characters, hyphens, and forward slashes. Must not start or end with a slash. Each segment between slashes must start with a lowercase alphanumeric character. |

## Resources

- [CloudFormationCodeBuildPolicy](#cloudformationcodebuildpolicy) - AWS::IAM::ManagedPolicy (via AWS::Include)
- [CloudFormationCognitoPolicy](#cloudformationcognitopolicy) - AWS::IAM::ManagedPolicy (via AWS::Include)
- [GitHubConnection](#githubconnection) - AWS::CodeStarConnections::Connection (Conditional: HasGitHubOrg, via AWS::Include)
- [ApiGatewayCloudWatchLogsRole](#apigatewaycloudwatchlogsrole) - AWS::IAM::Role (Conditional: EnableApiGatewayLogging, via AWS::Include)
- [ApiGatewayAccount](#apigatewayaccount) - AWS::ApiGateway::Account (Conditional: EnableApiGatewayLogging, via AWS::Include)
- [BedrockModelInvocationLogGroup](#bedrockModelInvocationLogGroup) - AWS::Logs::LogGroup (Conditional: EnableBedrockInvocationLogs, via AWS::Include)
- [BedrockCloudWatchLogsRole](#bedrockcloudwatchlogsrole) - AWS::IAM::Role (Conditional: EnableBedrockInvocationLogs, via AWS::Include)
- [AccessLogBucketRegional](#accesslogbucketregional) - AWS::S3::Bucket (Conditional: EnableS3AccessLogBucket, via AWS::Include)
- [AccessLogBucketPolicy](#accesslogbucketpolicy) - AWS::S3::BucketPolicy (Conditional: EnableS3AccessLogBucket, via AWS::Include)
- [S3ArtifactsBucketRegional](#s3artifactsbucketregional) - AWS::S3::Bucket (Conditional: EnableS3ArtifactsBucket, via AWS::Include)
- [S3ArtifactBucketPolicy](#s3artifactbucketpolicy) - AWS::S3::BucketPolicy (Conditional: EnableS3ArtifactsBucket, via AWS::Include)

### CloudFormationCodeBuildPolicy

Type: AWS::IAM::ManagedPolicy (via AWS::Include)

ABAC-scoped managed policy granting CodeBuild and CloudWatch Logs CRUD permissions. Scoped via the `atlantis:ApplicationDeploymentId` tag on the principal. Attach this policy to CloudFormation service roles that need to create and manage CodeBuild projects and their associated log groups.

**Module Source:** `templates/v2/modules/pipeline-policies/codebuild-crud.yml`

### CloudFormationCognitoPolicy

Type: AWS::IAM::ManagedPolicy (via AWS::Include)

ABAC-scoped managed policy granting Cognito User Pool CRUD permissions. Scoped via the `atlantis:ApplicationDeploymentId` tag on the principal. Attach this policy to CloudFormation service roles that need to manage Cognito User Pools.

**Module Source:** `templates/v2/modules/pipeline-policies/cognito-crud.yml`

### GitHubConnection

Type: AWS::CodeStarConnections::Connection (via AWS::Include)  
Condition: HasGitHubOrg

Creates a shared GitHub connection via AWS CodeConnections. This connection is used by pipeline templates as the source provider for GitHub repositories. The connection requires manual authorization in the AWS Console after creation.

**Module Source:** `templates/v2/modules/account-wide/codeconnections-github.yml`

> **Manual Step Required:** After deployment, navigate to AWS Console → Developer Tools → Connections and complete the pending connection authorization with your GitHub account.

### ApiGatewayCloudWatchLogsRole

Type: AWS::IAM::Role (via AWS::Include)  
Condition: EnableApiGatewayLogging

Creates an IAM role that allows API Gateway to push logs to CloudWatch. This is a one-time, per-account, per-region configuration.

**Module Source:** `templates/v2/modules/account-wide/apigw-cloudwatch-role.yml`

### ApiGatewayAccount

Type: AWS::ApiGateway::Account (via AWS::Include)  
Condition: EnableApiGatewayLogging  
DependsOn: ApiGatewayCloudWatchLogsRole

Configures the API Gateway account settings to use the CloudWatch logging role. This enables all API Gateway stages in the account/region to push execution and access logs to CloudWatch.

**Module Source:** `templates/v2/modules/account-wide/apigw-cloudwatch-account.yml`

### BedrockModelInvocationLogGroup

Type: AWS::Logs::LogGroup (via AWS::Include)  
Condition: EnableBedrockInvocationLogs

CloudWatch Logs destination for Amazon Bedrock model invocation logs. Once model invocation logging is activated, Bedrock writes records to the log stream `aws/bedrock/modelinvocations` within this log group.

**Key Configuration:**
- **Log Group Name:** `/aws/bedrock/{OrgPrefix}-ModelInvocations`
- **DeletionPolicy / UpdateReplacePolicy:** Retain — invocation logs are audit records containing prompt and response content and must survive stack deletion or feature disablement. This intentionally differs from the pipeline log group modules, which use Delete.
- **RetentionInDays:** Controlled by the `BedrockInvocationLogExpirationInDays` parameter (default 180 days)
- **KMS Encryption:** Optional — applied when `BedrockInvocationLogKmsKeyArn` is non-empty (condition `HasBedrockInvocationLogKmsKey`)

**Module Source:** `templates/v2/modules/account-wide/bedrock-cloudwatch-log-group.yml`

> **Activation required:** Creating this log group does **not** enable model invocation logging. Run `aws bedrock put-model-invocation-logging-configuration` with the `BedrockModelInvocationLoggingEnableCommand` output value after deployment. See [docs/admin-ops/bedrock-model-invocation-logging.md](../../../../docs/admin-ops/bedrock-model-invocation-logging.md).

> **Re-enable conflict:** Because the log group is retained, if you disable and then re-enable this feature for the same `OrgPrefix` and region, the retained log group already exists. You must delete it manually or import it before re-enabling.

### BedrockCloudWatchLogsRole

Type: AWS::IAM::Role (via AWS::Include)  
Condition: EnableBedrockInvocationLogs

IAM role that Amazon Bedrock assumes to publish model invocation logs to the CloudWatch Logs log group. The role ARN is supplied to Bedrock via the manual activation command.

**Key Configuration:**
- **Role Name:** `{OrgPrefix}-Bedrock-CloudWatch-Role`
- **Trust Policy:** Allows `bedrock.amazonaws.com` to assume the role, conditioned on `aws:SourceAccount` and `aws:SourceArn` to prevent confused-deputy attacks. This is intentionally tighter than the API Gateway CloudWatch role.
- **Inline Policy:** Grants exactly `logs:CreateLogStream` and `logs:PutLogEvents`, scoped to the specific log group and the `aws/bedrock/modelinvocations` log stream.
- **No DependsOn:** The inline policy constructs the log group ARN from parameters rather than via `Fn::GetAtt`, so the two resources are independent.

**Module Source:** `templates/v2/modules/account-wide/bedrock-cloudwatch-role.yml`

### AccessLogBucketRegional

Type: AWS::S3::Bucket (via AWS::Include)  
Condition: EnableS3AccessLogBucket

Creates a shared, account-wide S3 bucket for storing S3 server access logs (and optionally legacy CloudFront standard logs). Unlike the standalone `template-storage-s3-access-logs.yml`, this bucket drops the Prefix and ProjectId naming tokens, yielding one shared access log bucket per account/region.

**Key Configuration:**
- **Bucket Name:** `[S3BucketNameOrgPrefix-]access-logs-{AccountId}-{Region}-an`
- **DeletionPolicy / UpdateReplacePolicy:** Retain (logs preserved if the stack is deleted or the bucket replaced)
- **Versioning:** Suspended
- **Encryption:** AES256 server-side encryption with S3 Bucket Keys enabled
- **Public Access:** Blocked (`BlockPublicAcls` is relaxed to `false` only when `AllowLegacyCloudFrontLogs=true`)
- **Lifecycle:** `DeleteOldLogs` rule expires objects after `LogExpirationInDays` days
- **Ownership Controls:** `BucketOwnerPreferred` set only when `AllowLegacyCloudFrontLogs=true`

**Module Source:** `templates/v2/modules/s3-access-logs/s3-access-log-bucket.yml`

> **Keep in sync:** This module is the account-wide counterpart of the standalone `template-storage-s3-access-logs.yml`. See `.kiro/steering/s3-access-logs-module-sync.md`.

### AccessLogBucketPolicy

Type: AWS::S3::BucketPolicy (via AWS::Include)  
Condition: EnableS3AccessLogBucket

Bucket policy for the shared access log bucket. Enforces HTTPS-only access, grants the S3 log delivery service permission to write logs, and (optionally) grants the CloudFront log delivery service.

**Policy Statements:**
| Statement | Effect | Principal | Condition | Actions |
|-----------|--------|-----------|-----------|---------|
| DenyNonSecureTransportAccess | Deny | * | SecureTransport=false | s3:* |
| AllowS3LogDelivery | Allow | logging.s3.amazonaws.com | aws:SourceAccount = {AccountId} | s3:PutObject |
| AllowCloudFrontLogDelivery (Conditional: EnableLegacyCloudFrontLogs) | Allow | delivery.logs.amazonaws.com | s3:x-amz-acl = bucket-owner-full-control | s3:PutObject |

**Module Source:** `templates/v2/modules/s3-access-logs/s3-access-log-bucket-policy.yml`

### S3ArtifactsBucketRegional

Type: AWS::S3::Bucket (via AWS::Include)  
Condition: EnableS3ArtifactsBucket

Creates a shared S3 artifacts bucket for pipeline build artifacts. The bucket is accessible by all pipeline roles in the account regardless of prefix.

**Key Configuration:**
- **Bucket Name:** `[S3BucketNameOrgPrefix-]cf-artifacts-{AccountId}-{Region}-an`
- **DeletionPolicy:** Retain (preserves artifacts if stack is deleted)
- **Versioning:** Enabled
- **Encryption:** AES256 server-side encryption
- **Public Access:** Fully blocked (all four public access blocks enabled)
- **Ownership Controls:** `BucketOwnerEnforced` (ACLs disabled; bucket owner owns all objects, including those written by other accounts during promotion)
- **Lifecycle:** Objects expire after 395 days, noncurrent versions after 365 days, incomplete multipart uploads abort after 1 day
- **Logging:** Server access logging destination follows this precedence — (1) an explicit `S3LogBucketName` wins; (2) otherwise the account-wide access log bucket (`AccessLogBucketRegional`) when `EnableS3AccessLogBucket=true`; (3) otherwise no logging. Logs are written under the `cf-artifacts/` prefix.
- **Notifications (Conditional: EnablePromotionTrigger):** When `EnablePromotionTrigger='true'`, EventBridge notifications are enabled on the bucket (`EventBridgeEnabled: true`) so a receiving pipeline's `PromotionSourceEvent` rule can react to newly written promotion artifacts. When `'false'`, no `NotificationConfiguration` is set.

**Module Source:** `templates/v2/modules/account-wide/s3-artifacts-bucket.yml`

> **Ordering:** When the artifacts bucket logs to the account-wide access log bucket, the `Ref: AccessLogBucketRegional` in its logging configuration creates an implicit dependency so the log bucket is created first. That reference exists only in that branch, so with the feature off there is no dependency on the (uncreated) log resources.

### S3ArtifactBucketPolicy

Type: AWS::S3::BucketPolicy (via AWS::Include)  
Condition: EnableS3ArtifactsBucket

Bucket policy for the shared S3 artifacts bucket. Enforces HTTPS-only access and grants permissions to all pipeline service roles in the account using condition-based principal matching.

**Policy Statements:**
| Statement | Effect | Principal | Condition | Actions |
|-----------|--------|-----------|-----------|---------|
| DenyNonSecureTransportAccess | Deny | * | SecureTransport=false | s3:* |
| WhitelistedGet | Allow | * | ArnLike on aws:PrincipalArn (CodePipeline/CodeBuild/CloudFormation roles) | s3:GetObject, s3:GetObjectVersion, s3:GetBucketVersioning |
| WhitelistedPut | Allow | * | ArnLike on aws:PrincipalArn (CodePipeline/CodeBuild roles) | s3:PutObject |
| AllowCrossAccountPromotionWrite (Conditional: HasPromotionSourceAccounts) | Allow | AWS: `PromotionSourceAccountIds` | StringLike on aws:PrincipalArn (`arn:aws:iam::*:role/*-PromoteServiceRole`) | s3:PutObject, s3:GetObject, s3:GetObjectVersion (scoped to `promotions/*`) |

**Access Control Mechanism:**

The WhitelistedGet and WhitelistedPut statements use `Principal: "*"` with `aws:PrincipalArn` `ArnLike` conditions to match pipeline service roles by suffix convention. This approach does not require the roles to exist at policy creation time, allowing the account-wide infrastructure to be deployed before any project pipelines.

**ArnLike Condition Patterns (role suffix convention):**
- `arn:aws:iam::{AccountId}:role{RolePath}*-CodePipelineServiceRole`
- `arn:aws:iam::{AccountId}:role{RolePath}*-CodeBuildServiceRole`
- `arn:aws:iam::{AccountId}:role{RolePath}*-CloudFormationSvcRole` (WhitelistedGet only)

**Module Source:** `templates/v2/modules/account-wide/s3-artifacts-bucket-policy.yml`

> **Note:** Unlike the per-project `template-storage-s3-artifacts.yml`, this bucket policy uses suffix wildcard patterns (`*-RoleType`), granting access to ALL pipeline roles in the account regardless of their Prefix. This is intentional for account-wide shared usage. The condition-based approach (`Principal: "*"` with `ArnLike`) avoids "Invalid principal in policy" errors that occur when named principals don't yet exist.

> **Cross-account promotion:** The `AllowCrossAccountPromotionWrite` statement is additive and only appears when `PromotionSourceAccountIds` is non-empty (condition `HasPromotionSourceAccounts`). It is the receiving-account counterpart to the `PromoteServiceRole` created by `template-pipeline-s3-source.yml` and the origin pipeline templates (`template-pipeline.yml`, `template-pipeline-github.yml`, `template-pipeline-build-only.yml`) — write access is confined to the `promotions/*` prefix, and only for principals matching `*-PromoteServiceRole`.

## Outputs

### CodeBuildCrudPolicyArn

ARN of the CodeBuild CRUD managed policy. Pass this to pipeline templates via the `CloudFormationSvcRoleIncludeManagedPolicyArns` parameter.

| Attribute | Value |
|-----------|-------|
| Export Name | `{OrgPrefix}-ProjectPipeline-CodeBuildCrud-Arn` |
| Example Value | `arn:aws:iam::123456789012:policy/ACME-ProjectPipeline-CodeBuildCrud` |

### CodeBuildCrudPolicyName

Name of the CodeBuild CRUD managed policy.

| Attribute | Value |
|-----------|-------|
| Example Value | `ACME-ProjectPipeline-CodeBuildCrud` |

### CognitoCrudPolicyArn

ARN of the Cognito CRUD managed policy. Pass this to pipeline templates via the `CloudFormationSvcRoleIncludeManagedPolicyArns` parameter.

| Attribute | Value |
|-----------|-------|
| Export Name | `{OrgPrefix}-ProjectPipeline-CognitoCrud-Arn` |
| Example Value | `arn:aws:iam::123456789012:policy/ACME-ProjectPipeline-CognitoCrud` |

### CognitoCrudPolicyName

Name of the Cognito CRUD managed policy.

| Attribute | Value |
|-----------|-------|
| Example Value | `ACME-ProjectPipeline-CognitoCrud` |

### GitHubConnectionArn

Condition: HasGitHubOrg

ARN of the GitHub connection. Pass this to pipeline templates via the `GitHubConnectionArn` parameter.

| Attribute | Value |
|-----------|-------|
| Export Name | `{OrgPrefix}-GitHub-Connection-Arn` |
| Example Value | `arn:aws:codeconnections:us-east-1:123456789012:connection/abc123-def456-789` |

> **Note:** You must manually complete the connection in the AWS Console before it can be used by pipeline templates.

### GitHubConnectionStatus

Condition: HasGitHubOrg

Status of the GitHub connection. Will show PENDING until manually authorized in the AWS Console.

| Attribute | Value |
|-----------|-------|
| Example Value | `PENDING` or `AVAILABLE` |

### CodeConnectionsConsole

Condition: HasGitHubOrg

URL to complete the GitHub connection setup in the AWS Console.

| Attribute | Value |
|-----------|-------|
| Example Value | `https://us-east-1.console.aws.amazon.com/codesuite/settings/connections` |

### ApiGatewayCloudWatchLogsRoleArn

Condition: EnableApiGatewayLogging

ARN of the IAM role used by API Gateway to push logs to CloudWatch.

| Attribute | Value |
|-----------|-------|
| Export Name | `{OrgPrefix}-ApiGateway-CloudWatch-Role-Arn` |
| Example Value | `arn:aws:iam::123456789012:role/ACME-ApiGateway-CloudWatchLogs` |

### BedrockModelInvocationLogGroupName

Condition: EnableBedrockInvocationLogs

Name of the CloudWatch log group that receives Bedrock model invocation logs. Supply this as `cloudWatchConfig.logGroupName` when running the activation command.

| Attribute | Value |
|-----------|-------|
| Export Name | `{OrgPrefix}-Bedrock-CloudWatch-LogGroup-Name` |
| Example Value | `/aws/bedrock/ACME-ModelInvocations` |

### BedrockModelInvocationLogGroupArn

Condition: EnableBedrockInvocationLogs

ARN of the CloudWatch log group that receives Bedrock model invocation logs.

| Attribute | Value |
|-----------|-------|
| Export Name | `{OrgPrefix}-Bedrock-CloudWatch-LogGroup-Arn` |
| Example Value | `arn:aws:logs:us-east-1:123456789012:log-group:/aws/bedrock/ACME-ModelInvocations:*` |

### BedrockCloudWatchLogsRoleArn

Condition: EnableBedrockInvocationLogs

ARN of the IAM role Amazon Bedrock assumes to publish model invocation logs to CloudWatch. Supply this as `cloudWatchConfig.roleArn` when running the activation command.

| Attribute | Value |
|-----------|-------|
| Export Name | `{OrgPrefix}-Bedrock-CloudWatch-Role-Arn` |
| Example Value | `arn:aws:iam::123456789012:role/ACME-Bedrock-CloudWatch-Role` |

### BedrockModelInvocationLoggingEnableCommand

Condition: EnableBedrockInvocationLogs

Ready-to-run `--logging-config` JSON payload for the activation CLI command, with the log group name and role ARN already substituted. Copy this value and run:

```bash
aws bedrock put-model-invocation-logging-configuration \
  --region <REGION> \
  --logging-config '<this output value>'
```

Text and embedding delivery are enabled; image and video are disabled by default. See [docs/admin-ops/bedrock-model-invocation-logging.md](../../../../docs/admin-ops/bedrock-model-invocation-logging.md) for details on changing the delivery flags.

| Attribute | Value |
|-----------|-------|
| Export | None (not exported) |

> **Required manual step:** This stack output contains the activation payload but does **not** run the command for you. Model invocation logging remains disabled until the command is executed.

### BedrockModelInvocationLogGroupConsole

Condition: EnableBedrockInvocationLogs

Direct link to the Bedrock model invocation log group in the CloudWatch Logs console.

| Attribute | Value |
|-----------|-------|
| Export | None (not exported) |
| Example Value | `https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/...` |

### S3ArtifactsBucketName

Condition: EnableS3ArtifactsBucket

Name of the S3 artifacts bucket for pipeline build artifacts.

| Attribute | Value |
|-----------|-------|
| Export Name | `{OrgPrefix}-S3-Artifacts-Bucket-Name` |
| Example Value | `acme-cf-artifacts-123456789012-us-east-1-an` |

### S3ArtifactsBucketConsole

Condition: EnableS3ArtifactsBucket

S3 console link for the artifacts bucket.

| Attribute | Value |
|-----------|-------|
| Example Value | `https://s3.console.aws.amazon.com/s3/buckets/acme-cf-artifacts-123456789012-us-east-1-an` |

### S3AccessLogBucketName

Condition: EnableS3AccessLogBucket

Name of the account-wide S3 access log bucket.

| Attribute | Value |
|-----------|-------|
| Export Name | `{OrgPrefix}-S3-AccessLog-Bucket-Name` |
| Example Value | `acme-access-logs-123456789012-us-east-1-an` |

### S3AccessLogBucketArn

Condition: EnableS3AccessLogBucket

ARN of the account-wide S3 access log bucket.

| Attribute | Value |
|-----------|-------|
| Export Name | `{OrgPrefix}-S3-AccessLog-Bucket-Arn` |
| Example Value | `arn:aws:s3:::acme-access-logs-123456789012-us-east-1-an` |

### S3AccessLogBucketConsole

Condition: EnableS3AccessLogBucket

S3 console link for the access log bucket.

| Attribute | Value |
|-----------|-------|
| Example Value | `https://s3.console.aws.amazon.com/s3/buckets/acme-access-logs-123456789012-us-east-1-an` |

### IamPoliciesConsole

IAM Policies console link for quick access to view created policies.

| Attribute | Value |
|-----------|-------|
| Example Value | `https://console.aws.amazon.com/iam/home#/policies` |

## Conditions

| Condition | Logic | Purpose |
|-----------|-------|---------|
| HasGitHubOrg | GitHubOrg ≠ "" | Controls GitHub connection creation |
| EnableApiGatewayLogging | EnableApiGwCloudWatchLogs = "true" | Controls API Gateway CloudWatch role and account configuration |
| EnableS3ArtifactsBucket | EnableS3ArtifactsBucket = "true" | Controls S3 artifacts bucket and policy creation |
| UseS3BucketNameOrgPrefix | S3BucketNameOrgPrefix ≠ "" | Determines if org prefix is prepended to bucket names |
| HasLoggingBucket | S3LogBucketName ≠ "" | Determines if an explicit external log bucket overrides the shared access log bucket |
| EnableS3AccessLogBucket | EnableS3AccessLogBucket = "true" | Controls access log bucket and policy creation |
| EnableLegacyCloudFrontLogs | AllowLegacyCloudFrontLogs = "true" | Enables legacy CloudFront logging support on the access log bucket |
| HasPromotionSourceAccounts | PromotionSourceAccountIds ≠ "" | Controls creation of the `AllowCrossAccountPromotionWrite` bucket policy statement |
| EnablePromotionTrigger | EnablePromotionTrigger = "true" | Enables EventBridge notifications on the artifacts bucket for promotion receivers |
| EnableBedrockInvocationLogs | EnableBedrockInvocationLogs = "true" | Controls creation of the Bedrock log group and CloudWatch role |
| HasBedrockInvocationLogKmsKey | BedrockInvocationLogKmsKeyArn ≠ "" | Applies KMS encryption to the Bedrock log group when a key ARN is supplied |

## Examples

### Minimal Deployment (Policies Only)

Deploy with just the mandatory parameters to get ABAC-scoped managed policies:

```
OrgPrefix: ACME
RolePath: /
S3ModuleLocation: 63klabs-atlas-us-east-1
S3ModuleNamespace: atlantis
```

### Full Deployment with All Features

Enable all optional features:

```
OrgPrefix: ACME
RolePath: /service-roles/
GitHubOrg: my-github-org
EnableApiGwCloudWatchLogs: true
EnableS3ArtifactsBucket: true
S3BucketNameOrgPrefix: acme
EnableS3AccessLogBucket: true
LogExpirationInDays: 90
AllowLegacyCloudFrontLogs: false
S3ModuleLocation: 63klabs-atlas-us-east-1
S3ModuleNamespace: atlantis
```

This creates the artifacts bucket `acme-cf-artifacts-123456789012-us-east-1-an` and the access log bucket `acme-access-logs-123456789012-us-east-1-an`, and the artifacts bucket automatically logs to the access log bucket (under the `cf-artifacts/` prefix). To instead send artifacts logs to a pre-existing external bucket, set `S3LogBucketName` (which takes precedence) and leave `EnableS3AccessLogBucket` as needed.

### S3 Access Log Bucket Only

Enable just the shared access log bucket (for example, to reference it from other stacks via its exports):

```
OrgPrefix: ACME
RolePath: /
EnableS3AccessLogBucket: true
S3BucketNameOrgPrefix: acme
S3ModuleLocation: 63klabs-atlas-us-east-1
S3ModuleNamespace: atlantis
```

This creates: `acme-access-logs-123456789012-us-east-1-an`

### S3 Artifacts Bucket Only

Enable just the shared artifacts bucket:

```
OrgPrefix: ACME
RolePath: /
EnableS3ArtifactsBucket: true
S3BucketNameOrgPrefix: acme
S3ModuleLocation: 63klabs-atlas-us-east-1
S3ModuleNamespace: atlantis
```

This creates: `acme-cf-artifacts-123456789012-us-east-1-an`

### Artifacts Bucket as a Cross-Account Promotion Receiver

Enable the artifacts bucket, allow a source account to write promoted artifacts into `promotions/*`, and turn on the EventBridge trigger so a `template-pipeline-s3-source.yml` receiving pipeline in this account starts automatically:

```
OrgPrefix: ACME
RolePath: /
EnableS3ArtifactsBucket: true
S3BucketNameOrgPrefix: acme
PromotionSourceAccountIds: 111122223333
EnablePromotionTrigger: true
S3ModuleLocation: 63klabs-atlas-us-east-1
S3ModuleNamespace: atlantis
```

This grants the `111122223333` account's `*-PromoteServiceRole` roles write/read access scoped to `promotions/*` in `acme-cf-artifacts-123456789012-us-east-1-an`, and enables S3 EventBridge notifications so a receiving pipeline's `PromotionSourceEvent` rule can start on arrival. `PromotionSourceAccountIds` accepts a comma-delimited list, so multiple sending accounts can be listed at once.

## Related Templates

- **[template-storage-s3-artifacts](../storage/template-storage-s3-artifacts-README.md)**: Per-project, prefix-scoped S3 artifacts bucket (alternative to the account-wide bucket)
- **[template-storage-s3-access-logs](../storage/template-storage-s3-access-logs-README.md)**: The standalone, prefix + project scoped S3 access-logs template. It is the canonical reference for the access-log resource definitions and remains unchanged; the modules consumed here are its account-wide, condition-aware counterparts
- **[template-service-role-pipeline](../service-role/template-service-role-pipeline-README.md)**: Per-project service roles that use the managed policies exported by this template
- **[template-pipeline-github](../pipeline/template-pipeline-github-README.md)**: CI/CD pipeline that references the GitHub connection and managed policy exports
- **[template-pipeline](../pipeline/template-pipeline-README.md)** / **[template-pipeline-build-only](../pipeline/template-pipeline-build-only-README.md)**: Origin pipelines whose optional Promote stage writes to this template's artifacts bucket when `PromotionSourceAccountIds`/`EnablePromotionTrigger` are configured
- **[template-pipeline-s3-source](../pipeline/template-pipeline-s3-source-README.md)**: Receiving pipeline triggered by the `EnablePromotionTrigger` EventBridge notification on the artifacts bucket

## Troubleshooting

### Module Loading Fails

- Verify the `S3ModuleLocation` bucket exists and is accessible from the deploying account
- Check that `S3ModuleNamespace` matches the path structure in the bucket
- Ensure the CloudFormation service role has `s3:GetObject` permission on the module bucket

### GitHub Connection Stays PENDING

- Navigate to AWS Console → Developer Tools → Connections
- Click on the pending connection and complete authorization with your GitHub account
- The connection status output will update on the next stack update

### S3 Bucket Name Already Exists

- S3 bucket names are globally unique — if the name is taken, add or change the `S3BucketNameOrgPrefix`
- The bucket name pattern is: `[S3BucketNameOrgPrefix-]cf-artifacts-{AccountId}-{Region}-an`

### Managed Policy Limit Reached

- AWS accounts have a default limit of 1500 managed policies
- If you hit this limit, request an increase via AWS Support

### Stack Deletion with Retained Resources

- The S3 artifacts bucket uses `DeletionPolicy: Retain` — it will NOT be deleted when the stack is deleted
- You must manually delete the bucket after stack deletion if no longer needed
- This protects pipeline artifacts needed for rollbacks

### S3 Bucket Policy "Invalid principal in policy" Error

- This error occurs when a bucket policy uses named `Principal.AWS` ARNs that reference IAM roles not yet created
- The account-wide infrastructure template avoids this by using `Principal: "*"` with `aws:PrincipalArn` `ArnLike` conditions
- If you encounter this error with an older module version, update to the latest `s3-artifacts-bucket-policy.yml` module which uses the condition-based principal approach
- The corrected patterns use the role suffix convention: `*-CodePipelineServiceRole`, `*-CodeBuildServiceRole`, `*-CloudFormationSvcRole`
