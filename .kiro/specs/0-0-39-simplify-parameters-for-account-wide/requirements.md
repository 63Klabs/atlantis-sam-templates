# Requirements Document

## Introduction

This feature simplifies the parameters required to deploy `prefix-based-infrastructure.yml` (and the two related standalone service-role templates) by allowing the shared S3 artifacts bucket name to be derived automatically from the account-wide infrastructure stack export, rather than requiring it to be passed explicitly.

Today, `prefix-based-infrastructure.yml` requires an `S3ArtifactsBucket` parameter, which is consumed by the `pipeline-mgmt-role.yml` and `storage-mgmt-role.yml` modules to scope the `ArtifactBucketGetObjectForManagedStacks` IAM statement. The `account-wide-infrastructure.yml` template already exports the shared artifacts bucket name as `${OrgPrefix}-S3-Artifacts-Bucket-Name` when it is deployed with `EnableS3ArtifactsBucket = "true"`.

After this change, when `S3ArtifactsBucket` is not supplied, the two management-role modules fall back to importing the account-wide export using a new (optional) `OrgPrefix` parameter. Supplying `S3ArtifactsBucket` remains supported as an explicit override for backward compatibility, but the parameter is marked **DEPRECATED**; using the exported value is the encouraged path.

All changes are additive and backward compatible (new optional parameters, an override condition, and an `Fn::If` fallback in the modules). No parameters are removed or renamed, no required parameters are added, and no exports change. Existing deployments that pass `S3ArtifactsBucket` continue to behave exactly as before.

## Glossary

- **Module**: A YAML snippet file stored in S3 that defines a single CloudFormation resource body (starts with `Type:` at the top level, no wrapping logical ID), referenced by a parent template via `Fn::Transform: AWS::Include`. Modules must use long-form intrinsic functions only (`Fn::Sub`, `Ref`, `Fn::If`, `Fn::ImportValue`) because `AWS::Include` does not support YAML shorthand tags.
- **Prefix_Based_Template**: The parent template at `templates/v2/account/prefix-based-infrastructure.yml`.
- **Account_Wide_Template**: The template at `templates/v2/account/account-wide-infrastructure.yml` that conditionally exports the shared artifacts bucket name.
- **Pipeline_Mgmt_Role_Module**: The module at `templates/v2/modules/management-roles/pipeline-mgmt-role.yml`.
- **Storage_Mgmt_Role_Module**: The module at `templates/v2/modules/management-roles/storage-mgmt-role.yml`.
- **Standalone_Pipeline_Template**: The template at `templates/v2/service-role/template-service-role-pipeline.yml` (deprecation-noticed) that consumes the Pipeline_Mgmt_Role_Module.
- **Standalone_Storage_Template**: The template at `templates/v2/service-role/template-service-role-storage.yml` (deprecation-noticed) that consumes the Storage_Mgmt_Role_Module.
- **Consuming_Templates**: Collectively, the Prefix_Based_Template, Standalone_Pipeline_Template, and Standalone_Storage_Template — every parent template that consumes the two modified modules.
- **OrgPrefix**: The organization-level prefix (UPPER CASE) that the Account_Wide_Template uses to build the export name `${OrgPrefix}-S3-Artifacts-Bucket-Name`. Distinct from `PrefixUpper`.
- **PrefixUpper**: The existing team/namespace prefix (UPPER CASE) already defined in the Consuming_Templates. Not reused for the export lookup.
- **S3ArtifactsBucket**: The existing (now optional, deprecated) parameter naming the shared artifacts bucket. When non-empty it overrides the export lookup.
- **Artifacts_Bucket_Export**: The account-wide CloudFormation export named `${OrgPrefix}-S3-Artifacts-Bucket-Name`.
- **HasS3ArtifactsBucketOverride**: The new condition, true when `S3ArtifactsBucket` is not empty.
- **ArtifactBucketGetObjectForManagedStacks**: The existing IAM statement (Sid) in both modules that grants `s3:GetObject`/`s3:GetObjectVersion` on `arn:aws:s3:::<bucket>/${Prefix}-*`.

## Requirements

