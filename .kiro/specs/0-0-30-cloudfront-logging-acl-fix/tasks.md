# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - CloudFront Legacy Logging ACL Not Supported
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists in the unfixed template
  - **Scoped PBT Approach**: The bug is deterministic - scope the property to the concrete failing case: `AllowLegacyCloudFrontLogs=true` with the current template
  - Create test file `tests/test_storage_s3_access_logs_unit.py` with a fixture loading `templates/v2/storage/template-storage-s3-access-logs.yml`
  - Test that `AllowLegacyCloudFrontLogs` parameter exists with Type `String`, Default `"false"`, AllowedValues `["true", "false"]` (will FAIL - parameter missing)
  - Test that `EnableLegacyCloudFrontLogs` condition exists (will FAIL - condition missing)
  - Test that `BlockPublicAcls` uses `!If` conditional logic referencing `EnableLegacyCloudFrontLogs` (will FAIL - hardcoded to `true`)
  - Test that `OwnershipControls` with `ObjectOwnership: BucketOwnerPreferred` is present when CloudFront logging enabled (will FAIL - not present)
  - Test that bucket policy contains a statement with Sid `AllowCloudFrontLogDelivery` for principal `delivery.logs.amazonaws.com` with action `s3:PutObject` and condition `s3:x-amz-acl: bucket-owner-full-control` (will FAIL - statement missing)
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (this is correct - it proves the bug exists)
  - Document counterexamples found to understand root cause
  - Mark task complete when tests are written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4_

- [x] 2. Write preservation tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Default Configuration Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe the UNFIXED template structure for non-buggy inputs (default configuration where CloudFront logging is not enabled)
  - Add preservation tests to `tests/test_storage_s3_access_logs_unit.py`
  - Observe: `BlockPublicAcls` is `true` on unfixed code - write test asserting this
  - Observe: `BlockPublicPolicy` is `true`, `IgnorePublicAcls` is `true`, `RestrictPublicBuckets` is `true` - write tests asserting these
  - Observe: `AllowS3LogDelivery` policy statement exists with principal `logging.s3.amazonaws.com` and action `s3:PutObject` - write test asserting this
  - Observe: `DenyNonSecureTransportAccess` policy statement exists with Effect `Deny`, Action `s3:*`, Condition `aws:SecureTransport: false` - write test asserting this
  - Observe: `BucketEncryption` uses `AES256` SSE algorithm - write test asserting this
  - Observe: `LifecycleConfiguration` has rule `DeleteOldLogs` with `ExpirationInDays` referencing `LogExpirationInDays` - write test asserting this
  - Observe: `DeletionPolicy: Retain` and `UpdateReplacePolicy: Retain` on Bucket resource - write test asserting this
  - Observe: Bucket naming uses `Prefix`, `ProjectId`, `AWS::Region`, `AWS::AccountId`, and conditional `S3BucketNameOrgPrefix` - write test asserting this
  - Observe: Outputs `LoggingBucketName` and `LoggingBucketArn` exist with exports - write test asserting this
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

