# IAM TagRole/UntagRole Permissions Boundary Bugfix Design

## Overview

The `iam:TagRole` and `iam:UntagRole` actions are incorrectly bundled in the `ManageWorkerRolesByResourcePrefix` IAM policy statement alongside privilege-escalation-sensitive actions (`CreateRole`, `AttachRolePolicy`, `PutRolePolicy`, etc.) that require an `iam:PermissionsBoundary` condition. Because `TagRole` and `UntagRole` API calls do not include `iam:PermissionsBoundary` in their request context, IAM evaluates the condition as false and denies these non-sensitive actions. The fix separates `iam:TagRole` and `iam:UntagRole` into their own statement without the permissions boundary condition, while preserving the condition on actions that can escalate privileges.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug — `iam:TagRole` or `iam:UntagRole` is called on a Worker role when `HasPermissionsBoundaryArn` is true, causing denial because the `iam:PermissionsBoundary` context key is absent from the request
- **Property (P)**: The desired behavior — `iam:TagRole` and `iam:UntagRole` are allowed on prefix-scoped Worker roles regardless of permissions boundary configuration
- **Preservation**: The `iam:PermissionsBoundary` condition must remain enforced for privilege-escalation-sensitive actions (`CreateRole`, `AttachRolePolicy`, `PutRolePolicy`, `DetachRolePolicy`, `DeleteRolePolicy`, `UpdateRoleDescription`)
- **ManageWorkerRolesByResourcePrefix**: The IAM policy statement in both `pipeline-mgmt-role.yml` and `storage-mgmt-role.yml` that grants IAM management actions on `arn:aws:iam::${AccountId}:role${RolePath}${Prefix}-Worker-*`
- **HasPermissionsBoundaryArn**: A CloudFormation condition that is true when the `PermissionsBoundaryArn` parameter is provided (non-empty)
- **Worker Role**: IAM roles matching the path and prefix pattern `${RolePath}${Prefix}-Worker-*`, created by CloudFormation stacks managed by these service roles

## Bug Details

### Bug Condition

The bug manifests when CloudFormation attempts to tag or untag a Worker role during stack create/update operations while a `PermissionsBoundaryArn` is configured. The `ManageWorkerRolesByResourcePrefix` statement includes `iam:TagRole` and `iam:UntagRole` alongside actions that support the `iam:PermissionsBoundary` condition key, but the Tag/Untag APIs do not include this context key in their request, causing IAM to deny the action.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type IAMPolicyEvaluation
  OUTPUT: boolean
  
  RETURN input.action IN {"iam:TagRole", "iam:UntagRole"}
         AND input.hasPermissionsBoundaryArn = true
         AND input.resource MATCHES "arn:aws:iam::*:role${RolePath}${Prefix}-Worker-*"