### Requirement 1: Add optional `OrgPrefix` parameter to the Prefix_Based_Template

**User Story:** As a platform administrator, I want to supply an organization prefix so that the prefix-based stack can locate the account-wide artifacts bucket export without me having to look up and paste the bucket name.

#### Acceptance Criteria

1. THE Prefix_Based_Template SHALL add an `OrgPrefix` parameter of type String.
2. THE `OrgPrefix` parameter SHALL use `Default: ""` so it is optional and backward compatible.
3. THE `OrgPrefix` parameter SHALL use `AllowedPattern: "^[A-Z][A-Z0-9-]{0,18}[A-Z0-9]$|^$"` and `MaxLength: 20`, and SHALL NOT declare a `MinLength` (so that an empty value is permitted).
4. THE `OrgPrefix` parameter `Description` SHALL explain that it is the organization-level prefix used to resolve the account-wide artifacts bucket export `${OrgPrefix}-S3-Artifacts-Bucket-Name`, that it is distinct from `PrefixUpper`, and that it is only required when `S3ArtifactsBucket` is left empty.
5. THE `OrgPrefix` parameter SHALL be listed in the `AWS::CloudFormation::Interface` metadata under the "Application Resource Naming" group, positioned adjacent to `PrefixUpper`.
6. THE `OrgPrefix` parameter definition (pattern, length, description intent) SHALL be consistent with the `OrgPrefix` definition in the Account_Wide_Template, differing only by permitting an empty value.

### Requirement 2: Make `S3ArtifactsBucket` optional and deprecated in the Prefix_Based_Template

**User Story:** As a platform administrator, I want `S3ArtifactsBucket` to be optional so that I can rely on the account-wide export, while existing stacks that still pass it keep working.

#### Acceptance Criteria

1. THE Prefix_Based_Template SHALL change the `S3ArtifactsBucket` parameter to `Default: ""`.
2. THE `S3ArtifactsBucket` parameter SHALL use `AllowedPattern: "^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$|^$"` and `MaxLength: 63`, and SHALL NOT declare a `MinLength` (so that an empty value is permitted).
3. THE `S3ArtifactsBucket` parameter `Description` SHALL be prefixed with `"DEPRECATED: "` and SHALL explain that the value is now derived from the `${OrgPrefix}-S3-Artifacts-Bucket-Name` export, that supplying it is an override retained for backward compatibility, and that using the export (by leaving this empty and setting `OrgPrefix`) is encouraged.
4. THE `S3ArtifactsBucket` parameter SHALL remain in the existing "External Resources" metadata group.
5. THE change SHALL NOT rename or remove the `S3ArtifactsBucket` parameter (preserving backward compatibility).

### Requirement 3: Add the `HasS3ArtifactsBucketOverride` condition to the Consuming_Templates

**User Story:** As a template maintainer, I want a single condition that indicates whether an explicit artifacts bucket override was provided, so that the modules can choose between the override and the export.

#### Acceptance Criteria

1. Each Consuming_Template SHALL define a condition named `HasS3ArtifactsBucketOverride` equal to `!Not [!Equals [!Ref S3ArtifactsBucket, ""]]`.
2. WHEN `S3ArtifactsBucket` is a non-empty string, THE `HasS3ArtifactsBucketOverride` condition SHALL evaluate to true.
3. WHEN `S3ArtifactsBucket` is an empty string, THE `HasS3ArtifactsBucketOverride` condition SHALL evaluate to false.

### Requirement 4: Fall back to the account-wide export in the Pipeline_Mgmt_Role_Module

**User Story:** As a platform administrator, I want the pipeline management service role to be granted read access to the correct artifacts bucket whether I pass it explicitly or rely on the account-wide export.

#### Acceptance Criteria

