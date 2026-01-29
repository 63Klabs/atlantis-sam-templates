# template-storage-s3-oac-for-cloudfront

CloudFront distribution with S3 origin access control (OAC). Supports external invalidator services via S3 event notifications - Deployed using SAM

**Version:** v0.1.0/2025-12-08  
**Template:** [templates/v2/storage/template-storage-s3-oac-for-cloudfront.yml](../../../templates/v2/storage/template-storage-s3-oac-for-cloudfront.yml)

## Overview

This template creates an S3 bucket configured for use as a CloudFront origin with Origin Access Control (OAC). It includes support for external CloudFront cache invalidation services via S3 event notifications, allowing automatic cache invalidation when objects are created, modified, or deleted.

### Use Cases

- Serve static websites through CloudFront with secure S3 access
- Host single-page applications (SPAs) with CloudFront distribution
- Store and serve static assets (images, CSS, JavaScript) via CDN
- Automatic CloudFront cache invalidation when content changes
- Multi-stage deployments with separate S3 paths per stage

### Prerequisites

- CloudFormation Service Role with appropriate permissions
- CloudFront distribution (created by network templates)
- Lambda function for cache invalidation (optional, for automatic invalidation)
- S3 logging bucket (optional, for access logs)
- SNS topic for alarm notifications

### Important Notes

- Uses Origin Access Control (OAC), not the legacy Origin Access Identity (OAI)
- Bucket is deleted when stack is deleted (content is not retained)
- Access is restricted to CloudFront and CodeBuild services only
- Optional S3 event notifications trigger Lambda invalidator function
- Bucket must be tagged with "AllowInvalidationEvents: true" for invalidation support

## Parameters

### Resource Naming

