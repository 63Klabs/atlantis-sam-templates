# template-storage-s3-devops

S3 for storing shared and latest (non-versioned) DevOps files (buildspec, buildscripts, reusable Lambda src) - Deployed using SAM

**Version:** v0.0.1/2025-05-10  
**Template:** [templates/v2/storage/template-storage-s3-devops.yml](../../../templates/v2/storage/template-storage-s3-devops.yml)

## Overview

This template creates an S3 bucket for storing shared DevOps files that are used across multiple deployments. Ideal for storing reusable Lambda functions, buildspecs, build scripts, and other common files that utilize variables and are shared across multiple stacks and pipelines.

### Use Cases

- Store reusable Lambda function source code (e.g., CloudFront cache invalidation scripts)
- Store buildspec files used by multiple CodeBuild projects
- Store common build scripts shared across multiple pipelines
- Store CloudFormation template includes and nested stacks
- Centralize DevOps tooling and scripts

### Prerequisites

- CloudFormation Service Role with appropriate permissions
- CodeBuild project (optional, for managing bucket contents)
- S3 logging bucket (optional, for access logs)

### Important Notes

- Versioning is suspended (stores only the latest version of files)
- Objects are managed by a pipeline or manual uploads
- Access is restricted to CloudFormation and CodeBuild services
- The bucket is retained on stack deletion to preserve critical infrastructure
- No lifecycle policies (files are kept indefinitely)

## Parameters

### Resource Naming