1. THE Pipeline_Mgmt_Role_Module SHALL keep the `ArtifactBucketGetObjectForManagedStacks` statement with actions `s3:GetObject` and `s3:GetObjectVersion` unchanged.
2. THE `ArtifactBucketGetObjectForManagedStacks` statement `Resource` SHALL use `Fn::If` on `HasS3ArtifactsBucketOverride`.
3. WHEN `HasS3ArtifactsBucketOverride` is true, THE statement `Resource` SHALL be `arn:aws:s3:::${S3ArtifactsBucket}/${Prefix}-*` (the current behavior).
4. WHEN `HasS3ArtifactsBucketOverride` is false, THE statement `Resource` SHALL be `arn:aws:s3:::<imported-bucket>/${Prefix}-*` where `<imported-bucket>` is resolved via `Fn::ImportValue` of `Fn::Sub: "${OrgPrefix}-S3-Artifacts-Bucket-Name"`.
5. THE Pipeline_Mgmt_Role_Module SHALL use long-form intrinsic functions only (`Fn::If`, `Fn::Sub`, `Fn::ImportValue`, `Ref`).
6. THE Pipeline_Mgmt_Role_Module header contract comment SHALL be updated to add `OrgPrefix` to the required parent parameters and `HasS3ArtifactsBucketOverride` to the required parent conditions.
7. All other statements in the Pipeline_Mgmt_Role_Module SHALL remain unchanged.

### Requirement 5: Fall back to the account-wide export in the Storage_Mgmt_Role_Module

**User Story:** As a platform administrator, I want the storage management service role to be granted read access to the correct artifacts bucket whether I pass it explicitly or rely on the account-wide export.

#### Acceptance Criteria

1. THE Storage_Mgmt_Role_Module SHALL keep the `ArtifactBucketGetObjectForManagedStacks` statement with actions `s3:GetObject` and `s3:GetObjectVersion` unchanged.
2. THE `ArtifactBucketGetObjectForManagedStacks` statement `Resource` SHALL use `Fn::If` on `HasS3ArtifactsBucketOverride`.
3. WHEN `HasS3ArtifactsBucketOverride` is true, THE statement `Resource` SHALL be `arn:aws:s3:::${S3ArtifactsBucket}/${Prefix}-*` (the current behavior).
4. WHEN `HasS3ArtifactsBucketOverride` is false, THE statement `Resource` SHALL be `arn:aws:s3:::<imported-bucket>/${Prefix}-*` where `<imported-bucket>` is resolved via `Fn::ImportValue` of `Fn::Sub: "${OrgPrefix}-S3-Artifacts-Bucket-Name"`.
5. THE Storage_Mgmt_Role_Module SHALL use long-form intrinsic functions only (`Fn::If`, `Fn::Sub`, `Fn::ImportValue`, `Ref`).
6. THE Storage_Mgmt_Role_Module header contract comment SHALL be updated to add `OrgPrefix` to the required parent parameters and `HasS3ArtifactsBucketOverride` to the required parent conditions.
7. All other statements in the Storage_Mgmt_Role_Module SHALL remain unchanged.

### Requirement 6: Keep the standalone service-role templates consistent with the modified modules

**User Story:** As a maintainer, I want the standalone pipeline and storage service-role templates to keep deploying successfully after the shared modules change, since they consume the same modules.

#### Acceptance Criteria

1. THE Standalone_Pipeline_Template SHALL add the optional, deprecated `S3ArtifactsBucket` parameter as defined in Requirement 2.
2. THE Standalone_Pipeline_Template SHALL add the optional `OrgPrefix` parameter as defined in Requirement 1.
3. THE Standalone_Pipeline_Template SHALL add the `HasS3ArtifactsBucketOverride` condition as defined in Requirement 3.
4. THE Standalone_Pipeline_Template SHALL group the new parameters into its `AWS::CloudFormation::Interface` metadata: `OrgPrefix` under "Application Resource Naming" (adjacent to `PrefixUpper`) and `S3ArtifactsBucket` under "External Resources".
5. THE Standalone_Storage_Template SHALL add the optional, deprecated `S3ArtifactsBucket` parameter as defined in Requirement 2.
6. THE Standalone_Storage_Template SHALL add the optional `OrgPrefix` parameter as defined in Requirement 1.
7. THE Standalone_Storage_Template SHALL add the `HasS3ArtifactsBucketOverride` condition as defined in Requirement 3.
8. THE Standalone_Storage_Template SHALL group the new parameters into its `AWS::CloudFormation::Interface` metadata: `OrgPrefix` under "Application Resource Naming" (adjacent to `PrefixUpper`) and `S3ArtifactsBucket` under "External Resources".
9. IF either standalone template previously referenced `${S3ArtifactsBucket}` through its module without declaring the parameter, THEN adding the parameter per this requirement SHALL resolve that inconsistency.

