# Requirements Document

## Introduction

This spec addresses a bug where the `storage-mgmt-role.yml` S3 resource pattern (`ManageBucketsByResourcePrefix`) does not match the bucket names produced by storage templates, causing `s3:CreateBucket` (and all other S3 actions) to be denied. Additionally, IAM managed policy CRUD permissions are missing for storage templates that create `AWS::IAM::ManagedPolicy` resources.

- **GitHub Issue**: [#7](https://github.com/63Klabs/atlantis-sam-templates/issues/7)
- **Type**: bug
- **Assigned**: chadkluck
- **Created from issue**: 2026-06-12

## Glossary

- **ManageBucketsByResourcePrefix**: The IAM policy statement in `storage-mgmt-role.yml` that grants S3 actions scoped to bucket ARN patterns derived from the deployment prefix.
- **UseS3BucketNameOrgPrefix**: A CloudFormation condition that, when true, prepends an organization prefix (`S3BucketNameOrgPrefix`) to bucket name patterns for disambiguation across organizations.
- **S3BucketNameOrgPrefix**: A parameter providing the organization-level prefix for S3 bucket names when `UseS3BucketNameOrgPrefix` is enabled.
- **Prefix**: The team/org identifier used as the first segment of all resource names in this naming convention.
- **ProjectId**: The short identifier for the application, appearing between Prefix and AccountId/Region in bucket names.
- **Management Role**: A CloudFormation service role used to create and manage resources within a specific prefix scope.

## Requirements

### 1. S3 Resource Pattern Fix

1.1 WHEN `UseS3BucketNameOrgPrefix` is true THEN the `ManageBucketsByResourcePrefix` S3 resource ARN pattern SHALL resolve to `arn:aws:s3:::${S3BucketNameOrgPrefix}-${Prefix}-*` (bucket-level) and `arn:aws:s3:::${S3BucketNameOrgPrefix}-${Prefix}-*/*` (object-level)

1.2 WHEN `UseS3BucketNameOrgPrefix` is false THEN the `ManageBucketsByResourcePrefix` S3 resource ARN pattern SHALL resolve to `arn:aws:s3:::${Prefix}-*` (bucket-level) and `arn:aws:s3:::${Prefix}-*/*` (object-level)

1.3 The pattern SHALL use `Fn::If` with `UseS3BucketNameOrgPrefix` to conditionally select the bucket prefix. Example:
```yaml
Resource:
  - Fn::Sub:
    - "arn:aws:s3:::${BucketPrefix}-*"
    - BucketPrefix:
        Fn::If:
          - UseS3BucketNameOrgPrefix
          - Fn::Sub: "${S3BucketNameOrgPrefix}-${Prefix}"
          - Fn::Sub: "${Prefix}"
  - Fn::Sub:
    - "arn:aws:s3:::${BucketPrefix}-*/*"
    - BucketPrefix:
        Fn::If:
          - UseS3BucketNameOrgPrefix
          - Fn::Sub: "${S3BucketNameOrgPrefix}-${Prefix}"
          - Fn::Sub: "${Prefix}"
```

1.4 The deprecated `${Prefix}-${Region}-${AccountId}-*` and preferred `${Prefix}-${AccountId}-${Region}-*` patterns SHALL be removed and replaced with the simplified prefix-wildcard pattern above

### 2. Least Privilege S3 Actions

2.1 The S3 actions in `ManageBucketsByResourcePrefix` SHOULD be scoped to specific bucket management actions rather than `s3:*` to follow least privilege principles

### 3. IAM Managed Policy Permissions

3.1 A `ManageManagedPoliciesByResourcePrefix` statement SHALL be added granting `iam:CreatePolicy`, `iam:DeletePolicy`, `iam:CreatePolicyVersion`, `iam:DeletePolicyVersion`, `iam:TagPolicy`, and `iam:UntagPolicy` scoped to `arn:aws:iam::${AWS::AccountId}:policy${RolePath}${Prefix}-*`

### 4. Validation

4.1 The modified template SHALL pass cfn-lint validation with no errors

4.2 Unit tests SHALL verify the corrected S3 pattern (including `UseS3BucketNameOrgPrefix` conditional) and new IAM policy statement

## Description

The `ManageBucketsByResourcePrefix` statement in `storage-mgmt-role.yml` constructs S3 ARN patterns as:
- `arn:aws:s3:::${Prefix}-${AccountId}-${Region}-*` (preferred)
- `arn:aws:s3:::${Prefix}-${Region}-${AccountId}-*` (deprecated)

These resolve to patterns like `acme-123456789012-us-east-1-*` which do not match actual bucket names that include ProjectId between Prefix and Account/Region (e.g. `acme-myproj-origin-123456789012-us-east-1-an`).

### Error

```
User: arn:aws:sts::123456789012:assumed-role/ACME-CloudFormation-Service-Role-Storage-Management/AWSCloudFormation
is not authorized to perform: s3:CreateBucket on resource:
arn:aws:s3:::acme-myproj-origin-123456789012-us-east-1-an
because no identity-based policy allows the s3:CreateBucket action
```

### Additional Missing Permissions

1. **IAM Managed Policy CRUD** — `template-storage-cache-data.yml` creates `AWS::IAM::ManagedPolicy` but the role only has `iam:Get*`/`iam:List*` for policies.
2. **Lambda Permission** — `template-storage-s3-oac-for-cloudfront.yml` creates `AWS::Lambda::Permission` (covered by existing `lambda:*` if function is under same prefix).

### Affected Templates

- `templates/v2/modules/management-roles/storage-mgmt-role.yml` (the role policy)
- All templates in `templates/v2/storage/` are affected by the S3 pattern mismatch