- [Prefix](#prefix)
- [ProjectId](#projectid)
- [S3BucketNameOrgPrefix](#s3bucketnameorgprefix)

### Supporting Resources

- [BuildSourceArn](#buildsourcearn)
- [S3LogBucketName](#s3logbucketname)

---

#### Prefix

Prefix pre-pended to all resources.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | acme |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,6}[a-z0-9]$` |
| Min Length | 2 |
| Max Length | 8 |
| Constraint Description | 2 to 8 characters. Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. |

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

#### BuildSourceArn

The ARN of the CodeBuild project that will be managing objects in this bucket. It will be granted read, write, delete permissions.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^arn:aws:codebuild:[a-z0-9-]+:[0-9]{12}:project/[a-zA-Z0-9-_]+$\|^$` |
| Constraint Description | Must be a valid CodeBuild ARN or empty. |

**Note:** If not provided, you can still manually upload files to the bucket, but CodeBuild won't have write access.

#### S3LogBucketName

The name of the S3 bucket used for logging.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$\|^$` |
| Constraint Description | Must be a valid S3 bucket name or empty. Must be between 3 and 63 characters long. |

## Resources

- [Bucket](#bucket) - AWS::S3::Bucket
- [BucketPolicy](#bucketpolicy) - AWS::S3::BucketPolicy

### Bucket

Type: AWS::S3::Bucket

Creates an S3 bucket for storing shared DevOps files with encryption and public access blocking.

**Key Properties:**
- Bucket name: `{Prefix}-{ProjectId}-{Region}-{AccountId}` or `{OrgPrefix}-{Prefix}-{ProjectId}-{Region}-{AccountId}`
- Versioning: Suspended (only latest version stored)
- Encryption: AES256 with bucket key enabled
- Public access: Completely blocked
- Deletion policy: Retain (preserves critical infrastructure)
- Update replace policy: Retain (prevents accidental deletion)
- Optional logging to specified S3 log bucket

**Operational Note:** The Retain deletion policy ensures DevOps files are preserved even if the stack is deleted, which is important since these files may be referenced by other active stacks.

**Cost Consideration:** No lifecycle policies means files are kept indefinitely. Manually clean up unused files to minimize storage costs.

### BucketPolicy

Type: AWS::S3::BucketPolicy

Defines access policies for the DevOps bucket, restricting access to CloudFormation and CodeBuild services.

**Key Properties:**
- Denies all non-HTTPS access
- Allows CodeBuild (if BuildSourceArn provided) to read, write, and delete objects
- Allows CloudFormation service to read objects and list bucket
- Allows all CodeBuild projects in the account to read objects
- Access restricted by account and region

**Security Note:** CloudFormation and CodeBuild access is restricted to the same AWS account and region, preventing unauthorized access from other accounts.

## Outputs

### BucketName

The S3 Bucket Name used for CloudFront Origin.

**Example Value:** `acme-devops-us-east-1-123456789012`

**Usage:** Reference this bucket name in CloudFormation templates and CodeBuild projects that need to access shared DevOps files.

### CodeBuildSourceArn

Condition: UseBuildSourceArn

This is the Arn of CodeBuild project that manages this bucket's objects.

**Example Value:** `arn:aws:codebuild:us-east-1:123456789012:project/acme-devops-builder`

**Usage:** Confirms which CodeBuild project has write access to manage bucket contents.

### LoggingBucketName

Condition: HasLoggingBucket

The S3 Bucket Name used for logging.

**Example Value:** `acme-logs-us-east-1-123456789012`

**Usage:** Confirms the logging configuration for the DevOps bucket.

## Examples

### Example 1: Basic DevOps Bucket

```yaml
Parameters:
  Prefix: myorg
  ProjectId: devops-scripts
```

Result: Creates a DevOps bucket for manual file uploads, accessible by CloudFormation and CodeBuild.

### Example 2: With CodeBuild Management

```yaml
Parameters:
  Prefix: prod
  ProjectId: shared-devops
  BuildSourceArn: arn:aws:codebuild:us-east-1:123456789012:project/prod-devops-deployer
```

Result: Creates a DevOps bucket with a specific CodeBuild project authorized to manage contents.

### Example 3: With Logging and Custom Prefix

```yaml
Parameters:
  Prefix: ws
  ProjectId: tools
  S3BucketNameOrgPrefix: acmecorp
  S3LogBucketName: acmecorp-logs-us-east-1-123456789012
  BuildSourceArn: arn:aws:codebuild:us-east-1:123456789012:project/ws-tools-manager
```

Result: Creates a DevOps bucket with custom naming, access logging, and CodeBuild management.

## Troubleshooting

### CloudFormation Cannot Access Files

- Verify the CloudFormation stack is in the same AWS account and region
- Check that files exist in the bucket at the expected paths
- Ensure HTTPS is being used for all requests
- Verify the bucket policy allows CloudFormation service access

### CodeBuild Cannot Write Files

- Verify BuildSourceArn parameter is set correctly
- Check that the CodeBuild project ARN matches exactly
- Ensure the CodeBuild project is in the same region and account
- Verify the bucket policy includes the CodeBuild write permissions

### CodeBuild Cannot Read Files

- All CodeBuild projects in the account have read access by default
- Verify the CodeBuild project is in the same region and account
- Check that files exist in the bucket
- Ensure HTTPS is being used

### Files Not Being Deleted When Expected

- This bucket has no lifecycle policies - files are kept indefinitely
- Manually delete unused files or implement a custom cleanup process
- Consider adding lifecycle policies if automatic cleanup is needed

## Related Templates

This template is designed to work with:

- **Pipeline Templates**: Pipelines that deploy objects to this bucket
  - `template-pipeline-build-only.yml`
- **Storage Templates**: Logging bucket for access logs
  - `template-storage-s3-access-logs.yml`
- **All Templates**: Any CloudFormation template that references shared scripts or includes

## Use Case Examples

### Reusable Lambda Functions

Store Lambda function source code that's used across multiple stacks:
```yaml
# In your application template
Resources:
  InvalidatorFunction:
    Type: AWS::Lambda::Function
    Properties:
      Code:
        S3Bucket: !ImportValue myorg-devops-scripts-BucketName
        S3Key: lambda/cloudfront-invalidator.zip
```

### Shared Buildspec Files

Store buildspec files used by multiple CodeBuild projects:
```yaml
# In your pipeline template
Resources:
  CodeBuildProject:
    Type: AWS::CodeBuild::Project
    Properties:
      Source:
        Type: S3
        Location: !Sub "${DevOpsBucket}/buildspecs/standard-build.yml"
```

### Common Build Scripts

Store shell scripts used during builds:
```bash
# In your buildspec.yml
phases:
  pre_build:
    commands:
      - aws s3 cp s3://myorg-devops-us-east-1-123456789012/scripts/setup.sh .
      - chmod +x setup.sh
      - ./setup.sh
```

## Additional Resources

- [CloudFormation Template Includes](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/create-reusable-transform-function-snippets-and-add-to-your-template-with-aws-include-transform.html)
- [CodeBuild Source](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html)
- [Lambda Deployment Packages](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-package.html)
