# Implementation Plan

## Overview

Fix the `ManageBucketsByResourcePrefix` S3 ARN pattern in `storage-mgmt-role.yml` to use a simplified prefix-wildcard that matches actual bucket names (including ProjectId), and add a `ManageManagedPoliciesByResourcePrefix` statement for IAM managed policy CRUD operations.

## Tasks

- [x] 1. Fix ManageBucketsByResourcePrefix S3 resource pattern
  - [x] 1.1 Replace the four resource entries in `ManageBucketsByResourcePrefix` in `templates/v2/modules/management-roles/storage-mgmt-role.yml` with two entries: one bucket-level (`arn:aws:s3:::${BucketPrefix}-*`) and one object-level (`arn:aws:s3:::${BucketPrefix}-*/*`), both using `Fn::If` with `UseS3BucketNameOrgPrefix` where the true branch is `Fn::Sub: "${S3BucketNameOrgPrefix}-${Prefix}"` and the false branch is `Fn::Sub: "${Prefix}"`

- [x] 2. Add ManageManagedPoliciesByResourcePrefix statement
  - [x] 2.1 Add a `ManageManagedPoliciesByResourcePrefix` statement after `IAMReadOnly` and before `ManageWorkerRolesByResourcePrefix` in `templates/v2/modules/management-roles/storage-mgmt-role.yml` with actions `iam:CreatePolicy`, `iam:DeletePolicy`, `iam:CreatePolicyVersion`, `iam:DeletePolicyVersion`, `iam:TagPolicy`, `iam:UntagPolicy` and resource `Fn::Sub: "arn:aws:iam::${AWS::AccountId}:policy${RolePath}${Prefix}-*"`

- [x] 3. Validate template with cfn-lint
  - [x] 3.1 Run cfn-lint on `templates/v2/modules/management-roles/storage-mgmt-role.yml` and verify no errors (module-format errors E1001/E1002 are expected and acceptable)

- [x] 4. Unit tests for fix verification
  - [x] 4.1 Write unit test: `ManageBucketsByResourcePrefix` has exactly 2 resource entries (bucket-level and object-level)
  - [x] 4.2 Write unit test: both S3 resource entries use `Fn::If` with `UseS3BucketNameOrgPrefix` and the non-org branch resolves to `${Prefix}` (not `${Prefix}-${AWS::AccountId}-${AWS::Region}` or `${Prefix}-${AWS::Region}-${AWS::AccountId}`)
  - [x] 4.3 Write unit test: the org-prefix branch resolves to `${S3BucketNameOrgPrefix}-${Prefix}` in both entries
  - [x] 4.4 Write unit test: `ManageManagedPoliciesByResourcePrefix` statement exists with correct Sid, all six actions, and resource containing `${RolePath}` and `${Prefix}-*`
  - [x] 4.5 Write unit test: existing statements (`ManageEventRulesByResourcePrefix`, `ManageCloudFormationStacksByResourcePrefix`, `AllowTransformOperations`, `LambdaCRUDThisDeploymentOnly`, `DynamoDbCRUDThisDeploymentOnly`) remain unchanged

- [x] 5. Update CHANGELOG.md
  - [x] 5.1 Add entry under `v0.0.38 (unreleased)` in the `Fixed` category documenting the S3 pattern fix and IAM managed policy addition, referencing spec and issue #7

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["3.1"] },
    { "id": 2, "tasks": ["4.1", "4.2", "4.3", "4.4", "4.5", "5.1"] }
  ]
}
```

## Notes

- Tasks 1 and 2 are independent and can be done in parallel (they modify different sections of the same file)
- Task 3 (linting) depends on both fixes being complete
- Task 4 (unit tests) depends on linting to confirm valid YAML structure
- Task 5 (changelog) can be done after the template fixes are validated
- All intrinsic functions must use long-form syntax (Fn::Sub, Ref, etc.) per the template header comments — no YAML shorthand tags
- The `s3:*` action is intentionally retained per the design decision (Requirement 2.1 is SHOULD, not SHALL)
- The new `ManageManagedPoliciesByResourcePrefix` statement does NOT need a `Condition` block — managed policy CRUD does not conflict with permissions boundary enforcement
