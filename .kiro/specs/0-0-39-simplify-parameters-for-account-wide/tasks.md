# Implementation Plan

## Overview

This plan makes the shared S3 artifacts bucket name optional for `prefix-based-infrastructure.yml` and the two standalone service-role templates. When `S3ArtifactsBucket` is not supplied, the two management-role modules (`pipeline-mgmt-role.yml`, `storage-mgmt-role.yml`) resolve the bucket name at deploy time from the account-wide export `${OrgPrefix}-S3-Artifacts-Bucket-Name` via `Fn::ImportValue`, selected by a new `HasS3ArtifactsBucketOverride` condition. Supplying `S3ArtifactsBucket` remains a supported but deprecated override.

The work is additive and backward compatible: no parameters are removed or renamed, no required parameters are added, and no exports change. Tasks proceed from version bumps, through template and module edits, into unit tests, `cfn-lint` validation, documentation, and a changelog entry.

## Tasks

- [x] 1. Version Management (increment before making changes; PATCH > 0 for all three)
  - [x] 1.1 Increment `prefix-based-infrastructure.yml` header version from `v0.0.1` to `v0.0.2` with date `2026-08-10`
    - Update only the `# Version:` line; leave all other header comments unchanged
    - _Requirements: 8.1, 8.5_
  - [x] 1.2 Increment `template-service-role-pipeline.yml` header version from `v0.0.18` to `v0.0.19` with date `2026-08-10`
    - _Requirements: 8.2, 8.5_
  - [x] 1.3 Increment `template-service-role-storage.yml` header version from `v0.0.3` to `v0.0.4` with date `2026-08-10`
    - _Requirements: 8.3, 8.5_

- [x] 2. Update `prefix-based-infrastructure.yml` (parent template)
  - [x] 2.1 Add the optional `OrgPrefix` parameter
    - Type String, `Default: ""`, `AllowedPattern: "^[A-Z][A-Z0-9-]{0,18}[A-Z0-9]$|^$"`, `MaxLength: 20`, no `MinLength`
    - Description per design §1 (org-level prefix, distinct from PrefixUpper, only needed on the import path)
    - Add `OrgPrefix` to the "Application Resource Naming" metadata group, positioned after `PrefixUpper`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_
  - [x] 2.2 Make `S3ArtifactsBucket` optional and mark deprecated
    - Set `Default: ""`, `AllowedPattern: "^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$|^$"`, `MaxLength: 63`, remove `MinLength`
    - Prefix Description with `DEPRECATED: ` and note derivation from the export (design §2)
    - Keep it in the "External Resources" metadata group; do not rename or remove it
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  - [x] 2.3 Add the `HasS3ArtifactsBucketOverride` condition
    - `HasS3ArtifactsBucketOverride: !Not [!Equals [!Ref S3ArtifactsBucket, ""]]`
    - _Requirements: 3.1, 3.2, 3.3_

- [x] 3. Update the two management-role modules (long-form intrinsics only)
  - [x] 3.1 Update `templates/v2/modules/management-roles/pipeline-mgmt-role.yml`
    - Replace the `ArtifactBucketGetObjectForManagedStacks` `Resource` scalar with the `Fn::If` fallback from design §4 (true branch = `${S3ArtifactsBucket}` ARN; false branch = `Fn::ImportValue Fn::Sub "${OrgPrefix}-S3-Artifacts-Bucket-Name"` via an `Fn::Sub` variable map)
    - Keep Effect and actions (`s3:GetObject`, `s3:GetObjectVersion`) unchanged; leave all other statements unchanged
    - Update the header contract comment to add `OrgPrefix` (parameters) and `HasS3ArtifactsBucketOverride` (conditions)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_
  - [x] 3.2 Update `templates/v2/modules/management-roles/storage-mgmt-role.yml`
    - Apply the identical `Fn::If` fallback and contract-comment update as 3.1
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

- [x] 4. Update the standalone service-role templates for consistency with the modules
  - [x] 4.1 Update `templates/v2/service-role/template-service-role-pipeline.yml`
    - Add the optional deprecated `S3ArtifactsBucket` parameter (design §2)
    - Add the optional `OrgPrefix` parameter (design §1)
    - Add the `HasS3ArtifactsBucketOverride` condition
    - Metadata: `OrgPrefix` under "Application Resource Naming" (after `PrefixUpper`); `S3ArtifactsBucket` under "External Resources"
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.9_
  - [x] 4.2 Update `templates/v2/service-role/template-service-role-storage.yml`
    - Apply the same parameter, condition, and metadata additions as 4.1
    - _Requirements: 6.5, 6.6, 6.7, 6.8, 6.9_

