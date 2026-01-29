# template-storage-s3-artifacts

S3 for storing Artifacts for CodeBuild and CodeDeploy - Deployed using SAM

**Version:** v0.0.1/2025-05-16  
**Template:** [templates/v2/storage/template-storage-s3-artifacts.yml](../../../../templates/v2/storage/template-storage-s3-artifacts.yml)

## Overview

This template creates an S3 bucket for storing build artifacts from CodeBuild and deployment artifacts for CodeDeploy/CloudFormation. The bucket is configured with versioning, encryption, lifecycle policies, and appropriate access policies for CI/CD pipeline services.

### Use Cases

- Store CodeBuild build artifacts
- Store CodePipeline artifacts between stages
- Store CloudFormation templates and deployment packages
- Centralized artifact storage for CI/CD pipelines

### Prerequisites

- CloudFormation Service Role with appropriate permissions
- CodePipeline and/or CodeBuild projects (optional, for access control)
- S3 logging bucket (optional, for access logs)

### Important Notes

- Versioning is enabled to track artifact history
- Artifacts are automatically deleted after 2 years (730 days)
- Non-current versions are deleted after 30 days
- The bucket is deleted when the stack is deleted (artifacts are not retained)
- Access is restricted to CodePipeline, CodeBuild, and CloudFormation service roles

## Parameters

### Resource Naming