### Requirement 7: Deployment behavior and cross-stack dependency

**User Story:** As a platform administrator, I want predictable, well-documented behavior when the artifacts bucket cannot be resolved, so that I understand deployment prerequisites and failure modes.

#### Acceptance Criteria

1. WHEN `S3ArtifactsBucket` is empty AND the `Artifacts_Bucket_Export` does not exist, THE stack deployment SHALL fail with CloudFormation's native "No export named `${OrgPrefix}-S3-Artifacts-Bucket-Name` found" error (no custom guard is added).
2. THE documentation SHALL state that, to use the export path, the Account_Wide_Template must first be deployed with `EnableS3ArtifactsBucket = "true"` and a matching `OrgPrefix`.
3. THE documentation SHALL note that `Fn::ImportValue` creates a hard cross-stack dependency that prevents deletion or modification of the `Artifacts_Bucket_Export` while any Consuming_Template stack references it.
4. WHEN `S3ArtifactsBucket` is supplied (non-empty), THE deployment SHALL NOT create any dependency on the `Artifacts_Bucket_Export`.

### Requirement 8: Versioning

**User Story:** As a maintainer, I want template versions bumped according to the version-control rules so that changes are traceable.

#### Acceptance Criteria

1. THE Prefix_Based_Template version SHALL be incremented from `v0.0.1` to `v0.0.2` with the current date, treating the change as non-breaking (PATCH).
2. THE Standalone_Pipeline_Template version SHALL be incremented by one PATCH (from `v0.0.18` to `v0.0.19`) with the current date.
3. THE Standalone_Storage_Template version SHALL be incremented by one PATCH (from `v0.0.3` to `v0.0.4`) with the current date.
4. THE modules (Pipeline_Mgmt_Role_Module, Storage_Mgmt_Role_Module) SHALL NOT carry individual version numbers (they are versioned with their parent templates).
5. Only the version and date lines in template header comments SHALL be modified; other header comment content SHALL remain unchanged.

### Requirement 9: Documentation and changelog

**User Story:** As a user of these templates, I want the documentation and changelog to reflect the new parameters and behavior so that I know how to deploy them.

#### Acceptance Criteria

1. THE end-user documentation for the Prefix_Based_Template (`docs/templates/v2/account/prefix-based-infrastructure-README.md`) SHALL be updated to document the new `OrgPrefix` parameter, the now-optional/deprecated `S3ArtifactsBucket` parameter, the export-based fallback behavior, and the cross-stack dependency and failure mode from Requirement 7.
2. THE end-user documentation for the Standalone_Pipeline_Template and Standalone_Storage_Template SHALL be updated to document the new `OrgPrefix` and deprecated `S3ArtifactsBucket` parameters, IF documentation files exist for those templates.
3. THE relevant category README files SHALL be updated only if parameter tables or template descriptions they contain are affected.
4. Any existing blockquotes in the documentation being updated SHALL be preserved.
5. THE `CHANGELOG.md` SHALL add entries under the `v0.0.39 (unreleased)` section referencing this spec, listing the three modified templates with their new version numbers and a brief description, without modifying existing changelog text.

### Requirement 10: Validation

**User Story:** As a maintainer, I want the modified templates and modules to pass linting so that I have confidence the changes are structurally valid.

#### Acceptance Criteria

1. THE modified Consuming_Templates SHALL pass `cfn-lint` using the repository's existing linter configuration.
2. THE existing `cfn-lint` ignore checks (E6101, W2001, W8001) SHALL remain sufficient; no new suppressions SHALL be added unless a specific, justified lint finding requires it.
3. THE two modified modules SHALL continue to contain only a single resource body (no logical ID, no `Resources:` wrapper) and long-form intrinsic functions only.
4. Any unit tests in the repository that assert on the modified modules or templates SHALL be updated to reflect the new `Fn::If` fallback structure and SHALL pass.
