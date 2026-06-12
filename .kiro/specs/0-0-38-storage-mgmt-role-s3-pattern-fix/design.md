# Design: Fix S3 resource pattern and add IAM policy permissions in storage-mgmt-role.yml

## Overview

Fix the `ManageBucketsByResourcePrefix` S3 ARN pattern in `storage-mgmt-role.yml` to match actual bucket names (which include ProjectId), and add a `ManageManagedPoliciesByResourcePrefix` statement for storage templates that create `AWS::IAM::ManagedPolicy` resources.

## Approach

Two changes are made to `storage-mgmt-role.yml`:

1. **S3 pattern simplification** — Replace the four over-specific ARN entries (deprecated + preferred × bucket + object) with two simple prefix-wildcard entries using `Fn::If` to handle the org-prefix condition.
2. **IAM managed policy CRUD** — Add a new statement granting create/delete/tag permissions for IAM managed policies scoped to the prefix and role path.

### Fix 1: Simplify S3 Resource Pattern

The current pattern uses `${Prefix}-${AccountId}-${Region}` which does not account for ProjectId in bucket names. The fix replaces all four resource entries with two entries using `${Prefix}-*` (or `${S3BucketNameOrgPrefix}-${Prefix}-*` when org prefix is enabled).

**Before (4 entries):**
```yaml
Resource:
  - Fn::Sub:
    - "arn:aws:s3:::${BucketPrefix}-*"
    - BucketPrefix:
        Fn::If: # Deprecated
          - UseS3BucketNameOrgPrefix
          - Fn::Sub: "${S3BucketNameOrgPrefix}-${Prefix}"
          - Fn::Sub: "${Prefix}-${AWS::Region}-${AWS::AccountId}"
  - Fn::Sub:
    - "arn:aws:s3:::${BucketPrefix}-*"
    - BucketPrefix:
        Fn::If: # Preferred
          - UseS3BucketNameOrgPrefix
          - Fn::Sub: "${S3BucketNameOrgPrefix}-${Prefix}"
          - Fn::Sub: "${Prefix}-${AWS::AccountId}-${AWS::Region}"
  - Fn::Sub:
    - "arn:aws:s3:::${BucketPrefix}-*/*"
    - BucketPrefix:
        Fn::If: # Deprecated
          - UseS3BucketNameOrgPrefix
          - Fn::Sub: "${S3BucketNameOrgPrefix}-${Prefix}"
          - Fn::Sub: "${Prefix}-${AWS::Region}-${AWS::AccountId}"
  - Fn::Sub:
    - "arn:aws:s3:::${BucketPrefix}-*/*"
    - BucketPrefix:
        Fn::If: # Preferred
          - UseS3BucketNameOrgPrefix
          - Fn::Sub: "${S3BucketNameOrgPrefix}-${Prefix}"
          - Fn::Sub: "${Prefix}-${AWS::AccountId}-${AWS::Region}"
```

**After (2 entries):**
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

This produces:
- Org prefix enabled: `arn:aws:s3:::acorp-acme-*` and `arn:aws:s3:::acorp-acme-*/*`
- Org prefix disabled: `arn:aws:s3:::acme-*` and `arn:aws:s3:::acme-*/*`

Both patterns match any bucket name starting with the prefix, regardless of whether ProjectId, AccountId, or Region segments follow.

### Fix 2: Add IAM Managed Policy CRUD

A new statement grants create/delete/version/tag permissions for IAM managed policies scoped by the role path and prefix.

```yaml
- Sid: ManageManagedPoliciesByResourcePrefix
  Effect: Allow
  Action:
    - iam:CreatePolicy
    - iam:DeletePolicy
    - iam:CreatePolicyVersion
    - iam:DeletePolicyVersion
    - iam:TagPolicy
    - iam:UntagPolicy
  Resource:
    Fn::Sub: "arn:aws:iam::${AWS::AccountId}:policy${RolePath}${Prefix}-*"
```

**Placement:** After the `IAMReadOnly` statement and before `ManageWorkerRolesByResourcePrefix`, keeping IAM permissions grouped together.

## Architecture

This is a minimal IAM policy modification to one existing CloudFormation module template. No new resources, services, or architectural changes are introduced.