END FUNCTION
```

### Examples

- **Pipeline mgmt role, TagRole with boundary**: CloudFormation calls `iam:TagRole` on `arn:aws:iam::123456789012:role/app/acme-Worker-ApiFunction` with `PermissionsBoundaryArn` configured → Expected: Allow, Actual: Deny ("is not authorized to perform: iam:TagRole")
- **Storage mgmt role, TagRole with boundary**: CloudFormation calls `iam:TagRole` on `arn:aws:iam::123456789012:role/app/acme-Worker-ProcessorFunction` with `PermissionsBoundaryArn` configured → Expected: Allow, Actual: Deny
- **Pipeline mgmt role, UntagRole with boundary**: CloudFormation calls `iam:UntagRole` on `arn:aws:iam::123456789012:role/app/acme-Worker-ApiFunction` with `PermissionsBoundaryArn` configured → Expected: Allow, Actual: Deny
- **CreateRole with boundary (not a bug)**: CloudFormation calls `iam:CreateRole` with `PermissionsBoundaryArn` configured → Correctly allowed because `CreateRole` includes `iam:PermissionsBoundary` in its request context

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- `iam:CreateRole` on Worker roles must continue to enforce the `iam:PermissionsBoundary` condition when `HasPermissionsBoundaryArn` is true
- `iam:AttachRolePolicy` on Worker roles must continue to enforce the `iam:PermissionsBoundary` condition when `HasPermissionsBoundaryArn` is true
- `iam:PutRolePolicy` on Worker roles must continue to enforce the `iam:PermissionsBoundary` condition when `HasPermissionsBoundaryArn` is true
- `iam:DetachRolePolicy` on Worker roles must continue to enforce the `iam:PermissionsBoundary` condition when `HasPermissionsBoundaryArn` is true
- `iam:DeleteRolePolicy` on Worker roles must continue to enforce the `iam:PermissionsBoundary` condition when `HasPermissionsBoundaryArn` is true
- `iam:UpdateRoleDescription` on Worker roles must continue to enforce the `iam:PermissionsBoundary` condition when `HasPermissionsBoundaryArn` is true
- When `HasPermissionsBoundaryArn` is false, all actions (including TagRole/UntagRole) must be allowed without condition (no-op condition)
- `iam:TagRole`/`iam:UntagRole` on resources NOT matching the Worker role prefix pattern must continue to be denied (no statement grants it)

**Scope:**
All IAM actions other than `iam:TagRole` and `iam:UntagRole` in the `ManageWorkerRolesByResourcePrefix` statement are completely unaffected. The resource scope (`arn:aws:iam::${AccountId}:role${RolePath}${Prefix}-Worker-*`) remains identical for all statements.

## Hypothesized Root Cause

Based on the bug description, the root cause is clear:

1. **Incorrect condition scoping**: `iam:TagRole` and `iam:UntagRole` are grouped with actions that support the `iam:PermissionsBoundary` condition key. These two actions do not include `iam:PermissionsBoundary` in their request context, so IAM cannot evaluate the `StringEquals` condition and defaults to deny.

2. **AWS IAM condition key behavior**: The `iam:PermissionsBoundary` condition key is only present in the request context for actions that create or modify role trust/permission boundaries (`CreateRole`, `AttachRolePolicy`, `PutRolePolicy`, `DetachRolePolicy`, `DeleteRolePolicy`). It is NOT present for `TagRole`, `UntagRole`, or `UpdateRoleDescription`.

3. **Note on UpdateRoleDescription**: While `iam:UpdateRoleDescription` also does not include `iam:PermissionsBoundary` in its request context, it is intentionally kept in the conditional statement as a defense-in-depth measure. The requirements (3.6) explicitly state it must remain conditioned. If this causes issues in practice, it can be addressed separately.

## Correctness Properties

Property 1: Bug Condition - TagRole/UntagRole Allowed Without PermissionsBoundary Condition

_For any_ IAM policy evaluation where the action is `iam:TagRole` or `iam:UntagRole` AND the resource matches `arn:aws:iam::*:role${RolePath}${Prefix}-Worker-*`, the fixed policy SHALL allow the action regardless of whether `HasPermissionsBoundaryArn` is true or false (i.e., no `iam:PermissionsBoundary` condition is applied to these actions).

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

Property 2: Preservation - Privilege-Escalation Actions Retain PermissionsBoundary Condition

_For any_ IAM policy evaluation where the action is NOT `iam:TagRole` or `iam:UntagRole` AND `HasPermissionsBoundaryArn` is true, the fixed policy SHALL produce the same evaluation result as the original policy — specifically, the `iam:PermissionsBoundary` condition SHALL continue to be enforced for `iam:CreateRole`, `iam:AttachRolePolicy`, `iam:PutRolePolicy`, `iam:DetachRolePolicy`, `iam:DeleteRolePolicy`, and `iam:UpdateRoleDescription`.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8**

## Fix Implementation

### Changes Required

The fix is identical in both affected templates. In each case, `iam:TagRole` and `iam:UntagRole` are extracted from `ManageWorkerRolesByResourcePrefix` into a new unconditional statement.

**File**: `templates/v2/modules/management-roles/pipeline-mgmt-role.yml`

**Changes**:
1. **Remove Tag/Untag from existing statement**: Remove `iam:TagRole` and `iam:UntagRole` from the `ManageWorkerRolesByResourcePrefix` statement's Action list
2. **Add new statement**: Create a new `TagWorkerRolesByResourcePrefix` statement with only `iam:TagRole` and `iam:UntagRole`, scoped to the same resource ARN, with NO condition block

**File**: `templates/v2/modules/management-roles/storage-mgmt-role.yml`

**Changes**:
1. **Remove Tag/Untag from existing statement**: Remove `iam:TagRole` and `iam:UntagRole` from the `ManageWorkerRolesByResourcePrefix` statement's Action list
2. **Add new statement**: Create a new `TagWorkerRolesByResourcePrefix` statement with only `iam:TagRole` and `iam:UntagRole`, scoped to the same resource ARN, with NO condition block

**Resulting structure (both templates):**

```yaml
      - Sid: ManageWorkerRolesByResourcePrefix
        Effect: Allow
        Action:
        - iam:AttachRolePolicy
        - iam:CreateRole
        - iam:DeleteRolePolicy
        - iam:DetachRolePolicy
        - iam:PutRolePolicy
        - iam:UpdateRoleDescription
        Resource:
          Fn::Sub: "arn:aws:iam::${AWS::AccountId}:role${RolePath}${Prefix}-Worker-*"
        Condition: 
          Fn::If:
            - HasPermissionsBoundaryArn
            - StringEquals:
                "iam:PermissionsBoundary":
                  Ref: PermissionsBoundaryArn
            - Ref: "AWS::NoValue"

      - Sid: TagWorkerRolesByResourcePrefix
        Effect: Allow
        Action:
        - iam:TagRole
        - iam:UntagRole
        Resource:
          Fn::Sub: "arn:aws:iam::${AWS::AccountId}:role${RolePath}${Prefix}-Worker-*"
