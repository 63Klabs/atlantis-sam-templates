# Implementation Plan: Add Mapping for Regional Template Imports

## Overview

Update 6 CloudFormation templates to support regional S3 bucket resolution for `AWS::Include` module imports. The implementation follows a reference-template-first approach: fully update one template as the reference, then apply the identical pattern to the remaining 5 templates. Testing validates structural correctness, cross-template consistency, and regex patterns. Documentation and changelog are updated last.

## Tasks

- [ ] 1. Version management
  - [ ] 1.1 Increment version for account-wide-infrastructure.yml (if PATCH > 0)
    - Check current version in template header comment
    - If PATCH > 0, increment PATCH by 1 and update date to today
    - If PATCH = 0, skip version increment (development mode)
    - _Requirements: 6.1_
  - [ ] 1.2 Increment version for prefix-based-infrastructure.yml (if PATCH > 0)
    - Check current version in template header comment
    - If PATCH > 0, increment PATCH by 1 and update date to today
    - If PATCH = 0, skip version increment (development mode)
    - _Requirements: 6.2_
  - [ ] 1.3 Increment version for template-service-role-pipeline.yml (if PATCH > 0)
    - Check current version in template header comment
    - If PATCH > 0, increment PATCH by 1 and update date to today
    - If PATCH = 0, skip version increment (development mode)
    - _Requirements: 6.3_
  - [ ] 1.4 Increment version for template-service-role-network-cloudfront.yml (if PATCH > 0)
    - Check current version in template header comment
    - If PATCH > 0, increment PATCH by 1 and update date to today
    - If PATCH = 0, skip version increment (development mode)
    - _Requirements: 6.4_
  - [ ] 1.5 Increment version for template-service-role-network-full.yml (if PATCH > 0)
    - Check current version in template header comment
    - If PATCH > 0, increment PATCH by 1 and update date to today
    - If PATCH = 0, skip version increment (development mode)
    - _Requirements: 6.5_
  - [ ] 1.6 Increment version for template-service-role-storage.yml (if PATCH > 0)
    - Check current version in template header comment
    - If PATCH > 0, increment PATCH by 1 and update date to today
    - If PATCH = 0, skip version increment (development mode)
    - _Requirements: 6.6_

- [ ] 2. Implement reference template (template-service-role-pipeline.yml)
  - [ ] 2.1 Update S3ModuleLocation parameter and add S3ModuleNamespace parameter
    - Replace existing `S3ModuleLocation` parameter with bucket-name-only version: empty default, AllowedPattern `^$|^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$`, updated Description and ConstraintDescription
    - Add new `S3ModuleNamespace` parameter: Type String, Default `atlantis`, AllowedPattern `^[a-z0-9][a-z0-9\-]*(\/[a-z0-9][a-z0-9\-]*)*$`, MinLength 1, MaxLength 128, with Description and ConstraintDescription
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_
  - [ ] 2.2 Add RegionalModuleBuckets mapping and HasS3ModuleLocation condition
    - Add `Mappings` section with `RegionalModuleBuckets` mapping containing 4 regions: us-east-1 → `63klabs-atlas-us-east-1`, us-east-2 → `63klabs-zenith-us-east-2`, us-west-1 → `63klabs-fabric-us-west-1`, us-west-2 → `63klabs-orbit-us-west-2`, each with key `BucketName`
    - Add `HasS3ModuleLocation` condition: `!Not [!Equals [!Ref S3ModuleLocation, ""]]`
    - Use standard section comment format for the Mappings section
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.3, 4.4_
  - [ ] 2.3 Update AWS::Include Location references to use !Sub with variable map
    - Replace all 2 `AWS::Include` Location values with the `!Sub` variable map pattern
    - Each Location becomes: `!Sub` with string `s3://${BucketName}/${Namespace}/templates/v2/modules/<module-path>` and variable map with `BucketName: !If [HasS3ModuleLocation, !Ref S3ModuleLocation, !FindInMap [RegionalModuleBuckets, !Ref "AWS::Region", BucketName]]` and `Namespace: !Ref S3ModuleNamespace`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.7, 6.8_
  - [ ] 2.4 Update Metadata parameter group to include S3ModuleNamespace
    - Update the "Module Source" parameter group to list both `S3ModuleLocation` and `S3ModuleNamespace`
    - _Requirements: 7.1, 7.2, 7.3_

