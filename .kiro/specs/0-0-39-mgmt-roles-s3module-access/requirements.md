# Requirements Document

## Introduction

The management roles created by `prefix-based-infrastructure.yml` enable CloudFormation to deploy infrastructure templates that use AWS::Include to load reusable module snippets from an S3 bucket. Currently, these roles have comprehensive permissions for managing prefix-scoped resources but lack explicit read permissions for the S3 bucket containing the CloudFormation modules (specified by the `S3ModuleLocation` parameter). This gap prevents CloudFormation from resolving AWS::Include references during stack deployments.

This specification addresses the missing S3 read permissions by adding scoped, read-only access to the module bucket for all four management role modules.

## Glossary

- **Management_Role**: IAM role assumed by CloudFormation service to create and manage infrastructure resources
- **S3ModuleLocation**: S3 bucket name parameter containing CloudFormation module snippets (e.g., `63klabs-atlas-us-east-1`)
- **S3ModuleNamespace**: S3 key prefix parameter scoping module access to a specific namespace path (e.g., `atlantis-sam-templates/v2`)
- **AWS_Include**: CloudFormation transform that imports template snippets from S3 at deployment time
- **Least_Privilege**: Security principle limiting permissions to the minimum required for function
- **Module_Snippet**: Reusable CloudFormation template fragment stored in S3 and referenced via AWS::Include
- **Prefix_Based_Infrastructure**: Parent account-level template that creates management roles using AWS::Include to load module definitions
- **Pipeline_Management_Role**: Management role for deploying CodePipeline and CodeBuild resources
- **Storage_Management_Role**: Management role for deploying S3, DynamoDB, and Lambda resources
- **Network_CloudFront_Management_Role**: Management role for deploying CloudFront, OAC, and API Gateway resources (no Route53)
- **Network_Full_Management_Role**: Management role for deploying CloudFront, Route53, and API Gateway resources
- **Network_CloudFront_Management_Policy**: Managed IAM policy containing CloudFront and API Gateway permissions, attached to network management roles

## Requirements

### Requirement 1: S3 Read Access for Pipeline Management Role

**User Story:** As a CloudFormation deployment, I want the Pipeline Management Role to read module snippets from the S3ModuleLocation bucket, so that I can resolve AWS::Include references during pipeline stack deployments.

#### Acceptance Criteria

1. WHEN the Pipeline_Management_Role assumes role, THE Role SHALL have s3:GetObject permission on `arn:aws:s3:::${S3ModuleLocation}/${S3ModuleNamespace}/*`
2. WHEN the Pipeline_Management_Role assumes role, THE Role SHALL have s3:GetObjectVersion permission on `arn:aws:s3:::${S3ModuleLocation}/${S3ModuleNamespace}/*`
3. WHEN the Pipeline_Management_Role assumes role, THE Role SHALL have s3:ListBucket permission on `arn:aws:s3:::${S3ModuleLocation}` with condition limiting prefix to `${S3ModuleNamespace}/`
4. THE Pipeline_Management_Role SHALL NOT have write permissions (s3:PutObject, s3:DeleteObject) on the S3ModuleLocation bucket
5. THE IAM policy statement SHALL be named `S3ModuleBucketReadOnly` for clear identification

### Requirement 2: S3 Read Access for Storage Management Role

**User Story:** As a CloudFormation deployment, I want the Storage Management Role to read module snippets from the S3ModuleLocation bucket, so that I can resolve AWS::Include references during storage stack deployments.

#### Acceptance Criteria

1. WHEN the Storage_Management_Role assumes role, THE Role SHALL have s3:GetObject permission on `arn:aws:s3:::${S3ModuleLocation}/${S3ModuleNamespace}/*`
2. WHEN the Storage_Management_Role assumes role, THE Role SHALL have s3:GetObjectVersion permission on `arn:aws:s3:::${S3ModuleLocation}/${S3ModuleNamespace}/*`
3. WHEN the Storage_Management_Role assumes role, THE Role SHALL have s3:ListBucket permission on `arn:aws:s3:::${S3ModuleLocation}` with condition limiting prefix to `${S3ModuleNamespace}/`
4. THE Storage_Management_Role SHALL NOT have write permissions (s3:PutObject, s3:DeleteObject) on the S3ModuleLocation bucket
5. THE IAM policy statement SHALL be named `S3ModuleBucketReadOnly` for clear identification

### Requirement 3: S3 Read Access for Network CloudFront Management Policy

