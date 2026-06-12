# Requirements Document

## Introduction

This spec addresses a bug where `cloudformation:CreateChangeSet` fails when CloudFormation attempts to process SAM transforms (e.g. `AWS::Serverless-2016-10-31`) because the storage and pipeline management role policies do not allow `CreateChangeSet` on the AWS-managed transform ARNs.

- **GitHub Issue**: [#6](https://github.com/63Klabs/atlantis-sam-templates/issues/6)
- **Type**: bug
- **Assigned**: chadkluck
- **Created from issue**: 2026-06-12

## Glossary

- **SAM Transform**: AWS Serverless Application Model macro (`AWS::Serverless-2016-10-31`) that CloudFormation processes during changeset creation to expand serverless resource shorthand into full CloudFormation resources.
- **Transform ARN**: The Amazon Resource Name identifying an AWS-managed CloudFormation transform (e.g. `arn:aws:cloudformation:*:aws:transform/Serverless-2016-10-31`).
- **Permissions Boundary**: An IAM policy that sets the maximum permissions a role can have, enforced via the `iam:PermissionsBoundary` condition key.
- **Management Role**: A CloudFormation service role used to create and manage resources within a specific prefix scope.

## Requirements

### 1. Fix

1.1 WHEN CloudFormation processes a SAM transform during changeset creation under the pipeline management role THEN `cloudformation:CreateChangeSet` SHALL be allowed on `arn:aws:cloudformation:*:aws:transform/Serverless-2016-10-31`, `arn:aws:cloudformation:*:aws:transform/LanguageExtensions`, and `arn:aws:cloudformation:*:aws:transform/Include`

1.2 WHEN CloudFormation processes a SAM transform during changeset creation under the storage management role THEN `cloudformation:CreateChangeSet` SHALL be allowed on `arn:aws:cloudformation:*:aws:transform/Serverless-2016-10-31`, `arn:aws:cloudformation:*:aws:transform/LanguageExtensions`, and `arn:aws:cloudformation:*:aws:transform/Include`

### 2. Consistency

2.1 The new `AllowTransformOperations` statement in both templates SHALL match the existing pattern in `network-cloudfront-mgmt-policy.yml` (same Sid, action, and resource ARNs)

### 3. Validation

3.1 Both modified templates SHALL pass cfn-lint validation with no errors

3.2 Unit tests SHALL verify the `AllowTransformOperations` statement exists with correct actions and resources in both templates

## Description

The `ManageCloudFormationStacksByResourcePrefix` statement in both templates scopes `cloudformation:CreateChangeSet` to only the prefix-scoped stack resource. When a template uses SAM transforms (`AWS::Serverless::Function`, etc.) or `AWS::LanguageExtensions`, CloudFormation also needs `CreateChangeSet` permission on the transform ARNs (`arn:aws:cloudformation:*:aws:transform/*`). Without it, changeset creation fails.

The `network-cloudfront-mgmt-policy.yml` already includes the correct `AllowTransformOperations` statement that should be replicated in both affected templates.

### Affected Templates

- `templates/v2/modules/management-roles/pipeline-mgmt-role.yml`
- `templates/v2/modules/management-roles/storage-mgmt-role.yml`

### Error

```
User: arn:aws:sts::123456789012:assumed-role/ACME-CloudFormation-Service-Role-Storage-Management/AWSCloudFormation
is not authorized to perform: cloudformation:CreateChangeSet on resource:
arn:aws:cloudformation:us-east-1:aws:transform/Serverless-2016-10-31
because no identity-based policy allows the cloudformation:CreateChangeSet action
```