- [ ] 3. Checkpoint - Verify reference template
  - Ensure the reference template (template-service-role-pipeline.yml) is valid YAML and structurally correct. Ask the user if questions arise.

- [ ] 4. Apply pattern to account templates
  - [ ] 4.1 Update account-wide-infrastructure.yml
    - Apply identical S3ModuleLocation parameter (bucket-name-only), S3ModuleNamespace parameter, RegionalModuleBuckets mapping, HasS3ModuleLocation condition, and Metadata parameter group changes
    - Update all 5 `AWS::Include` Location references to use the `!Sub` variable map pattern, preserving each module's specific path
    - _Requirements: 1.1–1.6, 2.1–2.6, 3.1–3.6, 4.1–4.4, 5.1–5.6, 6.1, 6.7, 6.8, 6.9, 7.1, 7.2, 7.3_
  - [ ] 4.2 Update prefix-based-infrastructure.yml
    - Apply identical S3ModuleLocation parameter (bucket-name-only), S3ModuleNamespace parameter, RegionalModuleBuckets mapping, HasS3ModuleLocation condition, and Metadata parameter group changes
    - Update all 10 `AWS::Include` Location references to use the `!Sub` variable map pattern, preserving each module's specific path
    - _Requirements: 1.1–1.6, 2.1–2.6, 3.1–3.6, 4.1–4.4, 5.1–5.6, 6.2, 6.7, 6.8, 6.9, 7.1, 7.2, 7.3_

- [ ] 5. Apply pattern to service-role templates
  - [ ] 5.1 Update template-service-role-network-cloudfront.yml
    - Apply identical S3ModuleLocation parameter (bucket-name-only), S3ModuleNamespace parameter, RegionalModuleBuckets mapping, HasS3ModuleLocation condition, and Metadata parameter group changes
    - Update all 3 `AWS::Include` Location references to use the `!Sub` variable map pattern, preserving each module's specific path
    - _Requirements: 1.1–1.6, 2.1–2.6, 3.1–3.6, 4.1–4.4, 5.1–5.6, 6.4, 6.7, 6.8, 6.9, 7.1, 7.2, 7.3_
  - [ ] 5.2 Update template-service-role-network-full.yml
    - Apply identical S3ModuleLocation parameter (bucket-name-only), S3ModuleNamespace parameter, RegionalModuleBuckets mapping, HasS3ModuleLocation condition, and Metadata parameter group changes
    - Update all 4 `AWS::Include` Location references to use the `!Sub` variable map pattern, preserving each module's specific path
    - _Requirements: 1.1–1.6, 2.1–2.6, 3.1–3.6, 4.1–4.4, 5.1–5.6, 6.5, 6.7, 6.8, 6.9, 7.1, 7.2, 7.3_
  - [ ] 5.3 Update template-service-role-storage.yml
    - Apply identical S3ModuleLocation parameter (bucket-name-only), S3ModuleNamespace parameter, RegionalModuleBuckets mapping, HasS3ModuleLocation condition, and Metadata parameter group changes
    - Update all 2 `AWS::Include` Location references to use the `!Sub` variable map pattern, preserving each module's specific path
    - _Requirements: 1.1–1.6, 2.1–2.6, 3.1–3.6, 4.1–4.4, 5.1–5.6, 6.6, 6.7, 6.8, 6.9, 7.1, 7.2, 7.3_

- [ ] 6. Checkpoint - Verify all templates updated
  - Ensure all 6 templates are valid YAML and structurally correct. Ask the user if questions arise.

