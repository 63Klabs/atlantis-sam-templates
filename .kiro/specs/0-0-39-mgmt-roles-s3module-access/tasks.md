# Implementation Plan: S3 Module Access for Management Roles

## Overview

This plan implements read-only S3 access permissions for three management role modules to enable CloudFormation's AWS::Include transform to access module snippets from the S3ModuleLocation bucket. The implementation adds a consistent IAM policy statement named `S3ModuleBucketReadOnly` to each module, following the principle of least privilege.

## Tasks

- [x] 1. Update pipeline-mgmt-role.yml module
  - [x] 1.1 Add S3ModuleBucketReadOnly statement to pipeline management role
    - Navigate to `templates/v2/modules/management-roles/pipeline-mgmt-role.yml`
    - Locate the inline policy document at `Properties.Policies[0].PolicyDocument.Statement`
    - Insert the S3ModuleBucketReadOnly statement after the existing `InspectServiceRole` statement
    - Use 6-space indentation for statement level, 8-space for properties
    - Use long-form intrinsic functions (Fn::Sub, not !Sub)
    - Statement structure:
      ```yaml
      - Sid: S3ModuleBucketReadOnly
        Effect: Allow
        Action:
          - s3:GetObject
          - s3:GetObjectVersion
          - s3:ListBucket
        Resource:
          - Fn::Sub: "arn:aws:s3:::${S3ModuleLocation}"
          - Fn::Sub: "arn:aws:s3:::${S3ModuleLocation}/${S3ModuleNamespace}/*"
        Condition:
          StringLike:
            s3:prefix:
              - Fn::Sub: "${S3ModuleNamespace}/*"
      ```
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [x] 1.2 Update header comment for pipeline-mgmt-role.yml
    - Add S3ModuleLocation and S3ModuleNamespace to the required parent parameters list
    - Update format: `# Parent template must define parameters: [existing], S3ModuleLocation, S3ModuleNamespace`
    - _Requirements: 4.1, 4.2, 4.3_

- [x] 2. Update storage-mgmt-role.yml module
  - [x] 2.1 Add S3ModuleBucketReadOnly statement to storage management role
    - Navigate to `templates/v2/modules/management-roles/storage-mgmt-role.yml`
    - Locate the inline policy document at `Properties.Policies[0].PolicyDocument.Statement`
    - Insert the S3ModuleBucketReadOnly statement after the existing `InspectServiceRole` statement
    - Use 6-space indentation for statement level, 8-space for properties
    - Use long-form intrinsic functions (Fn::Sub, not !Sub)
    - Use identical statement structure as pipeline-mgmt-role.yml
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [x] 2.2 Update header comment for storage-mgmt-role.yml
    - Add S3ModuleLocation and S3ModuleNamespace to the required parent parameters list
    - Update format: `# Parent template must define parameters: [existing], S3ModuleLocation, S3ModuleNamespace`
    - _Requirements: 4.1, 4.2, 4.4_

- [x] 3. Update network-cloudfront-mgmt-policy.yml module
  - [x] 3.1 Add S3ModuleBucketReadOnly statement to network CloudFront managed policy
    - Navigate to `templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml`
    - Locate the policy document at `Properties.PolicyDocument.Statement`
    - Insert the S3ModuleBucketReadOnly statement after the existing `AcmCertificateRead` statement
    - Use 6-space indentation for statement level, 8-space for properties
    - Use long-form intrinsic functions (Fn::Sub, not !Sub)
    - Use identical statement structure as pipeline-mgmt-role.yml and storage-mgmt-role.yml
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [x] 3.2 Update header comment for network-cloudfront-mgmt-policy.yml
    - Add S3ModuleLocation and S3ModuleNamespace to the required parent parameters list
    - Update format: `# Parent template must define parameters: [existing], S3ModuleLocation, S3ModuleNamespace`
    - _Requirements: 4.1, 4.2, 4.5_

- [x] 4. Validate all module templates
  - Run cfn-lint on all three modified modules:
    ```bash
    cfn-lint templates/v2/modules/management-roles/pipeline-mgmt-role.yml
    cfn-lint templates/v2/modules/management-roles/storage-mgmt-role.yml
    cfn-lint templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml
    ```
  - Verify zero errors and no warnings about policy structure
  - Confirm all Fn::Sub expressions have required parameters
  - Check that IAM policy statement structure is valid
  - _Requirements: All (validation ensures requirements are met)_

- [x] 5. Verify consistency across modules
  - Compare the S3ModuleBucketReadOnly statement in all three files
  - Confirm Sid is exactly "S3ModuleBucketReadOnly" in each file
  - Verify Action list order is identical: [s3:GetObject, s3:GetObjectVersion, s3:ListBucket]
  - Check Resource ARN format uses Fn::Sub with ${S3ModuleLocation} and ${S3ModuleNamespace}
  - Confirm Condition structure is identical (StringLike on s3:prefix)
  - Ensure indentation is consistent (6 spaces for statement, 8 for properties)
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 6. Update CHANGELOG.md
  - Add entry under v0.0.39 (unreleased) section
  - Document the three module changes: pipeline-mgmt-role.yml, storage-mgmt-role.yml, network-cloudfront-mgmt-policy.yml
  - Describe the change: "Added S3ModuleBucketReadOnly IAM policy statement to enable CloudFormation AWS::Include transform to access module snippets from S3"
  - Note that this is a non-breaking change (PATCH increment)
  - Reference the feature spec: 0-0-39-mgmt-roles-s3module-access
  - _Requirements: All (documentation of changes)_

- [x] 7. Checkpoint - Final verification
  - Ensure all cfn-lint validations pass
  - Confirm all three modules have identical S3ModuleBucketReadOnly statement structure
  - Verify header comments are updated in all three modules
  - Check that CHANGELOG.md documents the changes
  - Review git diff to ensure only intended changes are present
  - Ensure no trailing whitespace or formatting issues

## Notes

- All three modules must have **identical** S3ModuleBucketReadOnly statement structure for consistency
- Use **long-form** CloudFormation intrinsic functions (Fn::Sub) as AWS::Include does not support shorthand (!Sub)
- Maintain **6-space indentation** for statement level, **8-space** for properties within statements
- The parent template `prefix-based-infrastructure.yml` already defines S3ModuleLocation and S3ModuleNamespace parameters
- No version increment is needed (template remains at v0.0.0 in development mode)
- This is a **non-breaking change** - existing stacks can update without parameter modifications
- The S3ModuleBucketReadOnly statement grants **read-only** permissions scoped to the module bucket and namespace
- Permissions follow the **principle of least privilege** - no write operations (PutObject, DeleteObject) are granted
- Each task references specific requirements for traceability

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1", "3.1"] },
    { "id": 1, "tasks": ["1.2", "2.2", "3.2"] },
    { "id": 2, "tasks": ["4"] },
    { "id": 3, "tasks": ["5"] },
    { "id": 4, "tasks": ["6"] },
    { "id": 5, "tasks": ["7"] }
  ]
}
```
