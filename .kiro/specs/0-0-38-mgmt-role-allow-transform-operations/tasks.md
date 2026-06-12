# Implementation Plan

## Overview

Add an `AllowTransformOperations` IAM policy statement to both `pipeline-mgmt-role.yml` and `storage-mgmt-role.yml` to permit `cloudformation:CreateChangeSet` on AWS-managed transform ARNs, matching the existing pattern in `network-cloudfront-mgmt-policy.yml`.

## Tasks

- [x] 1. Fix pipeline-mgmt-role.yml
  - [x] 1.1 Add `AllowTransformOperations` statement immediately after `ManageCloudFormationStacksByResourcePrefix` in `templates/v2/modules/management-roles/pipeline-mgmt-role.yml` with Sid `AllowTransformOperations`, action `cloudformation:CreateChangeSet`, and resources `arn:aws:cloudformation:*:aws:transform/Serverless-2016-10-31`, `arn:aws:cloudformation:*:aws:transform/LanguageExtensions`, `arn:aws:cloudformation:*:aws:transform/Include`

- [x] 2. Fix storage-mgmt-role.yml
  - [x] 2.1 Add `AllowTransformOperations` statement immediately after `ManageCloudFormationStacksByResourcePrefix` in `templates/v2/modules/management-roles/storage-mgmt-role.yml` with Sid `AllowTransformOperations`, action `cloudformation:CreateChangeSet`, and resources `arn:aws:cloudformation:*:aws:transform/Serverless-2016-10-31`, `arn:aws:cloudformation:*:aws:transform/LanguageExtensions`, `arn:aws:cloudformation:*:aws:transform/Include`

- [x] 3. Validate templates with cfn-lint
  - [x] 3.1 Run cfn-lint on `templates/v2/modules/management-roles/pipeline-mgmt-role.yml` and verify no errors
  - [x] 3.2 Run cfn-lint on `templates/v2/modules/management-roles/storage-mgmt-role.yml` and verify no errors

- [x] 4. Unit tests for fix verification
  - [x] 4.1 Write unit test: `AllowTransformOperations` statement exists in pipeline template with Sid, correct action (`cloudformation:CreateChangeSet`), and all three transform resource ARNs
  - [x] 4.2 Write unit test: `AllowTransformOperations` statement exists in storage template with Sid, correct action (`cloudformation:CreateChangeSet`), and all three transform resource ARNs
  - [x] 4.3 Write unit test: `AllowTransformOperations` statement in both templates has no `Condition` key
  - [x] 4.4 Write unit test: `ManageCloudFormationStacksByResourcePrefix` statement in both templates is unchanged (still has same actions and condition)

- [x] 5. Update CHANGELOG.md
  - [x] 5.1 Add entry under `v0.0.38 (unreleased)` in the `Fixed` category documenting the fix for both templates, referencing spec and issue #6

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["3.1", "3.2"] },
    { "id": 2, "tasks": ["4.1", "4.2", "4.3", "4.4", "5.1"] }
  ]
}
```

## Notes

- Tasks 1 and 2 are independent and can be done in parallel
- Task 3 (linting) depends on both template fixes being complete
- Task 4 (unit tests) depends on linting to confirm valid YAML structure
- Task 5 (changelog) can be done after the template fixes are applied
- The statement format must use long-form intrinsic functions (no YAML shorthand) per the template header comments, but since this statement uses only string literals, no intrinsic functions are needed