- [ ] 7. Testing
  - [ ] 7.1 Create unit tests for regional module bucket resolution
    - Create `tests/test_regional_module_buckets_unit.py`
    - Test S3ModuleLocation parameter: Type is String, Default is empty string, AllowedPattern matches `^$|^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$`
    - Test S3ModuleNamespace parameter: Type is String, Default is `atlantis`, AllowedPattern matches expected regex, MinLength 1, MaxLength 128
    - Test RegionalModuleBuckets mapping: contains exactly 4 regions with correct bucket names and `BucketName` key
    - Test HasS3ModuleLocation condition: exists and uses `!Not [!Equals [...]]` pattern referencing S3ModuleLocation
    - Test all `AWS::Include` Location values use `!Sub` with variable map containing `BucketName` and `Namespace` keys
    - Test Metadata "Module Source" parameter group contains both `S3ModuleLocation` and `S3ModuleNamespace`
    - Run tests against all 6 templates using parameterized test fixtures
    - _Requirements: 1.1–1.5, 2.1–2.5, 3.1–3.6, 4.1–4.2, 5.5, 5.6, 7.1, 7.2_
  - [ ] 7.2 Create cross-template consistency verification tests
    - Add test class in same test file verifying character-for-character identical parameter definitions, mapping entries, condition logic, and `!Sub` variable map structure across all 6 templates
    - Only module paths within Location URIs should differ
    - _Requirements: 6.9_
  - [ ] 7.3 Create regex pattern validation tests
    - Add test class validating S3ModuleLocation AllowedPattern against known valid inputs (empty string, `my-bucket`, `63klabs-atlas-us-east-1`) and invalid inputs (`bucket/path`, `UPPERCASE`, `bucket_underscore`, `-leading-dash`, `a`, `ab`)
    - Add test class validating S3ModuleNamespace AllowedPattern against known valid inputs (`atlantis`, `atlantis-v2`, `org/project`, `a`) and invalid inputs (`/leading-slash`, `trailing-slash/`, empty string, `UPPER`, `-leading-dash`)
    - Use `cfn_test_utils.validate_regex_pattern` helper
    - _Requirements: 1.4, 1.6, 2.4_

- [ ] 8. Run cfn-lint validation
  - [ ] 8.1 Run cfn-lint against all 6 modified templates
    - Execute cfn-lint validation using the existing `cfn_linter` module or direct CLI invocation
    - Verify all templates pass with no errors (warnings from AWS::Include suppression are expected)
    - Fix any validation errors found
    - _Requirements: 6.1–6.6_

- [ ] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Documentation and changelog
  - [ ] 10.1 Update template documentation for affected templates
    - Update `docs/templates/v2/service-role/template-service-role-pipeline-README.md` to document new S3ModuleNamespace parameter, updated S3ModuleLocation parameter, RegionalModuleBuckets mapping, and HasS3ModuleLocation condition
    - Create or update documentation for remaining affected templates that have README files in `docs/templates/v2/`
    - Add "Module Source" parameter group documentation with both parameters
    - Add "Mappings" section documenting the 4-region bucket mapping
    - Add "Conditions" section documenting HasS3ModuleLocation
    - _Requirements: 7.1, 7.2, 7.3_
  - [ ] 10.2 Update CHANGELOG.md with v0.0.36 entry
    - Add entry under the unreleased v0.0.36 section (create section if needed)
    - Categorize under "Changed" with reference to all 6 templates and their version numbers
    - Include spec reference: `[Spec: 0-0-36-add-mapping-for-regional-template-imports](../.kiro/specs/0-0-36-add-mapping-for-regional-template-imports/)`
    - Describe the change: Added regional S3 bucket mapping for AWS::Include module resolution, enabling multi-region deployment without manual bucket specification
    - _Requirements: 6.1–6.6_

- [ ] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All 6 templates receive character-for-character identical additions (parameters, mapping, condition, variable map structure) — only the module paths differ
- Templates are in development mode (PATCH = 0), so version increments will be skipped per the version control steering document
- The design explicitly states property-based testing does not apply to this feature (declarative IaC configuration)
- The testing steering document prioritizes fast unit tests over property-based tests
- cfn-lint validation serves as the primary structural correctness check
- The reference template approach (task 2) establishes the exact pattern before replicating across remaining templates

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6"] },
    { "id": 1, "tasks": ["2.1"] },
    { "id": 2, "tasks": ["2.2"] },
    { "id": 3, "tasks": ["2.3", "2.4"] },
    { "id": 4, "tasks": ["4.1", "4.2", "5.1", "5.2", "5.3"] },
    { "id": 5, "tasks": ["7.1", "7.2", "7.3", "8.1"] },
    { "id": 6, "tasks": ["10.1", "10.2"] }
  ]
}
```
