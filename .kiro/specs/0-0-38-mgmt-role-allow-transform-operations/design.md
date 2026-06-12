# Design: AllowTransformOperations for pipeline-mgmt-role and storage-mgmt-role

## Overview

Add an `AllowTransformOperations` IAM policy statement to both `pipeline-mgmt-role.yml` and `storage-mgmt-role.yml` to permit `cloudformation:CreateChangeSet` on AWS-managed transform ARNs. This unblocks deployments that use SAM transforms, `AWS::LanguageExtensions`, or `AWS::Include`.

## Approach

The fix is a direct replication of the existing pattern already established in `network-cloudfront-mgmt-policy.yml`. A new statement is inserted immediately after the `ManageCloudFormationStacksByResourcePrefix` statement in each template.

### Statement to Add

```yaml
- Sid: AllowTransformOperations
  Effect: Allow
  Action:
    - cloudformation:CreateChangeSet
  Resource:
    - "arn:aws:cloudformation:*:aws:transform/Serverless-2016-10-31"
    - "arn:aws:cloudformation:*:aws:transform/LanguageExtensions"
    - "arn:aws:cloudformation:*:aws:transform/Include"
```

### Placement

In both templates, the new statement goes directly after `ManageCloudFormationStacksByResourcePrefix` — this groups all CloudFormation-related permissions together and mirrors the ordering in `network-cloudfront-mgmt-policy.yml`.

## Architecture

This is a minimal IAM policy addition to two existing CloudFormation module templates. No new resources, services, or architectural changes are introduced. The fix adds a single IAM policy statement to each management role, enabling CloudFormation to invoke AWS-managed transforms during changeset creation.

```
┌─────────────────────────────────────────────────────────┐
│  CloudFormation Service (assumes management role)       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ManageCloudFormationStacksByResourcePrefix             │
│    → cloudformation:CreateChangeSet on ${Prefix}-* stacks│
│                                                         │
│  AllowTransformOperations  ← NEW                        │
│    → cloudformation:CreateChangeSet on aws:transform/*  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### Affected Components

| Component | File | Role |
|-----------|------|------|
| Pipeline Management Role | `templates/v2/modules/management-roles/pipeline-mgmt-role.yml` | Service role for CloudFormation when deploying pipeline stacks |
| Storage Management Role | `templates/v2/modules/management-roles/storage-mgmt-role.yml` | Service role for CloudFormation when deploying storage stacks |

### Interfaces

No new interfaces are introduced. The change adds permissions that CloudFormation already attempts to use (and currently fails). The interaction is:

1. CloudFormation assumes the management role
2. CloudFormation calls `CreateChangeSet` on a transform ARN to process macros
3. The new `AllowTransformOperations` statement permits this call

### Existing Pattern Reference

`templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml` already contains the identical statement — this fix replicates it for consistency.

## Data Models

No data models are affected. This change modifies IAM policy documents only — no data is stored, transformed, or transmitted. The IAM policy statement structure follows the standard AWS format:

```yaml
- Sid: AllowTransformOperations      # Statement identifier
  Effect: Allow                       # Permission effect
  Action:                             # API actions granted
    - cloudformation:CreateChangeSet
  Resource:                           # Target resource ARNs
    - "arn:aws:cloudformation:*:aws:transform/Serverless-2016-10-31"
    - "arn:aws:cloudformation:*:aws:transform/LanguageExtensions"
    - "arn:aws:cloudformation:*:aws:transform/Include"