```

## Testing Strategy

### Validation Approach

The testing strategy validates the fix using CloudFormation template linting and structural analysis. Since this is an IAM policy configuration change in CloudFormation templates, testing focuses on verifying the template structure is correct and the policy statements have the expected configuration.

### Exploratory Bug Condition Checking

**Goal**: Confirm that the current template structure causes the bug by analyzing the policy statement grouping.

**Test Plan**: Parse the YAML templates and verify that `iam:TagRole` and `iam:UntagRole` are currently in the same statement as the `iam:PermissionsBoundary` condition. This confirms the root cause.

**Test Cases**:
1. **Pipeline template analysis**: Verify `iam:TagRole` is in `ManageWorkerRolesByResourcePrefix` with the boundary condition (confirms bug on unfixed code)
2. **Storage template analysis**: Verify `iam:TagRole` is in `ManageWorkerRolesByResourcePrefix` with the boundary condition (confirms bug on unfixed code)

**Expected Counterexamples**:
- `iam:TagRole` and `iam:UntagRole` found in a statement that has `iam:PermissionsBoundary` condition
- Root cause confirmed: these actions cannot satisfy the condition since they don't include the context key

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed templates produce the correct policy structure.

**Pseudocode:**
```
FOR ALL template IN {pipeline-mgmt-role.yml, storage-mgmt-role.yml} DO
  statements := parseStatements(template)
  tagStatement := findStatement(statements, "TagWorkerRolesByResourcePrefix")
  ASSERT tagStatement.actions = {"iam:TagRole", "iam:UntagRole"}
  ASSERT tagStatement.condition = NONE
  ASSERT tagStatement.resource MATCHES "arn:aws:iam::*:role${RolePath}${Prefix}-Worker-*"
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed templates retain the permissions boundary condition on privilege-escalation-sensitive actions.

**Pseudocode:**
```
FOR ALL template IN {pipeline-mgmt-role.yml, storage-mgmt-role.yml} DO
  statements := parseStatements(template)
  manageStatement := findStatement(statements, "ManageWorkerRolesByResourcePrefix")
  ASSERT "iam:TagRole" NOT IN manageStatement.actions
  ASSERT "iam:UntagRole" NOT IN manageStatement.actions
  ASSERT "iam:CreateRole" IN manageStatement.actions
  ASSERT "iam:AttachRolePolicy" IN manageStatement.actions
  ASSERT "iam:PutRolePolicy" IN manageStatement.actions
  ASSERT "iam:DetachRolePolicy" IN manageStatement.actions
  ASSERT "iam:DeleteRolePolicy" IN manageStatement.actions
  ASSERT "iam:UpdateRoleDescription" IN manageStatement.actions
  ASSERT manageStatement.condition contains "iam:PermissionsBoundary"
END FOR
```

### Unit Tests

- Verify `TagWorkerRolesByResourcePrefix` statement exists in fixed pipeline template with correct actions and no condition
- Verify `TagWorkerRolesByResourcePrefix` statement exists in fixed storage template with correct actions and no condition
- Verify `ManageWorkerRolesByResourcePrefix` statement in fixed pipeline template retains boundary condition and does NOT include TagRole/UntagRole
- Verify `ManageWorkerRolesByResourcePrefix` statement in fixed storage template retains boundary condition and does NOT include TagRole/UntagRole
- Verify resource ARN pattern is identical between both statements in each template
- Verify cfn-lint passes on both fixed templates

### Property-Based Tests

- Given the workspace testing guidelines and the controlled number of templates, property-based tests are not necessary for this fix. Unit tests with concrete assertions on template structure provide sufficient coverage.

### Integration Tests

- Deploy a CloudFormation stack with an `AWS::IAM::Role` resource containing `Tags` using the fixed pipeline management service role with `PermissionsBoundaryArn` configured — verify deployment succeeds
- Deploy a CloudFormation stack with an `AWS::IAM::Role` resource containing `Tags` using the fixed storage management service role with `PermissionsBoundaryArn` configured — verify deployment succeeds
- Verify that a Worker role created through either management role still has the permissions boundary attached (preservation of privilege-escalation protection)
