# template-storage-s3-access-logs

S3 for storing s3 log files - Deployed using SAM

**Version:** v0.0.2/2026-03-17  
**Template:** [templates/v2/storage/template-storage-s3-access-logs.yml](../../../../templates/v2/storage/template-storage-s3-access-logs.yml)

## Overview

This template creates an S3 bucket specifically designed for storing S3 access logs from other buckets. The bucket is configured with encryption, lifecycle policies for automatic log deletion, and appropriate bucket policies to allow S3 log delivery service access.

Optionally, the bucket can be configured to support CloudFront standard (legacy) logging by enabling ACL-based write access, setting `ObjectOwnership: BucketOwnerPreferred`, and adding a bucket policy statement for the CloudFront log delivery service (`delivery.logs.amazonaws.com`).

### Use Cases

- Centralized logging bucket for S3 access logs across multiple buckets
- Destination bucket for CloudFront standard (legacy) logging when `AllowLegacyCloudFrontLogs` is enabled
- Compliance and audit trail for S3 bucket access
- Security monitoring and analysis of S3 access patterns
- Automatic log retention management with configurable expiration

### Prerequisites

- CloudFormation Service Role with appropriate permissions
- Understanding of S3 server access logging requirements
- For CloudFront legacy logging: understanding of ACL-based log delivery requirements

### Important Notes

- The bucket is retained on stack deletion to preserve log history
- Logs are automatically deleted after the specified retention period
- The bucket policy allows S3 logging service to write logs
- All public access is blocked by default for security
- Versioning is suspended to reduce storage costs for logs
- When `AllowLegacyCloudFrontLogs` is enabled, `BlockPublicAcls` is set to `false` and `ObjectOwnership` is set to `BucketOwnerPreferred` to allow CloudFront ACL-based log delivery

## Parameters

### Resource Naming

Parameters that define the naming convention for all resources created by this template.