```

## Affected Files

| File | Change |
|------|--------|
| `templates/v2/modules/management-roles/pipeline-mgmt-role.yml` | Add `AllowTransformOperations` statement after `ManageCloudFormationStacksByResourcePrefix` |
| `templates/v2/modules/management-roles/storage-mgmt-role.yml` | Add `AllowTransformOperations` statement after `ManageCloudFormationStacksByResourcePrefix` |

## Design Decisions

1. **Exact match with network template**: The statement uses the same Sid, actions, and resource ARNs as `network-cloudfront-mgmt-policy.yml` to maintain consistency across the codebase.

2. **Wildcard region in transform ARNs**: Transform ARNs use `*` for the region component (`arn:aws:cloudformation:*:aws:transform/...`) because AWS transforms are not region-specific resources — they are globally available service-level constructs.

3. **No condition block**: Transform permissions do not require prefix-scoping or permissions boundary conditions. They are AWS-managed resources that any CloudFormation deployment using transforms needs access to.

4. **Placement after stack management statement**: Grouping transform permissions with stack management keeps related CloudFormation permissions together and matches the established pattern.

5. **Three transform ARNs covered**:
   - `Serverless-2016-10-31` — Required for SAM templates (`AWS::Serverless::*` resources)
   - `LanguageExtensions` — Required for `AWS::LanguageExtensions` transform (intrinsic functions like `Fn::ForEach`, `Fn::ToJsonString`)
   - `Include` — Required for `AWS::Include` transform (used by module includes in this repo)

## Correctness Properties

Property 1: Statement presence

_For any_ template in {`pipeline-mgmt-role.yml`, `storage-mgmt-role.yml`}, the fixed template SHALL contain an `AllowTransformOperations` IAM policy statement.
**Validates: Requirements 1.1, 1.2**

Property 2: Action correctness

_For any_ `AllowTransformOperations` statement in either template, the statement SHALL grant exactly `cloudformation:CreateChangeSet` — no additional actions.
**Validates: Requirements 1.1, 1.2**

Property 3: Resource completeness

_For any_ `AllowTransformOperations` statement in either template, all three AWS-managed transform ARNs SHALL be listed: `arn:aws:cloudformation:*:aws:transform/Serverless-2016-10-31`, `arn:aws:cloudformation:*:aws:transform/LanguageExtensions`, `arn:aws:cloudformation:*:aws:transform/Include`.
**Validates: Requirements 1.1, 1.2, 2.1**

Property 4: No condition block

_For any_ `AllowTransformOperations` statement in either template, the statement SHALL NOT have a `Condition` key — transforms are AWS-managed resources and do not require prefix-scoping or boundary enforcement.
**Validates: Requirements 1.1, 1.2, 2.1**

Property 5: Existing statements unchanged

_For any_ template in {`pipeline-mgmt-role.yml`, `storage-mgmt-role.yml`}, the `ManageCloudFormationStacksByResourcePrefix` statement SHALL remain unmodified — the new statement supplements it, not replaces it.
**Validates: Requirements 1.1, 1.2**

Property 6: Template validity

_For any_ template in {`pipeline-mgmt-role.yml`, `storage-mgmt-role.yml`}, the modified template SHALL pass cfn-lint validation with no errors.
**Validates: Requirements 3.1**

## Error Handling

This change does not introduce runtime error handling logic. The fix is purely declarative (IAM policy). Error scenarios:

| Scenario | Behavior |
|----------|----------|
| Transform ARN typo in template | cfn-lint will not catch this (ARNs are strings), but unit tests verify exact ARN values |
| Statement omitted from one template | Unit tests verify both templates contain the statement |
| Statement placed with incorrect Sid | Unit tests verify Sid is exactly `AllowTransformOperations` |
| Template YAML syntax error | cfn-lint validation catches malformed YAML |

If the statement is correctly applied and CloudFormation still fails, the error would indicate a different permission issue unrelated to this fix (e.g., SCP denial, service control policies at the organization level).

## Security Considerations

- The statement grants only `cloudformation:CreateChangeSet` — no broader permissions.
- Resources are scoped to AWS-managed transform ARNs only (account `aws`, not the customer account).
- This does not grant any ability to modify, delete, or create transforms — only to reference them during changeset creation.
- The principle of least privilege is maintained: only the minimum action needed on the minimum set of resources.

## Testing Strategy

- **cfn-lint validation**: Run cfn-lint on both modified templates to confirm valid YAML and CloudFormation structure.
- **Unit tests**: Verify the `AllowTransformOperations` statement exists in both templates with the correct Sid, action, and all three resource ARNs.

## Requirement Traceability

| Requirement | Design Element |
|-------------|----------------|
| 1.1 | `AllowTransformOperations` statement added to `pipeline-mgmt-role.yml` |
| 1.2 | `AllowTransformOperations` statement added to `storage-mgmt-role.yml` |
| 2.1 | Statement matches `network-cloudfront-mgmt-policy.yml` exactly |
| 3.1 | cfn-lint validation task |
| 3.2 | Unit tests for statement presence, actions, and resources |