- [x] 5. Unit tests (fast, concrete; no new property-based tests per testing guidelines)
  - [x] 5.1 Add `tests/test_mgmt_role_artifacts_bucket_fallback_unit.py`
    - For both modules: assert `ArtifactBucketGetObjectForManagedStacks` has Effect Allow and actions exactly `[s3:GetObject, s3:GetObjectVersion]`
    - Assert `Resource` is an `Fn::If` with `HasS3ArtifactsBucketOverride` as element 0
    - Assert true branch = `Fn::Sub "arn:aws:s3:::${S3ArtifactsBucket}/${Prefix}-*"`
    - Assert false branch uses `Fn::Sub` list form with `ArtifactsBucketName` → `Fn::ImportValue` → `Fn::Sub "${OrgPrefix}-S3-Artifacts-Bucket-Name"` and template contains `${ArtifactsBucketName}/${Prefix}-*`
    - Assert no shorthand `!`-tag keys in the statement; assert an unrelated statement (`S3ModuleBucketGetObject`) is unchanged
    - Assert header text contains `OrgPrefix` and `HasS3ArtifactsBucketOverride`
    - _Requirements: 4.1-4.7, 5.1-5.7, 10.3_
  - [x] 5.2 Add `tests/test_consuming_templates_artifacts_params_unit.py`
    - For all three consuming templates: assert `OrgPrefix` (`Default ""`, pattern, `MaxLength 20`, no `MinLength`)
    - Assert `S3ArtifactsBucket` (`Default ""`, pattern, `MaxLength 63`, no `MinLength`, Description starts with `DEPRECATED:`)
    - Assert `HasS3ArtifactsBucketOverride` equals `Not(Equals(Ref S3ArtifactsBucket, ""))`
    - Assert metadata grouping for `OrgPrefix` and `S3ArtifactsBucket`
    - Assert bumped header version line for each template
    - _Requirements: 1.1-1.5, 2.1-2.3, 3.1, 6.4, 6.8, 8.1-8.3_
  - [x] 5.3 Run the full test suite; fix any regressions
    - If `test_mgmt_role_allow_transform_operations_unit.py`, `test_iam_tagrole_permissions_boundary_fix_unit.py`, or `test_storage_mgmt_role_s3_pattern_fix_unit.py` assert on the old scalar shape of the artifacts statement, update them to the `Fn::If` structure
    - _Requirements: 10.4_

- [x] 6. Validation
  - [x] 6.1 Run `cfn-lint` over the three modified consuming templates using the repo's existing linter flow; resolve findings without adding new suppressions unless a specific finding requires it
    - _Requirements: 10.1, 10.2_

- [x] 7. Documentation (only for modified templates; preserve existing blockquotes)
  - [x] 7.1 Update `docs/templates/v2/account/prefix-based-infrastructure-README.md`
    - Document the new `OrgPrefix` parameter and the now-optional/deprecated `S3ArtifactsBucket`
    - Document export-based fallback, the account-wide prerequisite (`EnableS3ArtifactsBucket = "true"` + matching `OrgPrefix`), the `Fn::ImportValue` cross-stack dependency, and the native "No export named" failure mode
    - _Requirements: 7.2, 7.3, 9.1, 9.4_
  - [x] 7.2 Update the service-role docs for `template-service-role-pipeline.yml` and `template-service-role-storage.yml` if their README files exist
    - Document the new `OrgPrefix` and deprecated `S3ArtifactsBucket` parameters; preserve blockquotes
    - _Requirements: 9.2, 9.4_
  - [x] 7.3 Update category READMEs only if their parameter tables/descriptions are affected
    - _Requirements: 9.3_

- [x] 8. Update `CHANGELOG.md`
  - Add entries under the existing `v0.0.39 (unreleased)` section referencing this spec, listing the three modified templates with their new versions and a brief description; do not modify existing changelog text
  - _Requirements: 9.5_

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.3", "4.1", "4.2"] },
    { "id": 2, "tasks": ["3.1", "3.2"] },
    { "id": 3, "tasks": ["5.1", "5.2"] },
    { "id": 4, "tasks": ["5.3"] },
    { "id": 5, "tasks": ["6.1"] },
    { "id": 6, "tasks": ["7.1", "7.2", "7.3"] },
    { "id": 7, "tasks": ["8"] }
  ]
}
```

- Task 1 (version bumps) comes first so all subsequent edits land on the incremented versions.
- Tasks 2, 3, and 4 are the template/module changes; task 3 relies on the `OrgPrefix` parameter and `HasS3ArtifactsBucketOverride` condition introduced in task 2, and task 4 mirrors those additions in the standalone templates.
- Task 5 (unit tests) depends on tasks 2-4 being complete; 5.3 runs after 5.1 and 5.2.
- Task 6 (validation) depends on the completed template edits.
- Tasks 7 (documentation) and 8 (changelog) are finalization steps that depend on all preceding work.

## Notes

- Follow the naming conventions in `AGENTS.md` for all resources and IAM scoping (least privilege, resource-scoped ARNs).
- Use long-form intrinsics (`Fn::If`, `Fn::Sub`, `Fn::ImportValue`) inside the `AWS::Include` modules; do not introduce shorthand `!`-tag keys in the modified statement.
- Per the project testing guidelines, prioritize fast unit tests; do not add new property-based tests for this change.
- The change is backward compatible: no parameters removed or renamed, no required parameters added, and no exports changed.
- When updating documentation, preserve existing blockquotes and only touch READMEs for templates actually modified.