```
┌─────────────────────────────────────────────────────────────┐
│  CloudFormation Service (assumes storage mgmt role)         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Modified Statement:                                        │
│    ManageBucketsByResourcePrefix      ← FIX (pattern)       │
│                                                             │
│  New Statement:                                             │
│    ManageManagedPoliciesByResourcePrefix  ← NEW             │
│                                                             │
│  Existing Statements (unchanged):                           │
│    ManageEventRulesByResourcePrefix                         │
│    ManageCloudFormationStacksByResourcePrefix               │
│    AllowTransformOperations                                 │
│    CloudWatchAlarmsLimitedCRUDThisDeploymentOnly            │
│    LogGroupsLimitedCRUDThisDeploymentOnly                   │
│    LogGroupsListAll                                         │
│    LambdaCRUDThisDeploymentOnly                             │
│    DynamoDbCRUDThisDeploymentOnly                           │
│    PassAndDeleteWorkerRolesByResourcePrefix                 │
│    IAMReadOnly                                              │
│    ManageWorkerRolesByResourcePrefix                        │
│    TagWorkerRolesByResourcePrefix                           │
│    InspectServiceRole                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### Affected Components

| Component | File | Role |
|-----------|------|------|
| Storage Management Role | `templates/v2/modules/management-roles/storage-mgmt-role.yml` | IAM service role for CloudFormation when deploying storage stacks |

### Interfaces

No new interfaces are introduced. The changes fix permissions that CloudFormation already attempts to use:

1. CloudFormation calls `s3:CreateBucket` with bucket names containing ProjectId → `ManageBucketsByResourcePrefix` (fixed pattern) permits this
2. CloudFormation calls `iam:CreatePolicy` for `AWS::IAM::ManagedPolicy` resources → `ManageManagedPoliciesByResourcePrefix` permits this

## Data Models

No data models are affected. This change modifies IAM policy documents only.

## Affected Files

| File | Change |
|------|--------|
| `templates/v2/modules/management-roles/storage-mgmt-role.yml` | Fix `ManageBucketsByResourcePrefix` resource pattern; add `ManageManagedPoliciesByResourcePrefix` statement |

## Design Decisions

1. **S3 pattern uses `${Prefix}-*` instead of `${Prefix}-${AccountId}-${Region}-*`**: The original pattern was too specific and did not account for ProjectId in bucket names. Using `${Prefix}-*` matches all bucket names under the prefix regardless of internal structure. This is acceptable because the role is already scoped to a specific prefix, and the storage management role legitimately needs full S3 access to buckets within that prefix.

2. **Deprecated and preferred patterns consolidated into one**: Rather than maintaining two patterns (deprecated region-first and preferred accountid-first), the simplified `${Prefix}-*` pattern covers both conventions and any future naming variations.

3. **`s3:*` action retained (Requirement 2.1 is SHOULD, not SHALL)**: The storage management role needs comprehensive S3 access (create, delete, configure lifecycle, encryption, versioning, policies, etc.). Enumerating all individual actions would be fragile and hard to maintain as storage templates evolve. The resource scoping to `${Prefix}-*` provides the primary security boundary.

4. **IAM managed policy scoped by RolePath and Prefix**: The `ManageManagedPoliciesByResourcePrefix` statement uses the `${RolePath}` and `${Prefix}` parameters to ensure only policies under the correct path and prefix can be managed, following least privilege.

5. **Statement ordering**: `ManageManagedPoliciesByResourcePrefix` is placed after `IAMReadOnly` and before `ManageWorkerRolesByResourcePrefix` to keep all IAM-related statements grouped together logically.

## Correctness Properties

Property 1: S3 bucket-level pattern matches all prefix-scoped buckets

_For any_ S3 bucket name starting with `${Prefix}-` (non-org-prefix) or `${S3BucketNameOrgPrefix}-${Prefix}-` (org-prefix), the `ManageBucketsByResourcePrefix` bucket-level resource ARN SHALL match that bucket.

**Validates: Requirements 1.1, 1.2**

Property 2: S3 object-level pattern matches all objects in prefix-scoped buckets

_For any_ S3 object in a bucket starting with `${Prefix}-` (non-org-prefix) or `${S3BucketNameOrgPrefix}-${Prefix}-` (org-prefix), the `ManageBucketsByResourcePrefix` object-level resource ARN SHALL match that object.

**Validates: Requirements 1.1, 1.2**

Property 3: IAM managed policy CRUD scoped correctly

_For any_ IAM managed policy under path `${RolePath}` with name starting with `${Prefix}-`, the `ManageManagedPoliciesByResourcePrefix` resource ARN SHALL match that policy.

**Validates: Requirements 3.1**

Property 4: Existing statements unchanged

_For any_ existing statement in `storage-mgmt-role.yml` other than `ManageBucketsByResourcePrefix`, the statement SHALL remain unmodified.

**Validates: Requirements 1.1, 1.2, 3.1**

Property 5: Template validity

The modified template SHALL pass cfn-lint validation with no errors.

**Validates: Requirements 4.1**

## Error Handling

This change does not introduce runtime error handling logic. The fix is purely declarative (IAM policy). Error scenarios:

| Scenario | Behavior |
|----------|----------|
| S3 pattern still uses AccountId/Region | Unit test verifies the simplified pattern |
| IAM managed policy statement missing | Unit test verifies statement exists with correct Sid and actions |
| IAM managed policy scoped too broadly | Unit test verifies resource contains `${RolePath}` and `${Prefix}-*` |
| Template YAML syntax error | cfn-lint validation catches malformed YAML |

## Security Considerations

- **S3 pattern broadening**: The pattern changes from `${Prefix}-${AccountId}-${Region}-*` to `${Prefix}-*`, which is broader. However:
  - The role retains `s3:*` actions regardless — the security boundary is the prefix scope
  - The prefix is organization-controlled and unique per team
  - No cross-prefix access is possible since `${Prefix}` is always the leading segment
  - When org prefix is enabled, the pattern is `${S3BucketNameOrgPrefix}-${Prefix}-*` providing two levels of scoping

- **IAM managed policy CRUD**: Limited to `CreatePolicy`, `DeletePolicy`, `CreatePolicyVersion`, `DeletePolicyVersion`, `TagPolicy`, `UntagPolicy` only. Cannot attach/detach policies from roles (that's handled by `ManageWorkerRolesByResourcePrefix`). Scoped to `${RolePath}${Prefix}-*` ensuring only policies under the designated path and prefix can be managed.

- **No escalation risk**: The managed policy statement cannot be used to create arbitrary policies with elevated permissions because:
  - The policy path is constrained to `${RolePath}${Prefix}-*`
  - Attaching policies to roles requires separate `iam:AttachRolePolicy` permission (scoped to Worker roles only)
  - The role itself has a permissions boundary when `HasPermissionsBoundaryArn` is true

## Testing Strategy

- **cfn-lint validation**: Run cfn-lint on the modified template to confirm valid YAML and CloudFormation structure.
- **Unit tests**: Verify:
  - `ManageBucketsByResourcePrefix` has exactly 2 resource entries (bucket-level and object-level)
  - Bucket-level entry uses `Fn::Sub` with pattern `arn:aws:s3:::${BucketPrefix}-*`
  - Object-level entry uses `Fn::Sub` with pattern `arn:aws:s3:::${BucketPrefix}-*/*`
  - Both entries use `Fn::If` with `UseS3BucketNameOrgPrefix`
  - Non-org branch resolves to `${Prefix}` (not `${Prefix}-${AccountId}-${Region}` or `${Prefix}-${Region}-${AccountId}`)
  - Org branch resolves to `${S3BucketNameOrgPrefix}-${Prefix}`
  - `ManageManagedPoliciesByResourcePrefix` statement exists with correct Sid and actions
  - `ManageManagedPoliciesByResourcePrefix` resource contains `${RolePath}` and `${Prefix}-*`
  - Existing statements remain unchanged

## Requirement Traceability

| Requirement | Design Element |
|-------------|----------------|
| 1.1 | Org-prefix branch: `${S3BucketNameOrgPrefix}-${Prefix}-*` pattern |
| 1.2 | Non-org-prefix branch: `${Prefix}-*` pattern |
| 1.3 | `Fn::If` with `UseS3BucketNameOrgPrefix` conditional structure |
| 1.4 | Deprecated/preferred patterns removed, replaced with simplified wildcard |
| 2.1 | Acknowledged as SHOULD; `s3:*` retained with justification |
| 3.1 | `ManageManagedPoliciesByResourcePrefix` statement with specified actions and resource |
| 4.1 | cfn-lint validation task |
| 4.2 | Unit tests for S3 pattern and IAM statement |