- [Prefix](#prefix)
- [ProjectId](#projectid)
- [S3BucketNameOrgPrefix](#s3bucketnameorgprefix)

### Log Settings

Configuration for log retention and management.

- [LogExpirationInDays](#logexpirationindays)

### CloudFront Legacy Logging

Optional support for CloudFront standard (legacy) logging.

- [AllowLegacyCloudFrontLogs](#allowlegacycloudfrontinlogs)

---

#### Prefix

Prefix pre-pended to all resources. This can be thought of as a Name Space used to identify ownership/access for teams, departments, etc. Resources are named `<Prefix>-<ProjectId>-<StageId>-<ResourceId>`

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | acme |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,6}[a-z0-9]$` |
| Min Length | 2 |
| Max Length | 8 |
| Constraint Description | 2 to 8 characters. Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. Length of Prefix + Project ID should not exceed 28 characters. |

#### ProjectId

This is the Project or Application Identifier. Resources are named `<Prefix>-<ProjectId>-<StageId>-<ResourceId>`

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,24}[a-z0-9]$` |
| Min Length | 2 |
| Max Length | 26 |
| Constraint Description | Minimum of 2 characters (suggested maximum of 20). Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. Length of Prefix + Project ID should not exceed 28 characters. |

#### S3BucketNameOrgPrefix

By default, to enforce uniqueness, buckets include account and region in the bucket name. However, due to character limits, you can specify your own S3 prefix (like an org code). Buckets are named `<Prefix>-<Region>-<AccountId>-<ProjectId>-<StageId>-<ResourceId>` or `<S3OrgPrefix>-<Prefix>-<ProjectId>-<StageId>-<ResourceId>`

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,18}[a-z0-9]$\|^$` |
| Constraint Description | May be empty or 2 to 20 characters (8 or less recommended). Lower case alphanumeric and dashes. Must start and end with a letter or number. |

#### LogExpirationInDays

The number of days to keep logs in the logging bucket. Default is 90 days.

| Attribute | Setting |
|-----------|---------|
| Type | Number |
| Default | 90 |
| Min Value | 1 |
| Max Value | 365 |
| Constraint Description | Must be between 1 and 365 days. |

**Cost Consideration:** Longer retention periods increase storage costs. Set based on your compliance and audit requirements.

#### AllowLegacyCloudFrontLogs

Set to `true` to enable legacy CloudFront standard logging support. When enabled, `BlockPublicAcls` is set to `false`, `ObjectOwnership` is set to `BucketOwnerPreferred`, and a bucket policy statement is added for the CloudFront log delivery service (`delivery.logs.amazonaws.com`). Default is `false` to maintain the current secure configuration.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | false |
| Allowed Values | `true`, `false` |

> **Important:** Enabling this parameter relaxes `BlockPublicAcls` to allow ACL grants required by CloudFront standard logging. Only enable this if you need CloudFront legacy logging support. When set to `false` (the default), the bucket retains its fully locked-down public access configuration.

## Conditions

### UseS3BucketNameOrgPrefix

Evaluates to `true` when `S3BucketNameOrgPrefix` is not empty. Controls whether the bucket name uses the organization prefix format or the default region/account format.

### EnableLegacyCloudFrontLogs

Evaluates to `true` when `AllowLegacyCloudFrontLogs` equals `"true"`. Controls the following conditional behaviors:

- `BlockPublicAcls` is set to `false` (instead of `true`)
- `OwnershipControls` with `ObjectOwnership: BucketOwnerPreferred` is added to the bucket
- A bucket policy statement allowing `delivery.logs.amazonaws.com` to perform `s3:PutObject` is added

When the condition is `false`, none of these changes are applied and the bucket behaves identically to the pre-v0.0.2 configuration.

## Resources

- [Bucket](#bucket) - AWS::S3::Bucket
- [LoggingBucketPolicy](#loggingbucketpolicy) - AWS::S3::BucketPolicy

### Bucket

Type: AWS::S3::Bucket

Creates an S3 bucket for storing access logs with encryption, lifecycle policies, and public access blocking.

**Key Properties:**
- Bucket name: `{Prefix}-{ProjectId}-{Region}-{AccountId}` or `{OrgPrefix}-{Prefix}-{ProjectId}-{Region}-{AccountId}`
- Versioning: Suspended (reduces costs for log storage)
- Encryption: AES256 with bucket key enabled
- Public access: Completely blocked by default; `BlockPublicAcls` conditionally set to `false` when `EnableLegacyCloudFrontLogs` is true
- Lifecycle rule: Automatically deletes logs after specified days
- Deletion policy: Retain (preserves logs even if stack is deleted)
- Update replace policy: Retain (prevents accidental deletion during updates)
- OwnershipControls: Conditionally set to `BucketOwnerPreferred` when `EnableLegacyCloudFrontLogs` is true (absent otherwise)

**Security Note:** All public access is blocked by default. `BlockPublicPolicy`, `IgnorePublicAcls`, and `RestrictPublicBuckets` remain `true` regardless of the `AllowLegacyCloudFrontLogs` setting. Only `BlockPublicAcls` is conditionally relaxed.

**Cost Consideration:** Bucket key encryption reduces encryption costs. Lifecycle policy automatically deletes old logs to minimize storage costs.

**Operational Note:** The Retain deletion policy ensures logs are preserved even if the CloudFormation stack is deleted, which is important for compliance and audit purposes.

### LoggingBucketPolicy

Type: AWS::S3::BucketPolicy

Defines access policies for the logging bucket, allowing S3 log delivery service to write logs while enforcing secure transport.

**Policy Statements:**

- **DenyNonSecureTransportAccess** - Denies all non-HTTPS access to the bucket
- **AllowS3LogDelivery** - Allows the S3 logging service (`logging.s3.amazonaws.com`) to write logs, restricted to the same AWS account
- **AllowCloudFrontLogDelivery** (Conditional: `EnableLegacyCloudFrontLogs`) - Allows the CloudFront log delivery service (`delivery.logs.amazonaws.com`) to perform `s3:PutObject` with the condition that `s3:x-amz-acl` equals `bucket-owner-full-control`. This statement is only present when `AllowLegacyCloudFrontLogs` is `true`.

**Security Note:** The policy enforces HTTPS-only access and restricts log delivery to the account that owns the bucket, preventing unauthorized log injection. The CloudFront log delivery statement is only added when explicitly opted in.

## Outputs

### LoggingBucketName

The S3 Bucket Name used for CloudFront Origin.

**Export Name:** `{Prefix}-{ProjectId}-LoggingBucketName`

**Example Value:** `acme-logs-us-east-1-123456789012`

**Usage:** Reference this export when configuring logging on other S3 buckets or CloudFront distributions.

### LoggingBucketArn

The S3 Bucket Arn used for CloudFront Origin.

**Export Name:** `{Prefix}-{ProjectId}-LoggingBucketArn`

**Example Value:** `arn:aws:s3:::acme-logs-us-east-1-123456789012`

**Usage:** Use in IAM policies or other resources that require the bucket ARN.

## Examples

### Example 1: Standard Logging Bucket

```yaml
Parameters:
  Prefix: myorg
  ProjectId: logs
  LogExpirationInDays: 90
```

Result: Creates a logging bucket that retains logs for 90 days. CloudFront legacy logging is disabled (default).

### Example 2: Short-Term Logging

```yaml
Parameters:
  Prefix: dev
  ProjectId: temp-logs
  LogExpirationInDays: 7
```

Result: Creates a logging bucket for development with 7-day retention.

### Example 3: Compliance Logging with Custom Prefix

```yaml
Parameters:
  Prefix: prod
  ProjectId: audit-logs
  S3BucketNameOrgPrefix: acmecorp
  LogExpirationInDays: 365
```

Result: Creates a logging bucket with 1-year retention for compliance purposes.

### Example 4: CloudFront Legacy Logging Enabled

```yaml
Parameters:
  Prefix: prod
  ProjectId: cf-logs
  LogExpirationInDays: 90
  AllowLegacyCloudFrontLogs: "true"
```

Result: Creates a logging bucket configured for both S3 access logs and CloudFront standard (legacy) logging. `BlockPublicAcls` is set to `false`, `ObjectOwnership` is `BucketOwnerPreferred`, and the CloudFront log delivery policy statement is added.

## Troubleshooting

### Logs Not Appearing in Bucket

- Verify the source bucket has logging enabled and points to this bucket
- Check that the source bucket is in the same AWS account
- Ensure the bucket policy allows the S3 logging service
- Note that log delivery can take up to an hour

### Bucket Name Too Long Error

- Shorten the ProjectId parameter
- Use the S3BucketNameOrgPrefix parameter
- Ensure Prefix + ProjectId length does not exceed 28 characters

### Logs Not Being Deleted

- Verify the lifecycle policy is enabled
- Check the LogExpirationInDays parameter value
- Note that lifecycle policies may take 24-48 hours to take effect
- Confirm logs are older than the expiration period

### Access Denied When Configuring Source Bucket Logging

- Ensure the logging bucket policy is in place
- Verify the source bucket is in the same AWS account
- Check that you have permissions to configure logging on the source bucket

### CloudFront Logging Fails with ACL Error

- Verify `AllowLegacyCloudFrontLogs` is set to `true`
- Confirm the stack has been updated after changing the parameter
- Check that the CloudFront distribution is configured to use this bucket as the logging destination
- Note that CloudFront standard logging requires ACL-based access; this is different from CloudFront real-time logging

## Related Templates

This template is designed to work with:

- **Storage Templates**: Other S3 buckets that need access logging
  - `template-storage-s3-oac-for-cloudfront.yml`
  - `template-storage-s3-artifacts.yml`
  - `template-storage-s3-devops.yml`
- **Network Templates**: CloudFront distributions that need access logging
  - `template-network-route53-cloudfront-s3-apigw.yml`

## Additional Resources

- [S3 Server Access Logging](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ServerLogs.html)
- [S3 Lifecycle Configuration](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
- [S3 Bucket Policies](https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html)
- [CloudFront Standard Logging](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/AccessLogs.html)
