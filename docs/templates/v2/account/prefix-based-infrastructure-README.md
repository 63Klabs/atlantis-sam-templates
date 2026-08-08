# prefix-based-infrastructure

Combined prefix-based IAM Service Roles and Managed Policies for Pipeline and Storage management, plus optional shared Cache-Data resources — Assembled from reusable modules.

**Version:** v0.0.0/2026-04-28  
**Template:** [templates/v2/account/prefix-based-infrastructure.yml](../../../../templates/v2/account/prefix-based-infrastructure.yml)

## Overview

This template combines the Deploy Management service roles for a single Prefix into one stack. It assembles reusable module snippets stored in S3 using `AWS::Include` transforms — the same modules used when each service role is deployed independently. It creates prefix-scoped CloudFormation service roles and managed policies for pipeline, storage, and network management, and optionally provisions a shared, prefix-wide Cache-Data resource set (DynamoDB table, S3 bucket, bucket policy, and managed Lambda execution policy).

Each management module creates a CloudFormation service role (assumed by `cloudformation.amazonaws.com`) and a managed policy that grants `iam:PassRole` for that service role. Both are prefix-scoped, restricting actions to resources named with the given Prefix.

### Use Cases

- Deploy the pipeline, storage, and network management service roles for a Prefix in a single stack
- Grant `iam:PassRole` for those service roles via prefix-scoped managed policies
- Optionally provision shared Cache-Data infrastructure (DynamoDB + S3) for Lambda applications using the [@63klabs/cache-data](https://www.npmjs.com/package/@63klabs/cache-data) npm package
- Optionally provision a managed Lambda execution-role policy scoped to the Cache-Data resources

### Prerequisites

- S3 bucket containing the Atlantis module snippets (provided by 63klabs regional buckets or your own) — see `S3ModuleLocation`
- IAM permissions to create IAM roles, managed policies, and (when Cache-Data is enabled) DynamoDB tables and S3 buckets
- An existing S3 artifacts bucket referenced by `S3ArtifactsBucket`

### Important Notes

- Module snippets are loaded from S3 at deploy time via `AWS::Include` transforms
- The Cache-Data resources are **disabled by default** — set `EnableCacheData` to `"true"` to create them
- In the Cache-Data modules, the standalone template's `${ProjectId}` token is replaced with the literal `cache-data`, yielding **one shared Cache-Data resource set per Prefix**
- Cache-Data export names are identical to the standalone `template-storage-cache-data.yml`; the `EnableCacheData` toggle ensures only one stack owns these resources per Prefix, avoiding export-name collisions
- This template is in development mode (v0.0.0) and is edited in place without a version bump

## Parameters

### Application Resource Naming

Parameters that define the naming convention for all resources created by this template.

- [Prefix](#prefix)
- [PrefixUpper](#prefixupper)
- [S3BucketNameOrgPrefix](#s3bucketnameorgprefix)
- [ServiceRolePath](#servicerolepath)
- [RolePath](#rolepath)

### External Resources

Existing resources referenced (not created) by this template.

- [PermissionsBoundaryArn](#permissionsboundaryarn)
- [S3ArtifactsBucket](#s3artifactsbucket)

### Resources to Attach Managed Policies To

Optional existing IAM principals to attach the managed policies to.

- [GroupNames](#groupnames)
- [UserNames](#usernames)
- [RoleNames](#rolenames)

### Cache-Data

Optional shared, prefix-wide Cache-Data resources for Lambda applications.

- [EnableCacheData](#enablecachedata)
- [CacheDataPurgeAgeOfCachedBucketObjInDays](#cachedatapurgeageofcachedbucketobjindays)
- [CreateManagedCacheDataLambdaExecutionRolePolicy](#createmanagedcachedatalambdaexecutionrolepolicy)

### Module Source

Configuration for where module snippets are loaded from.

- [S3ModuleLocation](#s3modulelocation)
- [S3ModuleNamespace](#s3modulenamespace)

---

#### Prefix

Prefix pre-pended to all resources. This can be thought of as a Name Space used to identify ownership/access for teams, departments, etc. The Prefix must have a corresponding CloudFormation Service Role.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | acme |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,6}[a-z0-9]$` |
| Min Length | 2 |
| Max Length | 8 |
| Constraint Description | 2 to 8 characters. Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. Length of Prefix + Project ID should not exceed 28 characters. |

#### PrefixUpper

Prefix for Service Role in all UPPER CASE. Used in exported role names.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | ACME |
| Allowed Pattern | `^[A-Z][A-Z0-9-]{0,6}[A-Z0-9]$` |
| Min Length | 2 |
| Max Length | 8 |
| Constraint Description | 2 to 8 characters. UPPER case alphanumeric and dashes. Must start with a letter and end with a letter or number. |

#### S3BucketNameOrgPrefix

By default, to enforce uniqueness, buckets include account and region in the bucket name. However, due to character limits, you can specify your own S3 prefix (like an org code). This is used in addition to the Prefix.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,18}[a-z0-9]$\|^$` |
| Constraint Description | May be empty or 2 to 20 characters (8 or less recommended). Lower case alphanumeric and dashes. Must start and end with a letter or number. |

> **Tip:** This prefix is shared by the Cache-Data S3 bucket name when Cache-Data is enabled. Keep it short to avoid exceeding the 63-character S3 bucket name limit.

#### ServiceRolePath

Path to use for the Service Roles and Managed Policies. You may wish to provide a path to organize and base permissions on.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\/([a-zA-Z0-9-_]+[\/])+$\|^\/$` |
| Constraint Description | May only contain alphanumeric characters, forward slashes, underscores, and dashes. Must begin and end with a slash. |

#### RolePath

Application Role Path to use for IAM Roles and Policies for Applications. This path is applied to the Cache-Data managed Lambda execution policy when Cache-Data is enabled.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\/([a-zA-Z0-9-_]+[\/])+$\|^\/$` |
| Constraint Description | May only contain alphanumeric characters, forward slashes, underscores, and dashes. Must begin and end with a slash. |

#### PermissionsBoundaryArn

Permissions Boundary is a policy attached to a role to further restrict the permissions of the role. If left empty, no permissions boundary will be used.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^arn:aws:iam::\d{12}:policy\/[\w+=,.@\-\/]*[\w+=,.@\-]+$` |
| Constraint Description | Must be empty or a valid IAM Policy ARN in the format: arn:aws:iam::{account_id}:policy/{policy_name} |

#### S3ArtifactsBucket

Name of the existing S3 artifacts bucket used by managed stacks. Service roles will be granted `s3:GetObject` and `s3:GetObjectVersion` on keys prefixed with `<Prefix>-*` within this bucket.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None (required) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$` |
| Min Length | 3 |
| Max Length | 63 |
| Constraint Description | Must be a valid S3 bucket name between 3 and 63 characters containing only lowercase letters, numbers, and hyphens. |

#### GroupNames

Optional. Friendly Name (not ARN) of an existing IAM Group to attach the managed policies to. If left empty, no group will be attached.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | "" (empty) |
| Allowed Pattern | `^[\w+=,_.@\-]+$\|^$` |
| Constraint Description | Must be empty or a comma delimited list of valid IAM Group names. |

#### UserNames

Optional. Friendly Name (not ARN) of an existing IAM User to attach the managed policies to. If left empty, no user will be attached.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | "" (empty) |
| Allowed Pattern | `^[\w+=,_.@\-]+$\|^$` |
| Constraint Description | Must be empty or a comma delimited list of valid IAM User names. |

#### RoleNames

Optional. Friendly Name (not ARN) of an existing IAM Role to attach the managed policies to. If left empty, no role will be attached.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | "" (empty) |
| Allowed Pattern | `^[\w+=,_.@\-]+$\|^$` |
| Constraint Description | Must be empty or a comma delimited list of valid IAM Role names. |

#### EnableCacheData

Set to `'true'` to create the shared, prefix-wide Cache-Data resources (DynamoDB table, S3 bucket, bucket policy, and optional managed Lambda execution policy). See [@63klabs/cache-data](https://www.npmjs.com/package/@63klabs/cache-data).

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | false |
| Allowed Values | true, false |
| Constraint Description | Must be 'true' or 'false'. |

> **Note:** When `false` (the default), none of the four Cache-Data resources and none of the Cache-Data outputs/exports are created — the stack has no Cache-Data footprint.

> **Single owner per Prefix:** Because export names are shared with the standalone `template-storage-cache-data.yml`, enable Cache-Data here **only if** no other stack already owns the `${Prefix}-CacheData*` exports. Only one stack per Prefix should own these resources.

#### CacheDataPurgeAgeOfCachedBucketObjInDays

Similar to `CacheData_PurgeExpiredCacheEntriesInHours`, but for the S3 Bucket. S3 calculates from the time an object is created/last modified (not accessed). This should be longer than your longest cache expiration set in custom/policies. Keeping objects in S3 for too long increases storage costs. (30 is recommended.)

| Attribute | Setting |
|-----------|---------|
| Type | Number |
| Default | 15 |
| Min Value | 3 |
| Constraint Description | Choose a value of 3 days or greater. This should be slightly longer than the longest cache expiration expected. |

> **Cost Consideration:** Setting this value too high increases S3 storage costs. Set it slightly longer than your longest cache TTL. Only applies when `EnableCacheData` is `'true'`.

#### CreateManagedCacheDataLambdaExecutionRolePolicy

Create a managed Lambda Execution Role Policy for accessing Cache-Data. Set to `FALSE` to supply your own policy for the Lambda Execution Role. Only applies when `EnableCacheData` is `'true'`. This is the renamed equivalent of the standalone template's `CreateManagedLambdaExecutionRolePolicy` parameter.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | TRUE |
| Allowed Values | TRUE, FALSE |

#### S3ModuleLocation

S3 bucket name containing module snippets. Modules are loaded from `s3://<S3ModuleLocation>/<S3ModuleNamespace>/templates/v2/modules/*`. Bucket must be in the same region as deployment.

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

All resources are assembled from module snippets via `AWS::Include`.

- [PrefixBasedCloudFormationPipelineMgmtServiceRole](#prefixbasedcloudformationpipelinemgmtservicerole) - AWS::IAM::Role (via AWS::Include)
- [PrefixBasedPipelineMgmtManagedPolicy](#prefixbasedpipelinemgmtmanagedpolicy) - AWS::IAM::ManagedPolicy (via AWS::Include)
- [PrefixBasedCloudFormationStorageMgmtServiceRole](#prefixbasedcloudformationstoragemgmtservicerole) - AWS::IAM::Role (via AWS::Include)
- [PrefixBasedStorageMgmtManagedPolicy](#prefixbasedstoragemgmtmanagedpolicy) - AWS::IAM::ManagedPolicy (via AWS::Include)
- [PrefixBasedNetworkCloudFrontMgmtPolicy](#prefixbasednetworkcloudfrontmgmtpolicy) - AWS::IAM::ManagedPolicy (via AWS::Include)
- [PrefixBasedNetworkRoute53MgmtPolicy](#prefixbasednetworkroute53mgmtpolicy) - AWS::IAM::ManagedPolicy (via AWS::Include)
- [PrefixBasedCloudFormationNetworkCloudFrontMgmtServiceRole](#prefixbasedcloudformationnetworkcloudfrontmgmtservicerole) - AWS::IAM::Role (via AWS::Include)
- [PrefixBasedNetworkCloudFrontMgmtManagedPolicy](#prefixbasednetworkcloudfrontmgmtmanagedpolicy) - AWS::IAM::ManagedPolicy (via AWS::Include)
- [PrefixBasedCloudFormationNetworkFullMgmtServiceRole](#prefixbasedcloudformationnetworkfullmgmtservicerole) - AWS::IAM::Role (via AWS::Include)
- [PrefixBasedNetworkFullMgmtManagedPolicy](#prefixbasednetworkfullmgmtmanagedpolicy) - AWS::IAM::ManagedPolicy (via AWS::Include)
- [CacheDataDynamoDbTable](#cachedatadynamodbtable) - AWS::DynamoDB::Table (Conditional: CreateCacheData, via AWS::Include)
- [CacheDataS3BucketRegional](#cachedatas3bucketregional) - AWS::S3::Bucket (Conditional: CreateCacheData, via AWS::Include)
- [CacheDataS3BucketPolicy](#cachedatas3bucketpolicy) - AWS::S3::BucketPolicy (Conditional: CreateCacheData, via AWS::Include)
- [ManagedLambdaExecutionRolePolicy](#managedlambdaexecutionrolepolicy) - AWS::IAM::ManagedPolicy (Conditional: CreateCacheDataManagedPolicy, via AWS::Include)

### PrefixBasedCloudFormationPipelineMgmtServiceRole

Type: AWS::IAM::Role (via AWS::Include)

Prefix-scoped CloudFormation service role for Pipeline Management, assumed by `cloudformation.amazonaws.com`.

**Module Source:** `templates/v2/modules/management-roles/pipeline-mgmt-role.yml`

### PrefixBasedPipelineMgmtManagedPolicy

Type: AWS::IAM::ManagedPolicy (via AWS::Include)

Managed policy granting `iam:PassRole` for the pipeline management service role.

**Module Source:** `templates/v2/modules/management-roles/pipeline-mgmt-passrole-policy.yml`

### PrefixBasedCloudFormationStorageMgmtServiceRole

Type: AWS::IAM::Role (via AWS::Include)

Prefix-scoped CloudFormation service role for Storage Management. Its S3 module read access (`S3ModuleBucketGetObject`) grants namespace-wide read, covering the `cache-data/` module path.

**Module Source:** `templates/v2/modules/management-roles/storage-mgmt-role.yml`

### PrefixBasedStorageMgmtManagedPolicy

Type: AWS::IAM::ManagedPolicy (via AWS::Include)

Managed policy granting `iam:PassRole` for the storage management service role.

**Module Source:** `templates/v2/modules/management-roles/storage-mgmt-passrole-policy.yml`

### PrefixBasedNetworkCloudFrontMgmtPolicy

Type: AWS::IAM::ManagedPolicy (via AWS::Include)

Managed policy granting CloudFront management permissions.

**Module Source:** `templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml`

### PrefixBasedNetworkRoute53MgmtPolicy

Type: AWS::IAM::ManagedPolicy (via AWS::Include)

Managed policy granting Route53 management permissions.

**Module Source:** `templates/v2/modules/management-roles/network-route53-mgmt-policy.yml`

### PrefixBasedCloudFormationNetworkCloudFrontMgmtServiceRole

Type: AWS::IAM::Role (via AWS::Include)

Prefix-scoped CloudFormation service role for CloudFront-only network management (no Route53).

**Module Source:** `templates/v2/modules/management-roles/network-cloudfront-mgmt-role.yml`

### PrefixBasedNetworkCloudFrontMgmtManagedPolicy

Type: AWS::IAM::ManagedPolicy (via AWS::Include)

Managed policy granting `iam:PassRole` for the CloudFront network management service role.

**Module Source:** `templates/v2/modules/management-roles/network-cloudfront-mgmt-passrole-policy.yml`

### PrefixBasedCloudFormationNetworkFullMgmtServiceRole

Type: AWS::IAM::Role (via AWS::Include)

Prefix-scoped CloudFormation service role for full network management (CloudFront + Route53).

**Module Source:** `templates/v2/modules/management-roles/network-full-mgmt-role.yml`

### PrefixBasedNetworkFullMgmtManagedPolicy

Type: AWS::IAM::ManagedPolicy (via AWS::Include)

Managed policy granting `iam:PassRole` for the full network management service role.

**Module Source:** `templates/v2/modules/management-roles/network-full-mgmt-passrole-policy.yml`

### CacheDataDynamoDbTable

Type: AWS::DynamoDB::Table (via AWS::Include)  
Condition: CreateCacheData

DynamoDB table for cache metadata with Time-To-Live (TTL) enabled, using PAY_PER_REQUEST billing.

**Key Configuration:**
- **Table Name:** `${Prefix}-cache-data-CacheData` (the standalone `${ProjectId}` token replaced with the literal `cache-data`)
- **Hash Key:** `id_hash` (String)
- **TTL Attribute:** `purge_ts` (enabled) — automatically removes expired entries
- **Billing Mode:** PAY_PER_REQUEST
- **UpdateReplacePolicy:** Retain
- **DeletionPolicy:** Delete (cache data can be regenerated)

**Module Source:** `templates/v2/modules/cache-data/cache-dynamodb-table.yml`

### CacheDataS3BucketRegional

Type: AWS::S3::Bucket (via AWS::Include)  
Condition: CreateCacheData

Encrypted S3 bucket for cached data objects with a lifecycle rule for automatic cleanup.

**Key Configuration:**
- **Bucket Name:** `${S3BucketNameOrgPrefix}-${Prefix}-cache-data-${AWS::AccountId}-${AWS::Region}-an` when `UseS3BucketNameOrgPrefix` is true, otherwise `${Prefix}-cache-data-${AWS::AccountId}-${AWS::Region}-an`
- **Bucket Namespace:** `account-regional`
- **Encryption:** AES256 server-side encryption
- **Public Access:** Fully blocked (all four public access blocks enabled)
- **Lifecycle:** Objects under the `cache` prefix (current and noncurrent) expire after `CacheDataPurgeAgeOfCachedBucketObjInDays` days; incomplete multipart uploads abort after 1 day

**Module Source:** `templates/v2/modules/cache-data/cache-s3-bucket.yml`

### CacheDataS3BucketPolicy

Type: AWS::S3::BucketPolicy (via AWS::Include)  
Condition: CreateCacheData

Bucket policy enforcing HTTPS-only access and scoping Lambda access to the `cache/*` path. References the bucket via `Ref: CacheDataS3BucketRegional`.

**Policy Statements:**
| Statement | Effect | Principal | Actions |
|-----------|--------|-----------|---------|
| DenyNonSecureTransportAccess | Deny | * | s3:* (when aws:SecureTransport=false) |
| AllowLambdaReadWriteDelete | Allow | lambda.amazonaws.com | s3:GetObject, s3:PutObject, s3:DeleteObject on `cache/*` (scoped via aws:SourceArn `arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:project/${Prefix}-*`) |

**Module Source:** `templates/v2/modules/cache-data/cache-s3-bucket-policy.yml`

### ManagedLambdaExecutionRolePolicy

Type: AWS::IAM::ManagedPolicy (via AWS::Include)  
Condition: CreateCacheDataManagedPolicy

Managed IAM policy granting Lambda execution roles scoped access to the Cache-Data resources. References the sibling resources `CacheDataS3BucketRegional` and `CacheDataDynamoDbTable`.

**Key Configuration:**
- **Policy Name:** `${Prefix}-cache-data-ManagedLambdaExecutionRolePolicy`
- **Path:** `RolePath`
- **S3 Permissions:** PutObject, GetObject, GetObjectVersion on `cache/*`; ListBucket on the bucket
- **DynamoDB Permissions:** GetItem, Scan, Query, BatchGetItem, PutItem, UpdateItem, BatchWriteItem on the cache table

**Module Source:** `templates/v2/modules/cache-data/cache-managed-lambda-policy.yml`

> **Operational Note:** Attach this managed policy to your Lambda execution roles to grant access to the Cache-Data resources. If you prefer a custom policy, set `CreateManagedCacheDataLambdaExecutionRolePolicy` to `FALSE`.

## Conditions

| Condition | Logic | Purpose |
|-----------|-------|---------|
| UseS3BucketNameOrgPrefix | S3BucketNameOrgPrefix ≠ "" | Determines if the org prefix is prepended to the Cache-Data bucket name |
| HasPermissionsBoundaryArn | PermissionsBoundaryArn ≠ "" | Controls whether a permissions boundary is applied to roles |
| HasGroupNames | GroupNames ≠ "" | Controls whether managed policies attach to IAM groups |
| HasRoleNames | RoleNames ≠ "" | Controls whether managed policies attach to IAM roles |
| HasUserNames | UserNames ≠ "" | Controls whether managed policies attach to IAM users |
| CreateCacheData | EnableCacheData = "true" | Gates creation of all four Cache-Data resources |
| CreateCacheDataManagedPolicy | And(CreateCacheData, CreateManagedCacheDataLambdaExecutionRolePolicy = "TRUE") | Gates creation of the Cache-Data managed Lambda execution policy |

> **One condition per resource:** CloudFormation allows a single `Condition` per resource. The managed policy therefore uses the combined `CreateCacheDataManagedPolicy` condition rather than nesting two conditions.

## Outputs

### PipelineMgmtServiceRoleArn

ARN of the prefix-based CloudFormation service role for Pipeline Management.

| Attribute | Value |
|-----------|-------|
| Export Name | `{PrefixUpper}-CloudFormation-Pipeline-Mgmt-Service-Role-Arn` |

### PipelineMgmtServiceRoleName

Name of the prefix-based CloudFormation service role for Pipeline Management.

| Attribute | Value |
|-----------|-------|
| Export Name | `{PrefixUpper}-CloudFormation-Pipeline-Mgmt-Service-Role-Name` |

### StorageMgmtServiceRoleArn

ARN of the prefix-based CloudFormation service role for Storage Management.

| Attribute | Value |
|-----------|-------|
| Export Name | `{PrefixUpper}-CloudFormation-Storage-Mgmt-Service-Role-Arn` |

### StorageMgmtServiceRoleName

Name of the prefix-based CloudFormation service role for Storage Management.

| Attribute | Value |
|-----------|-------|
| Export Name | `{PrefixUpper}-CloudFormation-Storage-Mgmt-Service-Role-Name` |

### NetworkCloudFrontMgmtServiceRoleArn

ARN of the Network CloudFront Management service role (no Route53).

| Attribute | Value |
|-----------|-------|
| Export Name | `{PrefixUpper}-CloudFormation-Network-CloudFront-Mgmt-Service-Role-Arn` |

### NetworkCloudFrontMgmtServiceRoleName

Name of the Network CloudFront Management service role.

| Attribute | Value |
|-----------|-------|
| Export Name | `{PrefixUpper}-CloudFormation-Network-CloudFront-Mgmt-Service-Role-Name` |

### NetworkFullMgmtServiceRoleArn

ARN of the Full Network Management service role (CloudFront + Route53).

| Attribute | Value |
|-----------|-------|
| Export Name | `{PrefixUpper}-CloudFormation-Network-Full-Mgmt-Service-Role-Arn` |

### NetworkFullMgmtServiceRoleName

Name of the Full Network Management service role.

| Attribute | Value |
|-----------|-------|
| Export Name | `{PrefixUpper}-CloudFormation-Network-Full-Mgmt-Service-Role-Name` |

### CacheDataDynamoDbWebConsole

Condition: CreateCacheData

Web console link to the Cache-Data DynamoDB table.

| Attribute | Value |
|-----------|-------|
| Example Value | `https://console.aws.amazon.com/dynamodbv2/home?region=us-east-1#table?name=acme-cache-data-CacheData&initialTableGroup=%23all` |

### CacheDataS3BucketWebConsole

Condition: CreateCacheData

Web console link to the Cache-Data S3 bucket.

| Attribute | Value |
|-----------|-------|
| Example Value | `https://s3.console.aws.amazon.com/s3/buckets/acme-cache-data-123456789012-us-east-1-an?region=us-east-1` |

### CacheDataDynamoDbTableExport

Condition: CreateCacheData

Cache-Data DynamoDB table name. Export name is identical to the standalone template.

| Attribute | Value |
|-----------|-------|
| Export Name | `{Prefix}-CacheDataDynamoDbTable` |
| Example Value | `acme-cache-data-CacheData` |

### CacheDataS3BucketExport

Condition: CreateCacheData

Cache-Data S3 bucket name. Export name is identical to the standalone template.

| Attribute | Value |
|-----------|-------|
| Export Name | `{Prefix}-CacheDataS3Bucket` |
| Example Value | `acme-cache-data-123456789012-us-east-1-an` |

### CacheDataS3BucketArnExport

Condition: CreateCacheData

Cache-Data S3 bucket ARN. Export name is identical to the standalone template.

| Attribute | Value |
|-----------|-------|
| Export Name | `{Prefix}-CacheDataS3BucketArn` |
| Example Value | `arn:aws:s3:::acme-cache-data-123456789012-us-east-1-an` |

### CacheDataDynamoDbTableArnExport

Condition: CreateCacheData

Cache-Data DynamoDB table ARN. Export name is identical to the standalone template.

| Attribute | Value |
|-----------|-------|
| Export Name | `{Prefix}-CacheDataDynamoDbTableArn` |
| Example Value | `arn:aws:dynamodb:us-east-1:123456789012:table/acme-cache-data-CacheData` |

### CacheDataManagedLambdaExecutionRolePolicyArn

Condition: CreateCacheDataManagedPolicy

Managed policy ARN for Lambda execution roles to access the Cache-Data resources. Export name is identical to the standalone template.

| Attribute | Value |
|-----------|-------|
| Export Name | `{Prefix}-CacheDataManagedLambdaExecutionRolePolicy` |
| Example Value | `arn:aws:iam::123456789012:policy/acme-cache-data-ManagedLambdaExecutionRolePolicy` |

## Examples

### Management Roles Only (No Cache-Data)

```
Prefix: acme
PrefixUpper: ACME
S3ArtifactsBucket: acme-cf-artifacts-123456789012-us-east-1-an
S3ModuleLocation: 63klabs-atlas-us-east-1
S3ModuleNamespace: atlantis
```

Cache-Data resources are not created (`EnableCacheData` defaults to `false`).

### With Shared Cache-Data Enabled

```
Prefix: acme
PrefixUpper: ACME
S3BucketNameOrgPrefix: acmecorp
S3ArtifactsBucket: acme-cf-artifacts-123456789012-us-east-1-an
EnableCacheData: true
CacheDataPurgeAgeOfCachedBucketObjInDays: 30
CreateManagedCacheDataLambdaExecutionRolePolicy: TRUE
RolePath: /app_role/
S3ModuleLocation: 63klabs-atlas-us-east-1
S3ModuleNamespace: atlantis
```

Creates the DynamoDB table `acme-cache-data-CacheData`, the S3 bucket `acmecorp-acme-cache-data-123456789012-us-east-1-an`, its bucket policy, and the managed Lambda execution policy `acme-cache-data-ManagedLambdaExecutionRolePolicy`.

### Cache-Data With a Custom Lambda Policy

```
Prefix: acme
PrefixUpper: ACME
S3ArtifactsBucket: acme-cf-artifacts-123456789012-us-east-1-an
EnableCacheData: true
CreateManagedCacheDataLambdaExecutionRolePolicy: FALSE
S3ModuleLocation: 63klabs-atlas-us-east-1
S3ModuleNamespace: atlantis
```

Creates the Cache-Data DynamoDB table, S3 bucket, and bucket policy without the managed policy, allowing you to define custom IAM permissions for Lambda access.

## Related Templates

- **[template-storage-cache-data](../storage/template-storage-cache-data-README.md)**: The standalone, prefix + project scoped Cache-Data template. It is the canonical reference for the Cache-Data resource definitions and remains unchanged; the modules consumed here are its condition-aware counterparts.
- **[account-wide-infrastructure](./account-wide-infrastructure-README.md)**: Account-wide (cross-prefix) managed policies, connections, and shared artifacts bucket.
- **Pipeline templates** (`template-pipeline.yml`, `template-pipeline-github.yml`, `template-pipeline-build-only.yml`): consume the pipeline management service role.
- **Storage and Network templates**: consume the storage and network management service roles.

## Troubleshooting

### Module Loading Fails

- Verify the `S3ModuleLocation` bucket exists and is accessible from the deploying account
- Check that `S3ModuleNamespace` matches the path structure in the bucket
- The Cache-Data modules must be published under `s3://<S3ModuleLocation>/<S3ModuleNamespace>/templates/v2/modules/cache-data/` — the storage management role's `S3ModuleBucketGetObject` statement grants namespace-wide read that covers this path

### Cache-Data Export-Name Collision

- The Cache-Data exports (`${Prefix}-CacheData*`) are shared with the standalone `template-storage-cache-data.yml`
- If another stack for the same Prefix already owns these exports, keep `EnableCacheData` set to `false` here (or disable it in the other stack) — only one stack per Prefix may own the Cache-Data resources

### Cache-Data Resources Not Created

- Confirm `EnableCacheData` is set to `"true"`
- The managed Lambda execution policy additionally requires `CreateManagedCacheDataLambdaExecutionRolePolicy` to be `TRUE`

## Additional Resources

- [@63klabs/cache-data npm package](https://www.npmjs.com/package/@63klabs/cache-data)
- [AWS CloudFormation Interface Metadata](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-cloudformation-interface.html)
- [Using AWS::Include Transform](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/create-reusable-transform-function-snippets-and-add-to-your-template-with-aws-include-transform.html)
- [DynamoDB Time To Live](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)
- [S3 Lifecycle Configuration](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
