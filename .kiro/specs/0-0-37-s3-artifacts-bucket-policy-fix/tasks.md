# Implementation Plan

## Overview

Fix the `s3-artifacts-bucket-policy.yml` module that fails with "Invalid principal in policy" by converting named `Principal.AWS` ARNs to `Principal: "*"` with `aws:PrincipalArn` `ArnLike` conditions, and correcting reversed wildcard patterns to match the role suffix convention (`*-CodePipelineServiceRole`, `*-CodeBuildServiceRole`, `*-CloudFormationSvcRole`). The fix uses the exploratory bugfix workflow: write tests to confirm the bug, write preservation tests to capture correct behavior, then implement and verify.

## Tasks

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Named Principal with Reversed Wildcard Patterns
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists (reversed patterns + named principals)
  - **Scoped PBT Approach**: Scope to the concrete failing structure: WhitelistedGet/WhitelistedPut use named Principal.AWS with role-type-prefix patterns (e.g., `CodePipelineServiceRole-*`)
  - Create test file: `tests/test_s3_artifacts_bucket_policy_unit.py`
  - Load unfixed template from `templates/v2/modules/account-wide/s3-artifacts-bucket-policy.yml` using `cfn_test_utils.load_template`
  - Test class `TestBugConditionPrincipalStructure`:
    - Assert WhitelistedGet uses `Principal: "*"` (not `Principal.AWS` named ARNs) — will FAIL on unfixed code
    - Assert WhitelistedPut uses `Principal: "*"` (not `Principal.AWS` named ARNs) — will FAIL on unfixed code
    - Assert WhitelistedGet has `Condition.ArnLike["aws:PrincipalArn"]` — will FAIL on unfixed code
    - Assert WhitelistedPut has `Condition.ArnLike["aws:PrincipalArn"]` — will FAIL on unfixed code
  - Test class `TestBugConditionWildcardPatterns`:
    - Assert ArnLike patterns end with `-CodePipelineServiceRole` (suffix convention) — will FAIL because current patterns use `CodePipelineServiceRole-*` (prefix convention)
    - Assert ArnLike patterns end with `-CodeBuildServiceRole` — will FAIL
    - Assert ArnLike patterns end with `-CloudFormationSvcRole` — will FAIL
    - Test fnmatch: pattern `*-CodePipelineServiceRole` matches `acme-Worker-myapp-test-CodePipelineServiceRole` — will FAIL because current pattern is reversed
  - Run test on UNFIXED code: `pytest tests/test_s3_artifacts_bucket_policy_unit.py -v`
  - **EXPECTED OUTCOME**: Tests FAIL (this is correct — it proves the bug exists)
  - Document counterexamples found (e.g., "WhitelistedGet uses Principal.AWS list instead of Principal: '*' with Condition")
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - DenyNonSecureTransport, Actions, and Resource Scoping Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe on UNFIXED code: DenyNonSecureTransportAccess statement structure (Principal: "*", Effect: Deny, Action: "s3:*", Condition: Bool aws:SecureTransport false)
  - Observe on UNFIXED code: WhitelistedGet actions are s3:GetObject, s3:GetObjectVersion, s3:GetBucketVersioning
  - Observe on UNFIXED code: WhitelistedPut actions are s3:PutObject
  - Observe on UNFIXED code: Resource references use `Fn::GetAtt: [S3ArtifactsBucketRegional, Arn]` and joined ARN/*
  - Observe on UNFIXED code: Resource-level `Condition: EnableS3ArtifactsBucket` is present
  - Observe on UNFIXED code: Policy has Version "2012-10-17" and Id "SSEAndSSLPolicy"
  - Add test class `TestPreservationDenyStatement` in same test file:
    - Assert DenyNonSecureTransportAccess Sid exists
    - Assert DenyNonSecureTransportAccess Effect is "Deny"
    - Assert DenyNonSecureTransportAccess Principal is "*"
    - Assert DenyNonSecureTransportAccess Action is "s3:*"
    - Assert DenyNonSecureTransportAccess Condition is `Bool: {"aws:SecureTransport": false}`
    - Assert DenyNonSecureTransportAccess Resource references S3ArtifactsBucketRegional ARN and ARN/*
  - Add test class `TestPreservationActionsAndResources`:
    - Assert WhitelistedGet actions are exactly: s3:GetObject, s3:GetObjectVersion, s3:GetBucketVersioning
    - Assert WhitelistedPut actions are exactly: s3:PutObject
    - Assert WhitelistedGet Resource references S3ArtifactsBucketRegional ARN and ARN/*
    - Assert WhitelistedPut Resource references S3ArtifactsBucketRegional ARN and ARN/*
  - Add test class `TestPreservationStructure`:
    - Assert resource-level Condition is `EnableS3ArtifactsBucket`
    - Assert PolicyDocument Version is "2012-10-17"
    - Assert PolicyDocument Id is "SSEAndSSLPolicy"
    - Assert there are exactly 3 statements (DenyNonSecureTransportAccess, WhitelistedGet, WhitelistedPut)
  - Run tests on UNFIXED code: `pytest tests/test_s3_artifacts_bucket_policy_unit.py::TestPreservationDenyStatement tests/test_s3_artifacts_bucket_policy_unit.py::TestPreservationActionsAndResources tests/test_s3_artifacts_bucket_policy_unit.py::TestPreservationStructure -v`
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Fix S3 artifacts bucket policy principal and wildcard patterns

  - [x] 3.1 Implement the fix
    - File: `templates/v2/modules/account-wide/s3-artifacts-bucket-policy.yml`
    - Replace WhitelistedGet `Principal.AWS` (list of named ARNs) with `Principal: "*"`
    - Add Condition block to WhitelistedGet with `ArnLike` on `aws:PrincipalArn`:
      - `Fn::Sub: "arn:aws:iam::${AWS::AccountId}:role${RolePath}*-CodePipelineServiceRole"`
      - `Fn::Sub: "arn:aws:iam::${AWS::AccountId}:role${RolePath}*-CodeBuildServiceRole"`
      - `Fn::Sub: "arn:aws:iam::${AWS::AccountId}:role${RolePath}*-CloudFormationSvcRole"`
    - Replace WhitelistedPut `Principal.AWS` (list of named ARNs) with `Principal: "*"`
    - Add Condition block to WhitelistedPut with `ArnLike` on `aws:PrincipalArn`:
      - `Fn::Sub: "arn:aws:iam::${AWS::AccountId}:role${RolePath}*-CodePipelineServiceRole"`
      - `Fn::Sub: "arn:aws:iam::${AWS::AccountId}:role${RolePath}*-CodeBuildServiceRole"`
    - Preserve DenyNonSecureTransportAccess statement unchanged
    - Preserve all actions, resources, Sid values, and condition gating unchanged
    - _Bug_Condition: isBugCondition(input) where WhitelistedGet/WhitelistedPut use named Principal.AWS with reversed wildcard patterns_
    - _Expected_Behavior: Principal: "*" with ArnLike condition using suffix patterns (*-RoleType)_
    - _Preservation: DenyNonSecureTransportAccess unchanged, actions unchanged, resource ARNs unchanged, EnableS3ArtifactsBucket condition unchanged_
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Named Principal with Reversed Wildcard Patterns
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior (Principal: "*" with ArnLike condition using suffix patterns)
    - When this test passes, it confirms the expected behavior is satisfied
    - Run: `pytest tests/test_s3_artifacts_bucket_policy_unit.py::TestBugConditionPrincipalStructure tests/test_s3_artifacts_bucket_policy_unit.py::TestBugConditionWildcardPatterns -v`
    - **EXPECTED OUTCOME**: Tests PASS (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - DenyNonSecureTransport, Actions, and Resource Scoping Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run: `pytest tests/test_s3_artifacts_bucket_policy_unit.py::TestPreservationDenyStatement tests/test_s3_artifacts_bucket_policy_unit.py::TestPreservationActionsAndResources tests/test_s3_artifacts_bucket_policy_unit.py::TestPreservationStructure -v`
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all preservation tests still pass after fix

- [x] 4. Update CHANGELOG.md
  - Add entry under the existing `## v0.0.38 (unreleased)` section
  - Add `### Fixed` category
  - Entry: `- **Modules: s3-artifacts-bucket-policy.yml** - Fixed "Invalid principal in policy" error by converting named Principal.AWS ARNs to Principal: "*" with aws:PrincipalArn ArnLike conditions, and corrected reversed wildcard patterns to match role suffix convention [Spec: 0-0-38-s3-artifacts-bucket-policy-fix](.kiro/specs/0-0-38-s3-artifacts-bucket-policy-fix/)`
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4_

- [x] 5. Update documentation for modified templates
  - Review and update `docs/templates/v2/account/account-wide-infrastructure-README.md` if it references the bucket policy module behavior
  - Verify documentation describes the condition-based principal approach (Principal: "*" with ArnLike)
  - Ensure examples and troubleshooting sections reflect the corrected pattern convention
  - Preserve all existing blockquotes and custom content
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 6. Checkpoint - Ensure all tests pass
  - Run full test suite: `pytest tests/test_s3_artifacts_bucket_policy_unit.py -v`
  - Ensure all bug condition tests pass (confirms fix works)
  - Ensure all preservation tests pass (confirms no regressions)
  - Validate the fixed YAML template is well-formed and parseable
  - Ask the user if questions arise

## Notes

- The module snippet (`s3-artifacts-bucket-policy.yml`) has no version header — no version increment needed
- The parent template (`account-wide-infrastructure.yml`) is at v0.0.0 (PATCH=0, development mode) — no version increment needed
- Per testing-guidelines steering: focus on unit tests, property-based tests are not critical for this repository
- Per changelog steering: update CHANGELOG.md under the existing `## v0.0.38 (unreleased)` section
- Per documentation steering: update documentation for modified templates as a final task
- The fix addresses two compounding issues simultaneously: reversed wildcard patterns and named principal validation at creation time

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2"] },
    { "id": 2, "tasks": ["3.1"] },
    { "id": 3, "tasks": ["3.2", "3.3"] },
    { "id": 4, "tasks": ["4", "5"] },
    { "id": 5, "tasks": ["6"] }
  ]
}
```
