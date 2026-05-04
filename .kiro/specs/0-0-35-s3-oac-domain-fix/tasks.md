# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Global S3 Domain Format in OriginBucketDomainForCloudFront Output
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists in the unfixed template
  - **Scoped PBT Approach**: This is a deterministic bug in a single template file; scope the test to the concrete `OriginBucketDomainForCloudFront` output value
  - Create test file `tests/test_storage_s3_oac_domain_unit.py`
  - Load the template using `load_template()` from `tests/cfn_test_utils.py` at path `templates/v2/storage/template-storage-s3-oac-for-cloudfront.yml`
  - Test 1: Assert `OriginBucketDomainForCloudFront` output value uses `!Sub` (not `!GetAtt`) — from `isBugCondition`: output.Value uses `!GetAtt OriginBucketRegional.DomainName`
  - Test 2: Assert the output value contains `AWS::Region` — from `isBugCondition`: output.Value does NOT contain `AWS::Region`
  - Test 3: Assert the output value matches the regional domain pattern `https://${OriginBucketRegional}.s3.${AWS::Region}.amazonaws.com` — from `expectedBehavior` in design
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (this is correct - it proves the bug exists: the output uses `!GetAtt OriginBucketRegional.DomainName` which produces the global domain format)
  - Document counterexamples found (e.g., "Output value is `{'!GetAtt': 'OriginBucketRegional.DomainName'}` instead of a `!Sub` expression with regional domain format")
  - Mark task complete when tests are written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 2.1, 2.2_

- [x] 2. Write preservation tests (BEFORE implementing fix)
  - **Property 2: Preservation** - All Other Template Content Unchanged
  - **IMPORTANT**: Follow observation-first methodology — observe behavior on UNFIXED code, then write tests asserting that behavior
  - Observe: Parse the UNFIXED template and record all parameters, conditions, resources, and other outputs
  - Write unit tests in the same file `tests/test_storage_s3_oac_domain_unit.py` capturing observed behavior:
    - Test all parameters remain identical (Prefix, ProjectId, S3BucketNameOrgPrefix, RolePath, AlarmNotificationEmail, PermissionsBoundaryArn, S3LogBucketName, InvalidatorArn)
    - Test all conditions remain identical (UseS3BucketNameOrgPrefix, HasLoggingBucket, HasInvalidatorArn)
    - Test `OriginBucketRegional` S3 bucket resource properties are unchanged (BucketName, BucketEncryption, PublicAccessBlockConfiguration, DeletionPolicy)
    - Test `BucketPolicy` resource and all policy statements are unchanged (DenyNonSecureTransportAccess, AllowCloudFrontServicePrincipalReadOnly, AllowCodeBuildReadWriteDelete)
    - Test `S3InvokeLambdaPermission` resource is unchanged (Condition, Properties)
    - Test `BucketName` output value is unchanged (`!Ref OriginBucketRegional`)
    - Test `AllowedCloudFrontAndCodeBuild` output value is unchanged (`!Sub "${Prefix}-${ProjectId}"`)
    - Test `LoggingBucketName`, `InvalidatorArn`, `InvalidationEventsEnabled` outputs are unchanged
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Fix for S3 OAC regional domain format in OriginBucketDomainForCloudFront output

  - [x] 3.1 Increment template version from v0.1.1 to v0.1.2
    - Update the version comment in `templates/v2/storage/template-storage-s3-oac-for-cloudfront.yml`
    - Change `# Version: v0.1.1/2026-03-29` to `# Version: v0.1.2/<current-date>` (PATCH increment for non-breaking bug fix)
    - _Requirements: 2.1, 2.2_

  - [x] 3.2 Implement the fix — replace !GetAtt with !Sub for regional domain
    - In `templates/v2/storage/template-storage-s3-oac-for-cloudfront.yml`, update the `OriginBucketDomainForCloudFront` output
    - Replace: `Value: !GetAtt OriginBucketRegional.DomainName`
    - With: `Value: !Sub "https://${OriginBucketRegional}.s3.${AWS::Region}.amazonaws.com"`
    - _Bug_Condition: isBugCondition(template) where output.Value uses !GetAtt OriginBucketRegional.DomainName AND does NOT contain AWS::Region_
    - _Expected_Behavior: output.Value uses !Sub with regional domain pattern https://${OriginBucketRegional}.s3.${AWS::Region}.amazonaws.com_
    - _Preservation: All other template content (parameters, conditions, resources, other outputs) must remain unchanged_
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.3 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Regional S3 Domain Format in OriginBucketDomainForCloudFront Output
    - **IMPORTANT**: Re-run the SAME tests from task 1 - do NOT write new tests
    - The tests from task 1 encode the expected behavior (uses `!Sub`, contains `AWS::Region`, matches regional pattern)
    - When these tests pass, it confirms the expected behavior is satisfied
    - Run bug condition exploration tests from step 1
    - **EXPECTED OUTCOME**: Tests PASS (confirms bug is fixed)
    - _Requirements: 2.1, 2.2_

  - [x] 3.4 Verify preservation tests still pass
    - **Property 2: Preservation** - All Other Template Content Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all preservation tests still pass after fix (no regressions)

  - [x] 3.5 Run cfn-lint validation on the fixed template
    - Run `cfn-lint templates/v2/storage/template-storage-s3-oac-for-cloudfront.yml` to validate the fixed template
    - Ensure no new linting errors are introduced by the fix
    - _Requirements: 2.1, 2.2_

  - [x] 3.6 Add changelog entry under v0.0.35 (unreleased) section
    - Update `CHANGELOG.md` — replace `TODO` under `## v0.0.35 (unreleased)` with a `### Fixed` section
    - Add entry: `- **Storage: template-storage-s3-oac-for-cloudfront.yml v0.1.2** - Fixed OriginBucketDomainForCloudFront output to use regional S3 domain format (`https://<bucket>.s3.<region>.amazonaws.com`) instead of global format, preventing 307 redirects for CloudFront distributions using OAC [Spec: 0-0-35-s3-oac-domain-fix](../.kiro/specs/0-0-35-s3-oac-domain-fix/) addresses [#3](https://github.com/63Klabs/atlantis-sam-templates/issues/3)`
    - Do NOT modify any existing changelog entries
    - _Requirements: 2.1, 2.2_

  - [x] 3.7 Update template documentation
    - Update `docs/templates/v2/storage/template-storage-s3-oac-for-cloudfront-README.md`
    - Update the version number from `v0.1.0/2025-12-08` to `v0.1.2/<current-date>`
    - Update the `OriginBucketDomainForCloudFront` output description to reflect the regional domain format with `https://` prefix
    - Preserve all existing blockquotes and custom content
    - _Requirements: 2.1, 2.2_

- [x] 4. Checkpoint - Ensure all tests pass
  - Run the full test file: `python -m pytest tests/test_storage_s3_oac_domain_unit.py -v`
  - Ensure all bug condition exploration tests pass (confirming fix works)
  - Ensure all preservation tests pass (confirming no regressions)
  - Ensure cfn-lint validation passes
  - Ask the user if questions arise
