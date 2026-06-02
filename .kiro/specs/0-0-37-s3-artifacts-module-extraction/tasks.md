# Implementation Plan: S3 Artifacts Module Extraction

## Overview

Extract the S3 artifacts bucket and bucket policy from the existing storage template into reusable account-wide modules, then integrate them into the `account-wide-infrastructure.yml` template with conditional creation support. Two new module files are created following the established module pattern, and the parent template is updated with new parameters, conditions, resources, outputs, and metadata.

## Tasks

- [x] 1. Create S3 Artifacts Bucket Module
  - [x] 1.1 Create `templates/v2/modules/account-wide/s3-artifacts-bucket.yml`
    - Add header comment documenting parent template prerequisites: parameters (`S3BucketNameOrgPrefix`, `S3LogBucketName`) and conditions (`UseS3BucketNameOrgPrefix`, `HasLoggingBucket`, `EnableS3ArtifactsBucket`)
    - Define `Type: AWS::S3::Bucket` at top level (no wrapping logical name)
    - Add `Condition: EnableS3ArtifactsBucket`
    - Add `DeletionPolicy: Retain`
    - Construct bucket name using `Fn::If` / `Fn::Sub` with `UseS3BucketNameOrgPrefix` condition: `[S3BucketNameOrgPrefix-]cf-artifacts-${AccountId}-${Region}-an`
    - Include `VersioningConfiguration` with Status Enabled
    - Include `PublicAccessBlockConfiguration` with all four blocks true
    - Include `BucketEncryption` with AES256
    - Include `LifecycleConfiguration`: expire 395 days, noncurrent 30 days, abort multipart 1 day
    - Include conditional `LoggingConfiguration` guarded by `HasLoggingBucket` condition
    - Use ONLY long-form intrinsic functions (`Ref:`, `Fn::Sub:`, `Fn::If:`, `Fn::GetAtt:`) — no YAML shorthand tags
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11, 1.12_

- [x] 2. Create S3 Artifacts Bucket Policy Module
  - [x] 2.1 Create `templates/v2/modules/account-wide/s3-artifacts-bucket-policy.yml`
    - Add header comment documenting parent template prerequisites: parameters (`RolePath`), conditions (`EnableS3ArtifactsBucket`), pseudo-parameters (`AWS::AccountId`), and bucket resource logical name (`S3ArtifactsBucketRegional`)
    - Define `Type: AWS::S3::BucketPolicy` at top level (no wrapping logical name)
    - Add `Condition: EnableS3ArtifactsBucket`
    - Reference bucket using `Ref: S3ArtifactsBucketRegional` and `Fn::GetAtt: [S3ArtifactsBucketRegional, Arn]`
    - Add `DenyNonSecureTransportAccess` statement: Deny all s3:* when SecureTransport=false on bucket ARN and objects
    - Add `WhitelistedGet` statement: Allow s3:GetObject, s3:GetObjectVersion, s3:GetBucketVersioning to unprefixed CodePipeline/CodeBuild/CloudFormation role wildcards
    - Add `WhitelistedPut` statement: Allow s3:PutObject to unprefixed CodePipeline/CodeBuild role wildcards
    - Construct IAM principal ARNs using `Fn::Sub` with `AWS::AccountId` and `RolePath`
    - Use ONLY long-form intrinsic functions — no YAML shorthand tags
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10_