**User Story:** As a CloudFormation deployment, I want the Network CloudFront Management Policy to include module bucket read permissions, so that network management roles can resolve AWS::Include references during CloudFront stack deployments.

#### Acceptance Criteria

1. WHEN the Network_CloudFront_Management_Policy is attached to a role, THE Policy SHALL grant s3:GetObject permission on `arn:aws:s3:::${S3ModuleLocation}/${S3ModuleNamespace}/*`
2. WHEN the Network_CloudFront_Management_Policy is attached to a role, THE Policy SHALL grant s3:GetObjectVersion permission on `arn:aws:s3:::${S3ModuleLocation}/${S3ModuleNamespace}/*`
3. WHEN the Network_CloudFront_Management_Policy is attached to a role, THE Policy SHALL grant s3:ListBucket permission on `arn:aws:s3:::${S3ModuleLocation}` with condition limiting prefix to `${S3ModuleNamespace}/`
4. THE Network_CloudFront_Management_Policy SHALL NOT grant write permissions (s3:PutObject, s3:DeleteObject) on the S3ModuleLocation bucket
5. THE IAM policy statement SHALL be named `S3ModuleBucketReadOnly` for clear identification
6. THE Network_CloudFront_Management_Role SHALL inherit these permissions via managed policy attachment
7. THE Network_Full_Management_Role SHALL inherit these permissions via managed policy attachment

### Requirement 4: Module Header Documentation Updates

**User Story:** As a template developer, I want module header comments to accurately list required parameters, so that I understand all dependencies when including a module.

#### Acceptance Criteria

1. WHEN a module header lists required parameters, THE Header SHALL include S3ModuleLocation in the parent template requirements list
2. WHEN a module header lists required parameters, THE Header SHALL include S3ModuleNamespace in the parent template requirements list
3. THE pipeline-mgmt-role.yml header SHALL list S3ModuleLocation and S3ModuleNamespace as required parent parameters
4. THE storage-mgmt-role.yml header SHALL list S3ModuleLocation and S3ModuleNamespace as required parent parameters
5. THE network-cloudfront-mgmt-policy.yml header SHALL list S3ModuleLocation and S3ModuleNamespace as required parent parameters

### Requirement 5: Backward Compatibility

**User Story:** As a template consumer, I want this change to be non-breaking, so that existing deployments continue to function without modification.

#### Acceptance Criteria

1. THE change SHALL NOT modify or remove existing IAM permissions from any management role
2. THE change SHALL NOT modify or remove existing parameters from any module
3. THE change SHALL NOT modify the logical resource names of any CloudFormation resources
4. THE change SHALL be a PATCH version increment (no breaking changes)
5. WHEN existing stacks are updated with new module versions, THE Stacks SHALL deploy successfully without parameter changes

### Requirement 6: Least Privilege Security

**User Story:** As a security engineer, I want IAM permissions to follow the principle of least privilege, so that roles have only the minimum access required for their function.

#### Acceptance Criteria

1. THE IAM policy statements SHALL grant only read permissions (s3:GetObject, s3:GetObjectVersion, s3:ListBucket)
2. THE IAM policy statements SHALL scope object access to the namespace path using `${S3ModuleLocation}/${S3ModuleNamespace}/*`
3. THE IAM policy statements SHALL scope ListBucket using a condition with StringLike operator on `s3:prefix` matching `${S3ModuleNamespace}/*`
4. THE IAM policy statements SHALL NOT use wildcard permissions (s3:*)
5. THE IAM policy statements SHALL NOT grant access to other S3 buckets beyond S3ModuleLocation
6. THE IAM policy statements SHALL NOT grant access to objects outside the namespace path

### Requirement 7: Consistent Implementation

**User Story:** As a template maintainer, I want all management roles to have consistent IAM statement structure, so that the codebase is maintainable and predictable.

#### Acceptance Criteria

1. THE S3ModuleBucketReadOnly policy statement SHALL have identical structure across all three modules (pipeline-mgmt-role.yml, storage-mgmt-role.yml, network-cloudfront-mgmt-policy.yml)
2. THE policy statement SHALL use the same Sid naming convention: `S3ModuleBucketReadOnly`
3. THE policy statement SHALL use the same action list order: [s3:GetObject, s3:GetObjectVersion, s3:ListBucket]
4. THE policy statement SHALL use the same resource ARN format with Fn::Sub intrinsic function
5. THE policy statement SHALL use the same StringLike condition structure for ListBucket scoping
