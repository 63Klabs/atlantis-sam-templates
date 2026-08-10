# Account Templates

Account-wide infrastructure templates for provisioning shared, account-level resources assembled from reusable modules.

## Overview

Account templates deploy resources that are shared across all projects and pipelines within an AWS account. Unlike per-project templates that use Prefix/ProjectId/StageId scoping, account-wide templates create resources accessible by all pipeline roles in the account regardless of prefix.

These templates use a modular architecture — individual resources are defined as module snippets stored in S3 and assembled into the parent template via `AWS::Include` transforms. This enables flexible, conditional provisioning of account-level infrastructure.

## Templates

### [account-wide-infrastructure](./account-wide-infrastructure-README.md)

Account-wide resources: ABAC-scoped managed policies, shared connections, optional S3 artifacts bucket, and optional shared S3 access log bucket — Assembled from reusable modules.

**Use Cases:**
- ABAC-scoped managed policies for CloudFormation service roles (CodeBuild CRUD, Cognito CRUD)
- Shared GitHub connections via AWS CodeConnections
- Account-level API Gateway CloudWatch logging configuration
- Shared S3 artifacts bucket for all pipeline roles in the account
- Shared S3 access log bucket used as the artifacts bucket's log destination (with optional legacy CloudFront logging support)

**Key Features:**
- Modular architecture using `AWS::Include` transforms for flexible resource assembly
- Conditional resource creation — enable only what you need
- ABAC-scoped policies using `atlantis:ApplicationDeploymentId` tag
- Exported outputs for cross-stack references (managed policy ARNs, connection ARNs, bucket names)
- Optional organization prefix for S3 bucket naming

**Prerequisites:**
- S3 bucket containing module snippets (S3ModuleLocation parameter)
- IAM permissions to create managed policies, connections, and S3 buckets
- (Optional) Existing S3 log bucket for artifacts bucket logging

### [prefix-based-infrastructure](./prefix-based-infrastructure-README.md)

Combined prefix-based CloudFormation service roles and managed policies for pipeline, storage, and network management, plus optional shared Cache-Data resources — Assembled from reusable modules.

**Use Cases:**
- Deploy the pipeline, storage, and network management service roles for a Prefix in a single stack
- Grant `iam:PassRole` for those service roles via prefix-scoped managed policies
- Optionally provision shared Cache-Data infrastructure (DynamoDB table, S3 bucket, bucket policy, and managed Lambda execution policy) for Lambda applications using [@63klabs/cache-data](https://www.npmjs.com/package/@63klabs/cache-data)

**Key Features:**
- Modular architecture using `AWS::Include` transforms for flexible resource assembly
- Prefix-scoped service roles restricting actions to resources named with the given Prefix
- Optional, opt-in Cache-Data resource set (gated by `EnableCacheData`, default `false`) with export names identical to the standalone `template-storage-cache-data.yml`

**Prerequisites:**
- S3 bucket containing module snippets (S3ModuleLocation parameter)
- IAM permissions to create IAM roles, managed policies, and (when Cache-Data is enabled) DynamoDB tables and S3 buckets
- An existing S3 artifacts bucket — resolved automatically from the account-wide export `${OrgPrefix}-S3-Artifacts-Bucket-Name` (set the optional `OrgPrefix` parameter), or supplied directly via the now-deprecated `S3ArtifactsBucket` override

## Common Use Cases

### Centralized Pipeline Policies

Deploy ABAC-scoped managed policies that can be attached to CloudFormation service roles across all projects. This provides consistent permissions for CodeBuild and Cognito operations without duplicating policies per project.

### GitHub Integration

Create a shared AWS CodeConnections GitHub connection that all pipeline templates can reference. The connection only needs to be authorized once in the AWS Console.

### Account-Level API Gateway Logging

Enable CloudWatch logging for API Gateway across the account with a single configuration. This is a one-time, per-account, per-region setup.

### Shared Artifacts Bucket

Provision a shared S3 artifacts bucket accessible by all pipeline roles (CodePipeline, CodeBuild, CloudFormation) in the account. This is an alternative to per-project artifacts buckets for teams that prefer centralized artifact storage.

## Architecture

```
account-wide-infrastructure.yml
├── modules/pipeline-policies/
│   ├── codebuild-crud.yml (ABAC-scoped managed policy)
│   └── cognito-crud.yml (ABAC-scoped managed policy)
├── modules/account-wide/
│   ├── codeconnections-github.yml (Conditional: HasGitHubOrg)
│   ├── apigw-cloudwatch-role.yml (Conditional: EnableApiGatewayLogging)
│   ├── apigw-cloudwatch-account.yml (Conditional: EnableApiGatewayLogging)
│   ├── s3-artifacts-bucket.yml (Conditional: EnableS3ArtifactsBucket)
│   └── s3-artifacts-bucket-policy.yml (Conditional: EnableS3ArtifactsBucket)
├── modules/s3-access-logs/
│   ├── s3-access-log-bucket.yml (Conditional: EnableS3AccessLogBucket)
│   └── s3-access-log-bucket-policy.yml (Conditional: EnableS3AccessLogBucket)
```

## Integration with Other Templates

Account templates provide foundational resources used by:

- **Pipeline Templates**: Reference exported managed policy ARNs and GitHub connection ARN
  - `template-pipeline-github.yml`
  - `template-pipeline.yml`

- **Storage Templates**: The shared artifacts bucket is an alternative to per-project `template-storage-s3-artifacts.yml`

- **Service Role Templates**: Managed policies from this template complement per-project service roles
  - `template-service-role-pipeline.yml`

## Deployment Notes

### Deployment Order

This template should be deployed **first** — before any project-specific templates that reference its exports.

### One Per Account Per Region

Deploy this template once per AWS account per region. It creates account-level resources that are shared across all projects.

### Manual Steps

- **GitHub Connection**: After deployment, you must manually authorize the GitHub connection in the AWS Console (CodeConnections → Connections → Complete pending connection)

### Conditional Resources

All optional resources are disabled by default. Enable them by setting the corresponding parameter to "true":
- `EnableApiGwCloudWatchLogs` → API Gateway CloudWatch role and account configuration
- `EnableS3ArtifactsBucket` → Shared S3 artifacts bucket and bucket policy
- `EnableS3AccessLogBucket` → Shared S3 access log bucket and bucket policy (used as the artifacts bucket's log destination)

## Additional Resources

- [AWS CloudFormation Interface Metadata](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-cloudformation-interface.html)
- [AWS CodeConnections Documentation](https://docs.aws.amazon.com/dtconsole/latest/userguide/welcome-connections.html)
- [API Gateway CloudWatch Logging](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-logging.html)
- [S3 Bucket Naming Rules](https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html)
