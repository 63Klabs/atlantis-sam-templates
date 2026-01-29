# template-storage-cache-data

Shared storage for Lambda applications utilizing Cache-Data (S3/DynamoDb) - Deployed using SAM

**Version:** v0.0.14/2025-08-08  
**Template:** [templates/v2/storage/template-storage-cache-data.yml](../../../templates/v2/storage/template-storage-cache-data.yml)

## Overview

This template creates shared storage infrastructure for Lambda applications using the [@63klabs/cache-data](https://www.npmjs.com/package/@63klabs/cache-data) npm package. It provisions a DynamoDB table for metadata and an S3 bucket for cached data objects, along with an optional managed IAM policy for Lambda execution roles to access these resources.

### Use Cases

- Implement caching layer for Lambda functions to reduce API calls and improve performance
- Store and retrieve cached data with automatic expiration using DynamoDB TTL
- Cache large objects in S3 while maintaining metadata in DynamoDB
- Share cached data across multiple Lambda functions in an application

### Prerequisites

- CloudFormation Service Role with appropriate permissions
- Understanding of the @63klabs/cache-data package and its configuration requirements

### Important Notes

- DynamoDB table uses PAY_PER_REQUEST billing mode for cost-effective spiky traffic patterns
- S3 bucket lifecycle policy automatically purges old cached objects
- DynamoDB TTL automatically removes expired cache entries
- The DynamoDB table has a Delete deletion policy since cache data can be regenerated
- Lambda functions need the managed policy attached to their execution role for access

## Parameters

### Resource Naming

Parameters that define the naming convention for all resources created by this template.

- [Prefix](#prefix)
- [ProjectId](#projectid)
- [S3BucketNameOrgPrefix](#s3bucketnameorgprefix)
- [RolePath](#rolepath)

### Cache-Data Parameters

Configuration settings for the cache-data storage infrastructure.

- [CacheDataPurgeAgeOfCachedBucketObjInDays](#cachedatapurgeageofcachedbucketobjindays)

### Stack Options

Optional features that can be enabled or disabled.

- [CreateManagedLambdaExecutionRolePolicy](#createmanagedlambdaexecutionrolepolicy)

---

#### Prefix

Prefix pre-pended to all resources. This can be thought of as a Name Space used to identify ownership/access for teams, departments, etc. For example, resources named ws-* could belong to the web service team and could have IAM permissions to allow access to other ws-* resources. The Prefix must have a corresponding CloudFormation Service Role. Short, descriptive 2-6 character values work best. Due to resource naming length restrictions, length of Prefix + Project ID should not exceed 28 characters. Resources are named `<Prefix>-<ProjectId>-<StageId>-<ResourceId>`

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | acme |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,6}[a-z0-9]$` |
| Min Length | 2 |
| Max Length | 8 |
| Constraint Description | 2 to 8 characters. Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. Length of Prefix + Project ID should not exceed 28 characters. |

#### ProjectId

This is the Project or Application Identifier. If you receive 'S3 bucket name too long' errors during stack creation, then you must shorten the Project ID or use an S3 Org Prefix. Due to resource naming length restrictions, length of Prefix + Project ID should not exceed 28 characters. Resources are named `<Prefix>-<ProjectId>-<StageId>-<ResourceId>`

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,24}[a-z0-9]$` |
| Min Length | 2 |
| Max Length | 26 |
| Constraint Description | Minimum of 2 characters (suggested maximum of 20). Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. Length of Prefix + Project ID should not exceed 28 characters. |

#### S3BucketNameOrgPrefix

By default, to enforce uniqueness, buckets include account and region in the bucket name. However, due to character limits, you can specify your own S3 prefix (like an org code). This will be used in addition to the Prefix entered above. Note that this length is shared with the recommended length of 20 characters for Resource Identifiers. So if you have a 10 character S3BucketNameOrgPrefix, you are limited to 10 characters for your bucket name identifier in your templates. Buckets are named `<Prefix>-<Region>-<AccountId>-<ProjectId>-<StageId>-<ResourceId>` or `<S3OrgPrefix>-<Prefix>-<ProjectId>-<StageId>-<ResourceId>`

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,18}[a-z0-9]$\|^$` |
| Constraint Description | May be empty or 2 to 20 characters (8 or less recommended). Lower case alphanumeric and dashes. Must start and end with a letter or number. |

#### RolePath

Application Role Path to use for IAM Roles and Policies for Applications. You may wish to separate out your applications from users, or create separate paths per prefix or application. Specific paths may required by permission boundaries. Ex: /ws-hello-world-test/ or /app_role/

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\\/([a-zA-Z0-9-_]+[\\/])+$\|^\\/$` |
| Constraint Description | May only contain alphanumeric characters, forward slashes, underscores, and dashes. Must begin and end with a slash. |

#### CacheDataPurgeAgeOfCachedBucketObjInDays

Similar to CacheData_PurgeExpiredCacheEntriesInHours, but for the S3 Bucket. S3 calculates from time object is created/last modified (not accessed). This should be longer than your longest cache expiration set in custom/policies. Keeping objects in S3 for too long increases storage costs. (30 is recommended)

| Attribute | Setting |
|-----------|---------|
| Type | Number |
| Default | 15 |
| Min Value | 3 |
| Constraint Description | Choose a value of 3 days or greater. This should be slightly longer than the longest cache expiration expected |

**Cost Consideration:** Setting this value too high increases S3 storage costs. Set it slightly longer than your longest cache TTL to ensure data availability while minimizing costs.

#### CreateManagedLambdaExecutionRolePolicy

Create a managed Lambda Execution Role Policy for the Lambda function. You can set this to FALSE and use your own policy for the Lambda Execution Role.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | TRUE |
| Allowed Values | TRUE, FALSE |

## Resources

- [CacheDataDynamoDbTable](#cachedatadynamodbtable) - AWS::DynamoDB::Table
- [CacheDataS3Bucket](#cachedatas3bucket) - AWS::S3::Bucket
- [CacheDataS3BucketPolicy](#cachedatas3bucketpolicy) - AWS::S3::BucketPolicy
- [ManagedLambdaExecutionRolePolicy](#managedlambdaexecutionrolepolicy) - AWS::IAM::ManagedPolicy (Conditional: CreateManagedPolicy)

### CacheDataDynamoDbTable

Type: AWS::DynamoDB::Table

Creates a DynamoDB table for storing cache metadata with Time-To-Live (TTL) enabled. The table uses PAY_PER_REQUEST billing mode for cost-effective handling of variable traffic patterns.

**Key Properties:**
- Table name: `{Prefix}-{ProjectId}-CacheData`
- Hash key: `id_hash` (String)
- TTL attribute: `purge_ts` (automatically removes expired entries)
- Billing mode: PAY_PER_REQUEST (no capacity planning required)
- Deletion policy: Delete (cache data can be regenerated)
- Update replace policy: Retain (prevents accidental data loss during updates)

**Cost Consideration:** PAY_PER_REQUEST billing is ideal for spiky web service traffic. You only pay for actual read/write requests, with no minimum capacity charges.

**Operational Note:** The TTL feature automatically removes expired cache entries, reducing storage costs and eliminating the need for manual cleanup.

### CacheDataS3Bucket

Type: AWS::S3::Bucket

Creates an S3 bucket for storing cached data objects with encryption and lifecycle policies for automatic cleanup.

**Key Properties:**
- Bucket name: `{Prefix}-{ProjectId}-{Region}-{AccountId}` or `{OrgPrefix}-{Prefix}-{ProjectId}-{Region}-{AccountId}`
- Server-side encryption: AES256
- Public access: Completely blocked
- Lifecycle policy: Expires objects after specified days (default 15)
- Prefix restriction: Lifecycle applies only to `cache/*` path

**Security Note:** All public access is blocked. Access is restricted to Lambda functions via bucket policy.

**Cost Consideration:** Lifecycle policy automatically deletes old cached objects to minimize storage costs. Adjust CacheDataPurgeAgeOfCachedBucketObjInDays based on your caching needs.

### CacheDataS3BucketPolicy

Type: AWS::S3::BucketPolicy

Defines access policies for the cache data S3 bucket, restricting access to Lambda functions and enforcing secure transport.

**Key Properties:**
- Denies all non-HTTPS access
- Allows Lambda service principal to read, write, and delete objects in `cache/*` path
- Restricts Lambda access to functions with project ARN pattern: `arn:aws:lambda:{Region}:{AccountId}:project/{Prefix}-*`

**Security Note:** The policy enforces HTTPS-only access and restricts Lambda access to functions matching the prefix pattern.

### ManagedLambdaExecutionRolePolicy

Type: AWS::IAM::ManagedPolicy  
Condition: CreateManagedPolicy

Creates a managed IAM policy that grants Lambda execution roles the necessary permissions to access cache-data resources.

**Key Properties:**
- Policy name: `{Prefix}-{ProjectId}-ManagedLambdaExecutionRolePolicy`
- Grants S3 permissions: PutObject, GetObject, GetObjectVersion on `cache/*` path
- Grants S3 ListBucket permission on the bucket
- Grants DynamoDB permissions: GetItem, Scan, Query, BatchGetItem, PutItem, UpdateItem, BatchWriteItem
- Uses specified RolePath for organization

**Operational Note:** Attach this managed policy to your Lambda execution roles to grant access to cache-data resources. If you prefer custom policies, set CreateManagedLambdaExecutionRolePolicy to FALSE.

## Outputs

### DynamoDbWebConsole

Web console link to the DynamoDB table for easy access and monitoring.

**Example Value:** `https://console.aws.amazon.com/dynamodbv2/home?region=us-east-1#table?name=acme-myapp-CacheData`

**Usage:** Quick access to view and manage cache metadata in the AWS console.

### S3BucketWebConsole

Web console link to the S3 bucket for easy access and monitoring.

**Example Value:** `https://s3.console.aws.amazon.com/s3/buckets/acme-myapp-us-east-1-123456789012?region=us-east-1`

**Usage:** Quick access to view and manage cached objects in the AWS console.

### DynamoDbTableExport

DynamoDB Table Name

**Export Name:** `{Prefix}-CacheDataDynamoDbTable`

**Example Value:** `acme-myapp-CacheData`

**Usage:** Reference this export in other stacks or Lambda environment variables to configure the cache-data package.

### S3BucketExport

S3 Bucket Name

**Export Name:** `{Prefix}-CacheDataS3Bucket`

**Example Value:** `acme-myapp-us-east-1-123456789012`

**Usage:** Reference this export in other stacks or Lambda environment variables to configure the cache-data package.

### S3BucketArnExport

S3 Bucket ARN

**Export Name:** `{Prefix}-CacheDataS3BucketArn`

**Example Value:** `arn:aws:s3:::acme-myapp-us-east-1-123456789012`

**Usage:** Use in IAM policies or other resources that require the bucket ARN.

### DynamoDbTableArnExport

DynamoDB Table ARN

**Export Name:** `{Prefix}-CacheDataDynamoDbTableArn`

**Example Value:** `arn:aws:dynamodb:us-east-1:123456789012:table/acme-myapp-CacheData`

**Usage:** Use in IAM policies or other resources that require the table ARN.

### ManagedLambdaExecutionRolePolicyArn

Condition: CreateManagedPolicy

Managed policy ARN for Lambda Execution Role to access Cache-Data resources

**Export Name:** `{Prefix}-CacheDataManagedLambdaExecutionRolePolicy`

**Example Value:** `arn:aws:iam::123456789012:policy/app_role/acme-myapp-ManagedLambdaExecutionRolePolicy`

**Usage:** Attach this policy to Lambda execution roles that need to access cache-data resources.

## Examples

### Example 1: Basic Cache-Data Setup

```yaml
Parameters:
  Prefix: myorg
  ProjectId: api-service
  CacheDataPurgeAgeOfCachedBucketObjInDays: 30
  CreateManagedLambdaExecutionRolePolicy: TRUE
  RolePath: /app_role/
```

Result: Creates cache-data infrastructure with 30-day object retention and a managed policy for Lambda access.

### Example 2: Custom Organization Prefix

```yaml
Parameters:
  Prefix: ws
  ProjectId: webapp
  S3BucketNameOrgPrefix: acmecorp
  CacheDataPurgeAgeOfCachedBucketObjInDays: 15
  CreateManagedLambdaExecutionRolePolicy: TRUE
```

Result: Bucket named `acmecorp-ws-webapp-us-east-1-123456789012` with 15-day retention.

### Example 3: Custom IAM Policy

```yaml
Parameters:
  Prefix: myorg
  ProjectId: custom-app
  CacheDataPurgeAgeOfCachedBucketObjInDays: 45
  CreateManagedLambdaExecutionRolePolicy: FALSE
  RolePath: /custom/path/
```

Result: Creates cache-data infrastructure without the managed policy, allowing you to define custom IAM permissions.

## Troubleshooting

### Lambda Cannot Access DynamoDB or S3

- Verify the Lambda execution role has the managed policy attached (if CreateManagedLambdaExecutionRolePolicy is TRUE)
- Check that the Lambda function ARN matches the pattern `arn:aws:lambda:{Region}:{AccountId}:project/{Prefix}-*`
- Ensure the Lambda function is configured with the correct table name and bucket name from the stack outputs

### S3 Bucket Name Too Long Error

- Shorten the ProjectId parameter
- Use the S3BucketNameOrgPrefix parameter to replace the region and account ID in the bucket name
- Ensure Prefix + ProjectId length does not exceed 28 characters

### Cache Objects Not Being Purged

- Verify the lifecycle policy is enabled on the S3 bucket
- Check that cached objects are stored under the `cache/` prefix
- Confirm CacheDataPurgeAgeOfCachedBucketObjInDays is set appropriately
- Note that S3 lifecycle policies may take 24-48 hours to take effect

### DynamoDB TTL Not Removing Expired Entries

- Verify TTL is enabled on the `purge_ts` attribute
- Ensure your cache-data implementation is setting the `purge_ts` attribute correctly
- Note that DynamoDB TTL typically deletes expired items within 48 hours

## Related Templates

This template is designed to work with:

- **Application Templates**: Lambda functions that use the @63klabs/cache-data package
- **Service Role Templates**: IAM roles for CloudFormation deployments
  - `template-service-role-storage.yml`

## Additional Resources

- [@63klabs/cache-data npm package](https://www.npmjs.com/package/@63klabs/cache-data)
- [DynamoDB Time To Live](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)
- [S3 Lifecycle Configuration](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
- [DynamoDB On-Demand Pricing](https://aws.amazon.com/dynamodb/pricing/on-demand/)
