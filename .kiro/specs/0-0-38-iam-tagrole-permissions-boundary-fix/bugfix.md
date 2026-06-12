# Bugfix Requirements Document

## Introduction

`iam:TagRole` and `iam:UntagRole` API calls are blocked when CloudFormation attempts to create or update a Worker role with tags while a `PermissionsBoundaryArn` is configured. This occurs because both actions are included in the `ManageWorkerRolesByResourcePrefix` IAM policy statement which carries an `iam:PermissionsBoundary` condition. The `iam:TagRole` and `iam:UntagRole` APIs do not include the `iam:PermissionsBoundary` context key in their request, causing the condition to evaluate to false and deny access. This affects both `pipeline-mgmt-role.yml` and `storage-mgmt-role.yml` templates and blocks any standard CloudFormation deployment of `AWS::IAM::Role` resources with tags under these management roles.

**GitHub Issue**: [#5](https://github.com/63Klabs/atlantis-sam-templates/issues/5)

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN `iam:TagRole` is called on a Worker role resource AND `HasPermissionsBoundaryArn` condition is true THEN the system denies the action because the `iam:PermissionsBoundary` condition key is absent from the `TagRole` request context

1.2 WHEN `iam:UntagRole` is called on a Worker role resource AND `HasPermissionsBoundaryArn` condition is true THEN the system denies the action because the `iam:PermissionsBoundary` condition key is absent from the `UntagRole` request context

1.3 WHEN CloudFormation creates or updates an `AWS::IAM::Role` with `Tags` property under the pipeline management role AND `PermissionsBoundaryArn` is configured THEN the deployment fails with "is not authorized to perform: iam:TagRole on resource"

1.4 WHEN CloudFormation creates or updates an `AWS::IAM::Role` with `Tags` property under the storage management role AND `PermissionsBoundaryArn` is configured THEN the deployment fails with "is not authorized to perform: iam:TagRole on resource"

### Expected Behavior (Correct)

2.1 WHEN `iam:TagRole` is called on a Worker role resource matching the prefix pattern THEN the system SHALL allow the action regardless of whether a permissions boundary is configured

2.2 WHEN `iam:UntagRole` is called on a Worker role resource matching the prefix pattern THEN the system SHALL allow the action regardless of whether a permissions boundary is configured

2.3 WHEN CloudFormation creates or updates an `AWS::IAM::Role` with `Tags` property under the pipeline management role AND `PermissionsBoundaryArn` is configured THEN the deployment SHALL succeed for tagging operations

2.4 WHEN CloudFormation creates or updates an `AWS::IAM::Role` with `Tags` property under the storage management role AND `PermissionsBoundaryArn` is configured THEN the deployment SHALL succeed for tagging operations

### Unchanged Behavior (Regression Prevention)

3.1 WHEN `iam:CreateRole` is called AND `HasPermissionsBoundaryArn` is true THEN the system SHALL CONTINUE TO enforce the `iam:PermissionsBoundary` condition requiring the specified boundary ARN

3.2 WHEN `iam:AttachRolePolicy` is called AND `HasPermissionsBoundaryArn` is true THEN the system SHALL CONTINUE TO enforce the `iam:PermissionsBoundary` condition requiring the specified boundary ARN

3.3 WHEN `iam:PutRolePolicy` is called AND `HasPermissionsBoundaryArn` is true THEN the system SHALL CONTINUE TO enforce the `iam:PermissionsBoundary` condition requiring the specified boundary ARN

3.4 WHEN `iam:DetachRolePolicy` is called AND `HasPermissionsBoundaryArn` is true THEN the system SHALL CONTINUE TO enforce the `iam:PermissionsBoundary` condition requiring the specified boundary ARN

3.5 WHEN `iam:DeleteRolePolicy` is called AND `HasPermissionsBoundaryArn` is true THEN the system SHALL CONTINUE TO enforce the `iam:PermissionsBoundary` condition requiring the specified boundary ARN

3.6 WHEN `iam:UpdateRoleDescription` is called AND `HasPermissionsBoundaryArn` is true THEN the system SHALL CONTINUE TO enforce the `iam:PermissionsBoundary` condition requiring the specified boundary ARN

3.7 WHEN `HasPermissionsBoundaryArn` is false THEN the system SHALL CONTINUE TO allow all `ManageWorkerRolesByResourcePrefix` actions (including `iam:TagRole` and `iam:UntagRole`) without any condition

3.8 WHEN `iam:TagRole` or `iam:UntagRole` is called on a resource NOT matching `arn:aws:iam::${AWS::AccountId}:role${RolePath}${Prefix}-Worker-*` THEN the system SHALL CONTINUE TO deny the action

---

## Bug Condition (Formal)

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type IAMPolicyEvaluation
  OUTPUT: boolean
  
  // Returns true when the action is TagRole or UntagRole AND 
  // the PermissionsBoundary condition is active
  RETURN (X.action IN {"iam:TagRole", "iam:UntagRole"})
         AND (X.hasPermissionsBoundaryArn = true)
END FUNCTION
```

```pascal
// Property: Fix Checking - TagRole/UntagRole allowed without PermissionsBoundary condition
FOR ALL X WHERE isBugCondition(X) DO
  result ← evaluatePolicy'(X)
  ASSERT result = "Allow"
         AND X.resource MATCHES "arn:aws:iam::*:role${RolePath}${Prefix}-Worker-*"
END FOR
```

```pascal
// Property: Preservation Checking - All other actions retain PermissionsBoundary enforcement
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT evaluatePolicy(X) = evaluatePolicy'(X)
END FOR
```