- [x] 3. Fix for CloudFront legacy logging ACL support

  - [x] 3.1 Increment template version from v0.0.1 to v0.0.2
    - Update the version comment from `v0.0.1/2025-05-10` to `v0.0.2/YYYY-MM-DD` (use current date)
    - Version increment happens BEFORE making functional changes per version control steering
    - _Requirements: 2.1_

  - [x] 3.2 Add `AllowLegacyCloudFrontLogs` parameter
    - Add parameter under a new `# CloudFront Legacy Logging` subsection in Parameters
    - Type: `String`, Default: `"false"`, AllowedValues: `["true", "false"]`
    - Description explaining the purpose and effect of enabling legacy CloudFront logging
    - _Bug_Condition: isBugCondition(template_config) where AllowLegacyCloudFrontLogs == "true" AND BlockPublicAcls == true AND OwnershipControls IS NOT DEFINED AND no delivery.logs.amazonaws.com policy_
    - _Expected_Behavior: Parameter exists with correct type, default, and allowed values_
    - _Preservation: Default "false" ensures existing deployments unaffected_
    - _Requirements: 2.1, 3.8_

  - [x] 3.3 Add `EnableLegacyCloudFrontLogs` condition
    - Add condition: `EnableLegacyCloudFrontLogs: !Equals [!Ref AllowLegacyCloudFrontLogs, "true"]`
    - Place in Conditions section alongside existing `UseS3BucketNameOrgPrefix`
    - _Requirements: 2.1_

  - [x] 3.4 Make `BlockPublicAcls` conditional
    - Change `BlockPublicAcls: true` to `BlockPublicAcls: !If [EnableLegacyCloudFrontLogs, false, true]`
    - Keep `BlockPublicPolicy: true`, `IgnorePublicAcls: true`, `RestrictPublicBuckets: true` unchanged
    - _Bug_Condition: BlockPublicAcls unconditionally true prevents ACL grants_
    - _Expected_Behavior: BlockPublicAcls resolves to false when enabled, true when disabled_
    - _Preservation: Other PublicAccessBlockConfiguration properties remain true always_
    - _Requirements: 2.2, 2.5, 3.5_

  - [x] 3.5 Add conditional `OwnershipControls`
    - Add `OwnershipControls: !If [EnableLegacyCloudFrontLogs, {Rules: [{ObjectOwnership: BucketOwnerPreferred}]}, !Ref "AWS::NoValue"]` to Bucket resource
    - _Bug_Condition: OwnershipControls not defined, CloudFront cannot use ACL-based delivery_
    - _Expected_Behavior: BucketOwnerPreferred when enabled, absent when disabled_
    - _Preservation: No OwnershipControls when disabled (same as current)_
    - _Requirements: 2.3, 2.5_

  - [x] 3.6 Add conditional CloudFront log delivery policy statement
    - Add new statement to `LoggingBucketPolicy.PolicyDocument.Statement` array
    - Sid: `AllowCloudFrontLogDelivery`
    - Effect: `Allow`
    - Principal: `{Service: delivery.logs.amazonaws.com}`
    - Action: `s3:PutObject`
    - Resource: `${Bucket.Arn}/*`
    - Condition: `StringEquals: {"s3:x-amz-acl": "bucket-owner-full-control"}`
    - Wrap entire statement in `!If [EnableLegacyCloudFrontLogs, {...}, !Ref "AWS::NoValue"]`
    - _Bug_Condition: No policy statement for delivery.logs.amazonaws.com_
    - _Expected_Behavior: CloudFront log delivery statement present when enabled, absent when disabled_
    - _Preservation: Existing AllowS3LogDelivery and DenyNonSecureTransportAccess statements unchanged_
    - _Requirements: 2.4, 2.5, 3.1, 3.2_

  - [x] 3.7 Update Metadata parameter groups
    - Add `AllowLegacyCloudFrontLogs` to the Metadata `ParameterGroups`
    - Add to existing "Log Settings" group or create a new "CloudFront Legacy Logging" group
    - _Requirements: 2.1_

  - [x] 3.8 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - CloudFront Legacy Logging ACL Supported
    - **IMPORTANT**: Re-run the SAME tests from task 1 - do NOT write new tests
    - The tests from task 1 encode the expected behavior
    - When these tests pass, it confirms the expected behavior is satisfied
    - Run bug condition exploration tests from step 1
    - **EXPECTED OUTCOME**: Tests PASS (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 3.9 Verify preservation tests still pass
    - **Property 2: Preservation** - Default Configuration Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all preservation tests still pass after fix (no regressions)

- [x] 4. Write fix verification unit tests
  - Add tests to `tests/test_storage_s3_access_logs_unit.py` verifying the fix works correctly on the FIXED template
  - Test that when `AllowLegacyCloudFrontLogs` is `true`, `BlockPublicAcls` resolves to `false` via `!If` (first element of `!If` list is `EnableLegacyCloudFrontLogs`, second is `false`)
  - Test that when `AllowLegacyCloudFrontLogs` is `false`/default, `BlockPublicAcls` resolves to `true` via `!If` (third element of `!If` list is `true`)
  - Test that `OwnershipControls` uses `!If` with `EnableLegacyCloudFrontLogs` condition and `AWS::NoValue` fallback
  - Test that CloudFront log delivery policy statement uses `!If` with `EnableLegacyCloudFrontLogs` condition and `AWS::NoValue` fallback
  - Test that CloudFront policy statement has correct Sid, Effect, Principal, Action, Resource, and Condition
  - Test that all other `PublicAccessBlockConfiguration` properties (`BlockPublicPolicy`, `IgnorePublicAcls`, `RestrictPublicBuckets`) remain unconditionally `true`
  - Test that `AllowLegacyCloudFrontLogs` appears in Metadata `ParameterGroups`
  - Test that template version comment is `v0.0.2`
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.5_

- [x] 5. Integration test - cfn-lint validation
  - Run `cfn-lint` against the fixed template `templates/v2/storage/template-storage-s3-access-logs.yml`
  - Verify no errors or warnings are reported
  - Verify the template is valid YAML and conforms to CloudFormation schema
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 6. Update documentation for template-storage-s3-access-logs
  - Update `docs/templates/v2/storage/template-storage-s3-access-logs-README.md`
  - Add `AllowLegacyCloudFrontLogs` parameter documentation with attribute table
  - Add `EnableLegacyCloudFrontLogs` condition documentation
  - Update Resources section to document conditional `OwnershipControls` and CloudFront log delivery policy statement
  - Update version number to v0.0.2
  - Preserve any existing blockquotes and custom content
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 7. Update CHANGELOG.md
  - Add entry under the `v0.0.30 - unreleased` section
  - Category: `Fixed`
  - Format: `**Storage: template-storage-s3-access-logs.yml v0.0.2** - Added optional CloudFront legacy logging support with AllowLegacyCloudFrontLogs parameter [Spec: cloudfront-logging-acl-fix](../.kiro/specs/cloudfront-logging-acl-fix/)`
  - _Requirements: 2.1_

- [x] 8. Checkpoint - Ensure all tests pass
  - Run full test suite for `tests/test_storage_s3_access_logs_unit.py`
  - Ensure all bug condition, preservation, and fix verification tests pass
  - Ensure cfn-lint validation passes
  - Ask the user if questions arise
