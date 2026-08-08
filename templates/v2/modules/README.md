# Modules/Nested Stacks

Store nested stacks for use in your templates.

## Account-Wide Modules

Located in `templates/v2/modules/account-wide/`:

- **s3-artifacts-bucket.yml** - S3 bucket for build artifacts with lifecycle policies. Server access logging destination follows this precedence: an explicitly supplied `S3LogBucketName` wins; otherwise the account-wide access log bucket is used (when `EnableS3AccessLogBucket=true`); if neither is set, logging is not configured. Logs are written under the `cf-artifacts/` prefix.

## S3 Access-Logs Modules

Located in `templates/v2/modules/s3-access-logs/`:

S3 Access-Logs modules provide the reusable resources for a shared, account-wide S3 server access log bucket. They are the intrinsic-normalized, condition-aware, account-wide counterparts of the standalone `templates/v2/storage/template-storage-s3-access-logs.yml` template, which remains the canonical reference implementation.

- **s3-access-log-bucket.yml** - Encrypted, retained, public-access-blocked S3 bucket with a lifecycle expiration rule and optional legacy CloudFront ownership controls → consumed as `AccessLogBucketRegional` (AWS::S3::Bucket)
- **s3-access-log-bucket-policy.yml** - Bucket policy enforcing HTTPS-only access, allowing the S3 log delivery service to write logs, and optionally allowing the CloudFront log delivery service → consumed as `AccessLogBucketPolicy` (AWS::S3::BucketPolicy)

### Consuming Template

| Template | Modules Consumed | Notes |
|----------|------------------|-------|
| `templates/v2/account/account-wide-infrastructure.yml` | Both s3-access-logs modules | Gated by the `EnableS3AccessLogBucket` parameter (default `false`). In the modules the standalone `${Prefix}` and `${ProjectId}` tokens are dropped entirely, yielding one shared account-wide access log bucket. When enabled, the account-wide artifacts bucket logs to this bucket unless an explicit `S3LogBucketName` is supplied (which takes precedence). |

> **Keep in sync:** The s3-access-logs modules and the standalone `template-storage-s3-access-logs.yml` describe the same resources and MUST be kept in sync. The intentional differences are the dropped `${Prefix}`/`${ProjectId}` naming tokens, long-form intrinsics, embedded `Condition: EnableS3AccessLogBucket` keys, and parent-side outputs using the `${OrgPrefix}-` export convention. See `.kiro/steering/s3-access-logs-module-sync.md`.

## Cache-Data Modules

Located in `templates/v2/modules/cache-data/`:

Cache-Data modules provide the reusable resources for Lambda applications using the [@63klabs/cache-data](https://www.npmjs.com/package/@63klabs/cache-data) npm package. They are the intrinsic-normalized, condition-aware counterparts of the standalone `templates/v2/storage/template-storage-cache-data.yml` template, which remains the canonical reference implementation.

- **cache-dynamodb-table.yml** - DynamoDB table for cache metadata with TTL (`purge_ts`) and PAY_PER_REQUEST billing → consumed as `CacheDataDynamoDbTable` (AWS::DynamoDB::Table)
- **cache-s3-bucket.yml** - Encrypted, public-access-blocked S3 bucket with a `cache/`-prefixed lifecycle expiration rule → consumed as `CacheDataS3BucketRegional` (AWS::S3::Bucket)
- **cache-s3-bucket-policy.yml** - Bucket policy enforcing HTTPS-only access and scoping Lambda read/write/delete to `cache/*` → consumed as `CacheDataS3BucketPolicy` (AWS::S3::BucketPolicy)
- **cache-managed-lambda-policy.yml** - Managed Lambda execution-role policy granting scoped S3 and DynamoDB access → consumed as `ManagedLambdaExecutionRolePolicy` (AWS::IAM::ManagedPolicy)

### Consuming Template

| Template | Modules Consumed | Notes |
|----------|------------------|-------|
| `templates/v2/account/prefix-based-infrastructure.yml` | All 4 cache-data modules | Gated by the `EnableCacheData` parameter (default `false`); the managed policy is additionally gated by `CreateManagedCacheDataLambdaExecutionRolePolicy`. In the modules the standalone `${ProjectId}` token is replaced with the literal `cache-data`, yielding one shared cache-data resource set per Prefix. Export names remain identical to the standalone template. |

> **Keep in sync:** The cache-data modules and the standalone `template-storage-cache-data.yml` describe the same resources and MUST be kept in sync. The intentional differences are the `${ProjectId}` → `cache-data` naming substitution, long-form intrinsics, embedded `Condition:` keys, and the renamed `CreateManagedCacheDataLambdaExecutionRolePolicy` parameter. See `.kiro/steering/cache-data-module-sync.md`.

## Pipeline Modules

Located in `templates/v2/modules/pipeline/`:

Pipeline modules provide reusable CloudFormation resources for CI/CD pipeline templates via AWS::Include. These modules enable consistent pipeline infrastructure across CodeCommit and GitHub-based deployments.

### Notification Resources (5 modules)

Used by all pipeline templates (template-pipeline.yml, template-pipeline-github.yml, template-pipeline-build-only.yml):

- **pipeline-notification-topic.yml** - SNS topic for pipeline event notifications with email subscription
- **pipeline-notification-started-rule.yml** - EventBridge rule that sends notification when pipeline execution starts
- **pipeline-notification-succeeded-rule.yml** - EventBridge rule that sends notification when pipeline execution succeeds
- **pipeline-notification-failed-rule.yml** - EventBridge rule that sends notification when pipeline execution fails
- **pipeline-notification-topic-policy.yml** - SNS topic policy allowing EventBridge to publish notifications

### Source and Build Resources (5 modules)

Core pipeline resources:

- **source-event-service-role.yml** - IAM role for EventBridge to trigger pipeline execution (used by all three templates)
- **source-event-rule.yml** - EventBridge rule to detect CodeCommit repository changes (used by template-pipeline.yml and template-pipeline-build-only.yml only; GitHub template uses CodeConnections webhook)
- **codebuild-log-group.yml** - CloudWatch log group for CodeBuild project logs (used by all three templates)
- **codebuild-service-role.yml** - IAM service role for CodeBuild with S3, SSM, and logging permissions (used by all three templates)
- **codebuild-project.yml** - CodeBuild project with Amazon Linux 2023 container image (used by all three templates)

### Deployment Resources (2 modules)

Used only by full pipeline templates (template-pipeline.yml and template-pipeline-github.yml):

- **cloudformation-svc-role.yml** - IAM service role for CloudFormation to create application infrastructure
- **codedeploy-service-role.yml** - IAM service role for CodeDeploy Lambda deployments

### PostDeploy Resources (3 modules)

Optional resources for post-deployment integration tests and validation (used by template-pipeline.yml and template-pipeline-github.yml when PostDeployStageEnabled=true):

- **postdeploy-service-role.yml** - IAM service role for PostDeploy CodeBuild project
- **postdeploy-project.yml** - CodeBuild project for post-deployment tasks
- **postdeploy-log-group.yml** - CloudWatch log group for PostDeploy project logs

### Module Consumption by Template

| Template | Modules Consumed | Count |
|----------|------------------|-------|
| template-pipeline.yml | All 15 modules | 15 |
| template-pipeline-github.yml | All except source-event-rule.yml | 14 |
| template-pipeline-build-only.yml | Notification (5) + Source/Build (5) only | 10 |

### Using Pipeline Modules

Pipeline modules are referenced via AWS::Include transforms in the parent templates. Each template requires two additional parameters:

- **S3ModuleLocation** - S3 bucket name where modules are stored
- **S3ModuleNamespace** - Namespace prefix for module paths (default: "atlantis")

Modules are resolved from: `s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/pipeline/<module-name>.yml`