- [Prefix](#prefix)
- [ProjectId](#projectid)
- [S3BucketNameOrgPrefix](#s3bucketnameorgprefix)
- [RolePath](#rolepath)

### External Resources and Alarm Notifications

- [AlarmNotificationEmail](#alarmnotificationemail)
- [PermissionsBoundaryArn](#permissionsboundaryarn)
- [S3LogBucketName](#s3logbucketname)
- [InvalidatorArn](#invalidatorarn)

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

#### RolePath

Path to use for IAM Roles and Policies.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\\/([a-zA-Z0-9-_]+[\\/])+$\|^\\/$` |
| Constraint Description | May only contain alphanumeric characters, forward slashes, underscores, and dashes. Must begin and end with a slash. |

#### AlarmNotificationEmail

Email address to send notifications to when alarms are triggered. Be sure to check the inbox as you will need to confirm the subscription.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[\\w\\-\\.]+@([\\w\\-]+\\.)+[\\w\\-]{2,4}$` |
| Constraint Description | A valid email address |

**Note:** You must confirm the SNS subscription by clicking the link in the confirmation email.

#### PermissionsBoundaryArn

Permissions Boundary is a policy attached to a role to further restrict the permissions of the role. Your organization may or may not require boundaries. If left empty, no permissions boundary will be used.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^arn:aws:iam::\\d{12}:policy\\/[\\w+=,.@\\-\\/]*[\\w+=,.@\\-]+$` |
| Constraint Description | Must be empty or a valid IAM Policy ARN |

#### S3LogBucketName

The name of the S3 bucket used for logging.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$\|^$` |
| Constraint Description | Must be a valid S3 bucket name or empty. Must be between 3 and 63 characters long. |

#### InvalidatorArn

ARN of the Lambda function providing your invalidator service for CloudFront distributions.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^arn:aws:lambda:[a-z0-9-]+:\\d{12}:function:[a-zA-Z0-9-_]+$` |
| Constraint Description | Must be empty or a valid ARN for Lambda |

**Note:** When provided, S3 event notifications will trigger this Lambda function for automatic cache invalidation.

## Resources

- [Bucket](#bucket) - AWS::S3::Bucket
- [BucketPolicy](#bucketpolicy) - AWS::S3::BucketPolicy
- [S3InvokeLambdaPermission](#s3invokelambdapermission) - AWS::Lambda::Permission (Conditional: HasInvalidatorArn)

### Bucket

Type: AWS::S3::Bucket

Creates an S3 bucket for CloudFront origin with encryption, public access blocking, and optional event notifications.

**Key Properties:**
- Bucket name: `{Prefix}-{ProjectId}-{Region}-{AccountId}` or `{OrgPrefix}-{Prefix}-{ProjectId}-{Region}-{AccountId}`
- Encryption: AES256 with bucket key enabled
- Public access: Completely blocked
- Deletion policy: Delete (content not retained when stack is deleted)
- Optional logging to specified S3 log bucket
- Optional S3 event notifications for cache invalidation
- Tag: "AllowInvalidationEvents: true" (when InvalidatorArn is provided)

**Event Notifications (when InvalidatorArn provided):**
- s3:ObjectCreated:* - Triggers invalidation when objects are created
- s3:ObjectRemoved:* - Triggers invalidation when objects are deleted
- s3:LifecycleExpiration:* - Triggers invalidation when objects expire

**Security Note:** All public access is blocked. Only CloudFront (via OAC) and CodeBuild can access the bucket.

**Cost Consideration:** Bucket key encryption reduces encryption costs. Event notifications incur Lambda invocation costs.

### BucketPolicy

Type: AWS::S3::BucketPolicy

Defines access policies for the bucket, restricting access to CloudFront and CodeBuild services.

**Key Properties:**
- Denies all non-HTTPS access
- Allows CloudFront service principal to read objects (GetObject)
- Restricts CloudFront access to distributions in the same account
- Allows CodeBuild to read, write, and delete objects
- Restricts CodeBuild access to projects matching `{Prefix}-{ProjectId}-*` pattern

**Security Note:** CloudFront access is restricted by distribution ARN pattern, and CodeBuild access is restricted by project name pattern.

### S3InvokeLambdaPermission

Type: AWS::Lambda::Permission  
Condition: HasInvalidatorArn

Grants S3 permission to invoke the external invalidator Lambda function.

**Key Properties:**
- Allows S3 service to invoke the specified Lambda function
- Restricts invocation to the same AWS account
- Restricts invocation to this specific bucket

**Operational Note:** This permission is required for S3 event notifications to trigger the Lambda function.

## Outputs

### BucketName

The S3 Bucket Name used for CloudFront Origin.

**Example Value:** `acme-webapp-us-east-1-123456789012`

**Usage:** Reference this bucket name in CloudFront origin configuration and CodeBuild projects.

### OriginBucketDomainForCloudFront

Domain to use for CloudFront S3 Origin.

**Example Value:** `acme-webapp-us-east-1-123456789012.s3.us-east-1.amazonaws.com`

**Usage:** Use this domain when configuring the CloudFront distribution's S3 origin.

### AllowedCloudFrontAndCodeBuild

Access to bucket is restricted to CloudFront (Read) and CodeBuild (CRUD) with the following atlantis:Application tag value.

**Example Value:** `acme-webapp`

**Usage:** Ensure CloudFront distributions and CodeBuild projects are tagged with this value for access.

### LoggingBucketName

Condition: HasLoggingBucket

The S3 Bucket Name used for logging.

**Example Value:** `acme-logs-us-east-1-123456789012`

**Usage:** Confirms the logging configuration for the origin bucket.

### InvalidatorArn

Condition: HasInvalidatorArn

ARN of the external invalidator service configured for S3 event notifications

**Example Value:** `arn:aws:lambda:us-east-1:123456789012:function:cloudfront-invalidator`

**Usage:** Confirms which Lambda function is handling cache invalidation.

### InvalidationEventsEnabled

Indicates whether S3 event notifications for cache invalidation are enabled

**Example Value:** `true` or `false`

**Usage:** Confirms whether automatic cache invalidation is configured.

## Examples

### Example 1: Basic CloudFront Origin Bucket

```yaml
Parameters:
  Prefix: myorg
  ProjectId: website
  AlarmNotificationEmail: ops@example.com
```

Result: Creates an S3 bucket for CloudFront origin without automatic invalidation.

### Example 2: With Automatic Cache Invalidation

```yaml
Parameters:
  Prefix: prod
  ProjectId: webapp
  AlarmNotificationEmail: ops@example.com
  InvalidatorArn: arn:aws:lambda:us-east-1:123456789012:function:cf-invalidator
```

Result: Creates an S3 bucket with automatic CloudFront cache invalidation on content changes.

### Example 3: With Logging and Custom Prefix

```yaml
Parameters:
  Prefix: ws
  ProjectId: spa
  S3BucketNameOrgPrefix: acmecorp
  AlarmNotificationEmail: devops@example.com
  S3LogBucketName: acmecorp-logs-us-east-1-123456789012
  InvalidatorArn: arn:aws:lambda:us-east-1:123456789012:function:invalidator
  RolePath: /app_role/
```

Result: Creates a fully configured origin bucket with custom naming, logging, and invalidation.

## Troubleshooting

### CloudFront Cannot Access Bucket

- Verify the CloudFront distribution has an Origin Access Control (OAC) configured
- Check that the distribution ARN matches the pattern in the bucket policy
- Ensure the CloudFront distribution is in the same AWS account
- Verify objects exist in the expected paths

### CodeBuild Cannot Upload Files

- Verify the CodeBuild project name matches the pattern `{Prefix}-{ProjectId}-*`
- Check that the CodeBuild project is in the same region and account
- Ensure HTTPS is being used for all requests

### Cache Invalidation Not Working

- Verify InvalidatorArn parameter is set correctly
- Check that the Lambda function exists and is in the same region
- Verify the S3InvokeLambdaPermission resource was created
- Check Lambda function logs for errors
- Ensure the bucket has the "AllowInvalidationEvents: true" tag

### S3 Event Notifications Not Triggering

- Verify the Lambda function has the correct permissions
- Check that S3 has permission to invoke the Lambda function
- Review CloudWatch Logs for the Lambda function
- Ensure the Lambda function is not throttling or erroring

## Related Templates

This template is designed to work with:

- **Network Templates**: CloudFront distributions that use this bucket as origin
  - `template-network-route53-cloudfront-s3-apigw.yml`
- **Pipeline Templates**: CI/CD pipelines that deploy content to this bucket
  - `template-pipeline-github.yml`
- **Storage Templates**: Logging bucket for access logs
  - `template-storage-s3-access-logs.yml`

## Additional Resources

- [CloudFront Origin Access Control](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)
- [S3 Event Notifications](https://docs.aws.amazon.com/AmazonS3/latest/userguide/NotificationHowTo.html)
- [CloudFront Cache Invalidation](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html)
- [S3 Bucket Policies](https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html)