- [x] 3. Checkpoint - Verify module syntax
  - Ensure both module files use only long-form intrinsic functions (no `!Ref`, `!Sub`, `!If`, `!GetAtt`)
  - Ensure both modules start with `Type:` at top level
  - Ensure both modules include `Condition: EnableS3ArtifactsBucket`
  - Run cfn-lint if available to validate syntax
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Integrate modules into account-wide-infrastructure.yml
  - [x] 4.1 Add new parameters to `templates/v2/account/account-wide-infrastructure.yml`
    - Add `EnableS3ArtifactsBucket` parameter: String, AllowedValues ["true", "false"], Default "false"
    - Add `S3BucketNameOrgPrefix` parameter: String, Default "", AllowedPattern `^[a-z0-9][a-z0-9-]{0,18}[a-z0-9]$|^$`
    - Add `S3LogBucketName` parameter: String, Default "", AllowedPattern `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$|^$`
    - _Requirements: 3.1, 3.3, 3.4_

  - [x] 4.2 Add new conditions to `templates/v2/account/account-wide-infrastructure.yml`
    - Add `EnableS3ArtifactsBucket` condition: `Equals [EnableS3ArtifactsBucket, "true"]`
    - Add `UseS3BucketNameOrgPrefix` condition: `Not [Equals [S3BucketNameOrgPrefix, ""]]`
    - Add `HasLoggingBucket` condition: `Not [Equals [S3LogBucketName, ""]]`
    - _Requirements: 3.2, 3.7_

  - [x] 4.3 Add new resources to `templates/v2/account/account-wide-infrastructure.yml`
    - Add `S3ArtifactsBucketRegional` resource via `Fn::Transform: AWS::Include` referencing `s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/account-wide/s3-artifacts-bucket.yml`
    - Add `S3ArtifactBucketPolicy` resource via `Fn::Transform: AWS::Include` referencing `s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/account-wide/s3-artifacts-bucket-policy.yml`
    - _Requirements: 3.5, 3.6_

  - [x] 4.4 Add new outputs to `templates/v2/account/account-wide-infrastructure.yml`
    - Add `S3ArtifactsBucketName` output with Condition `EnableS3ArtifactsBucket`, Export `${OrgPrefix}-S3-Artifacts-Bucket-Name`
    - Add `S3ArtifactsBucketConsole` output with Condition `EnableS3ArtifactsBucket`, console link format
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 4.5 Add metadata parameter group to `templates/v2/account/account-wide-infrastructure.yml`
    - Add "S3 Artifacts Bucket" parameter group containing `EnableS3ArtifactsBucket`, `S3BucketNameOrgPrefix`, `S3LogBucketName`
    - _Requirements: 3.8_

- [x] 5. Checkpoint - Validate parent template
  - Ensure account-wide-infrastructure.yml passes cfn-lint validation
  - Verify all new parameters are listed in metadata parameter groups
  - Verify conditional outputs reference the correct condition
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Update CHANGELOG and documentation
  - [x] 6.1 Update CHANGELOG.md
    - Add entry under `v0.0.37 - unreleased` section (create section if it doesn't exist)
    - Add under "Added" category: S3 Artifacts Bucket modules and account-wide-infrastructure integration
    - Reference spec: `[Spec: 0-0-37-s3-artifacts-module-extraction](.kiro/specs/0-0-37-s3-artifacts-module-extraction/)`
    - Include template references: Account: account-wide-infrastructure.yml v0.0.0, Modules: s3-artifacts-bucket.yml, s3-artifacts-bucket-policy.yml
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 3.5, 3.6_

  - [x] 6.2 Create documentation for account-wide-infrastructure template
    - Create `docs/templates/v2/account/` directory
    - Create `docs/templates/v2/account/README.md` with category overview
    - Create `docs/templates/v2/account/account-wide-infrastructure-README.md` with full template documentation
    - Document all parameters (including new S3 Artifacts Bucket parameters), resources, outputs
    - Follow documentation-end-user-cfn-templates steering document structure
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 4.1, 4.2, 4.3_

- [x] 7. Final checkpoint - Ensure all tests pass
  - Verify all module files exist at correct paths
  - Verify account-wide-infrastructure.yml has all new parameters, conditions, resources, outputs, and metadata
  - Verify CHANGELOG.md has new entry
  - Verify documentation files exist
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- This feature is Infrastructure as Code (CloudFormation templates) — property-based testing is not applicable
- The existing `template-storage-s3-artifacts.yml` is NOT modified by this feature
- `account-wide-infrastructure.yml` is at v0.0.0 (development mode) — no version increment needed per template-version-control steering
- Modules MUST use long-form intrinsic functions only (`Ref:`, `Fn::Sub:`, `Fn::If:`, `Fn::GetAtt:`) because `AWS::Include` does not support YAML shorthand tags
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["4.1", "4.2"] },
    { "id": 2, "tasks": ["4.3", "4.5"] },
    { "id": 3, "tasks": ["4.4"] },
    { "id": 4, "tasks": ["6.1", "6.2"] }
  ]
}
```