- [Prefix](#prefix)
- [ProjectId](#projectid)
- [S3BucketNameOrgPrefix](#s3bucketnameorgprefix)
- [RolePath](#rolepath)

### Supporting Resources

- [BuildSourceArn](#buildsourcearn)
- [S3LogBucketName](#s3logbucketname)

---

#### Prefix

Prefix pre-pended to all resources. Can be empty to allow account-wide access.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | acme |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,6}[a-z0-9]$\|^$` |
| Max Length | 8 |
| Constraint Description | 2 to 8 characters. Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. Can be empty. |

**Note:** This parameter allows empty strings to enable account-wide artifact bucket access.

#### ProjectId

This is the Project or Application Identifier.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,24}[a-z0-9]$` |
| Min Length | 2 |
| Max Length | 26 |
| Constraint Description | Minimum of 2 characters (suggested maximum of 20). Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. |

#### S3BucketNameOrgPrefix

Optional organization prefix for bucket naming.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,18}[a-z0-9]$\|^$` |
| Constraint Description | May be empty or 2 to 20 characters (8 or less recommended). Lower case alphanumeric and dashes. Must start and end with a letter or number. |

#### RolePath

Path to use for IAM Roles and Policies.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\\/([a-zA-Z0-9-_]+[\\/])+$\|^\\/$` |
| Constraint Description | May only contain alphanumeric characters, forward slashes, underscores, and dashes. Must begin and end with a slash. |

#### BuildSourceArn

The ARN of the CodeBuild project that will be managing objects in this bucket. It will be granted read, write, delete permissions.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^arn:aws:codebuild:[a-z0-9-]+:[0-9]{12}:project/[a-zA-Z0-9-_]+$\|^$` |
| Constraint Description | Must be a valid CodeBuild ARN or empty. |

#### S3LogBucketName

The name of the S3 bucket used for logging.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$\|^$` |
| Constraint Description | Must be a valid S3 bucket name or empty. Must be between 3 and 63 characters long. |

## Resources

- [S3ArtifactsBucket](#s3artifactsbucket) - AWS::S3::Bucket
- [S3ArtifactBucketPolicy](#s3artifactbucketpolicy) - AWS::S3::BucketPolicy

### S3ArtifactsBucket

Type: AWS::S3::Bucket

Creates an S3 bucket for storing CI/CD artifacts with versioning, encryption, and lifecycle policies.

**Key Properties:**
- Bucket name: `{OrgPrefix}-{Prefix}-cf-artifacts-{Region}-{AccountId}` or `cf-artifacts-{Region}-{AccountId}`
- Versioning: Enabled (tracks artifact history)
- Encryption: AES256
- Public access: Completely blocked
- Lifecycle rules:
  - Aborts incomplete multipart uploads after 1 day
  - Expires current versions after 730 days (2 years)
  - Expires non-current versions after 30 days
- Deletion policy: Delete (artifacts not retained when stack is deleted)
- Optional logging to specified S3 log bucket

**Cost Consideration:** Lifecycle policies automatically clean up old artifacts. Adjust retention periods based on your rollback requirements.

**Operational Note:** The 2-year retention allows for historical rollbacks while the 30-day non-current version retention balances storage costs with recent rollback needs.

### S3ArtifactBucketPolicy

Type: AWS::S3::BucketPolicy

Defines access policies for the artifacts bucket, restricting access to CI/CD service roles.

**Key Properties:**
- Denies all non-HTTPS access
- Allows CodePipeline, CodeBuild, and CloudFormation service roles to read artifacts
- Allows CodePipeline and CodeBuild service roles to write artifacts
- Access restricted by role path and prefix pattern

**Security Note:** Access is restricted to service roles matching the specified prefix and role path patterns, preventing unauthorized access.

## Outputs

### BucketName

The S3 Bucket Name used for CloudFront Origin.

**Example Value:** `acme-cf-artifacts-us-east-1-123456789012`

**Usage:** Reference this bucket name in CodePipeline and CodeBuild configurations.

### LoggingBucketName

Condition: HasLoggingBucket

The S3 Bucket Name used for logging.

**Example Value:** `acme-logs-us-east-1-123456789012`

**Usage:** Confirms the logging configuration for the artifacts bucket.

## Examples

### Example 1: Basic Artifacts Bucket

```yaml
Parameters:
  Prefix: myorg
  ProjectId: artifacts
  RolePath: /app_role/
```

Result: Creates an artifacts bucket accessible by service roles with the myorg prefix.

### Example 2: Account-Wide Artifacts Bucket

```yaml
Parameters:
  Prefix: ""
  ProjectId: shared-artifacts
  RolePath: /
```

Result: Creates an artifacts bucket accessible by all CodePipeline, CodeBuild, and CloudFormation service roles in the account.

### Example 3: With Logging and CodeBuild Access

```yaml
Parameters:
  Prefix: prod
  ProjectId: build-artifacts
  S3LogBucketName: prod-logs-us-east-1-123456789012
  BuildSourceArn: arn:aws:codebuild:us-east-1:123456789012:project/prod-builder
  RolePath: /prod/
```

Result: Creates an artifacts bucket with access logging and specific CodeBuild project access.

## Troubleshooting

### CodePipeline Cannot Access Bucket

- Verify the CodePipeline service role matches the prefix and role path patterns
- Check that the service role has the correct permissions
- Ensure HTTPS is being used for all requests

### CodeBuild Cannot Write Artifacts

- Verify the CodeBuild service role matches the prefix and role path patterns
- If using BuildSourceArn, ensure the CodeBuild project ARN is correct
- Check that the CodeBuild project is in the same region and account

### Artifacts Not Being Deleted

- Verify the lifecycle policy is enabled
- Check that artifacts are older than the expiration period (730 days for current, 30 days for non-current)
- Note that lifecycle policies may take 24-48 hours to take effect

## Related Templates

This template is designed to work with:

- **Pipeline Templates**: CI/CD pipelines that use this bucket for artifacts
  - `template-pipeline-github.yml`
  - `template-pipeline-build-only.yml`
- **Storage Templates**: Logging bucket for access logs
  - `template-storage-s3-access-logs.yml`

## Additional Resources

- [CodePipeline Artifact Stores](https://docs.aws.amazon.com/codepipeline/latest/userguide/concepts-how-it-works.html#concepts-how-it-works-artifacts)
- [S3 Versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html)
- [S3 Lifecycle Configuration](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
