# Implementation Plan

## Overview

Fix `iam:TagRole` and `iam:UntagRole` being blocked by the `iam:PermissionsBoundary` condition in both `pipeline-mgmt-role.yml` and `storage-mgmt-role.yml` by extracting those actions into a separate unconditional IAM policy statement.

## Tasks

- [x] 1. Fix pipeline-mgmt-role.yml
  - [x] 1.1 Remove `iam:TagRole` and `iam:UntagRole` from the `ManageWorkerRolesByResourcePrefix` statement Action list in `templates/v2/modules/management-roles/pipeline-mgmt-role.yml`
  - [x] 1.2 Add a new `TagWorkerRolesByResourcePrefix` statement immediately after `ManageWorkerRolesByResourcePrefix` with `iam:TagRole` and `iam:UntagRole` actions, same resource ARN, and no Condition block

- [x] 2. Fix storage-mgmt-role.yml
  - [x] 2.1 Remove `iam:TagRole` and `iam:UntagRole` from the `ManageWorkerRolesByResourcePrefix` statement Action list in `templates/v2/modules/management-roles/storage-mgmt-role.yml`
  - [x] 2.2 Add a new `TagWorkerRolesByResourcePrefix` statement immediately after `ManageWorkerRolesByResourcePrefix` with `iam:TagRole` and `iam:UntagRole` actions, same resource ARN, and no Condition block

- [x] 3. Validate templates with cfn-lint
  - [x] 3.1 Run cfn-lint on `templates/v2/modules/management-roles/pipeline-mgmt-role.yml` and verify no errors
  - [x] 3.2 Run cfn-lint on `templates/v2/modules/management-roles/storage-mgmt-role.yml` and verify no errors

- [x] 4. Unit tests for fix verification
  - [x] 4.1 Write unit test: `TagWorkerRolesByResourcePrefix` statement exists in pipeline template with correct actions (`iam:TagRole`, `iam:UntagRole`) and no Condition
  - [x] 4.2 Write unit test: `TagWorkerRolesByResourcePrefix` statement exists in storage template with correct actions (`iam:TagRole`, `iam:UntagRole`) and no Condition
  - [x] 4.3 Write unit test: `ManageWorkerRolesByResourcePrefix` in pipeline template does NOT contain `iam:TagRole` or `iam:UntagRole` and retains `iam:PermissionsBoundary` condition
  - [x] 4.4 Write unit test: `ManageWorkerRolesByResourcePrefix` in storage template does NOT contain `iam:TagRole` or `iam:UntagRole` and retains `iam:PermissionsBoundary` condition
  - [x] 4.5 Write unit test: Resource ARN pattern is identical between `ManageWorkerRolesByResourcePrefix` and `TagWorkerRolesByResourcePrefix` in both templates

- [x] 5. Update CHANGELOG.md
  - [x] 5.1 Add entry under `v0.0.38 (unreleased)` in the `Fixed` category documenting the fix for both templates, referencing spec and issue #5

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "2.1", "2.2"] },
    { "id": 1, "tasks": ["3.1", "3.2", "5.1"] },
    { "id": 2, "tasks": ["4.1", "4.2", "4.3", "4.4", "4.5"] }
  ]
}
```

## Notes

- Tasks 1 and 2 are independent and can be done in parallel
- Task 3 (linting) depends on both template fixes being complete
- Task 4 (unit tests) depends on linting to confirm valid YAML structure
- Task 5 (changelog) can be done after the template fixes are applied
