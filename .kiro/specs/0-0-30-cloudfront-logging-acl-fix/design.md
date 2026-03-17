# CloudFront Legacy Logging ACL Fix - Bugfix Design

## Overview

The S3 access logs bucket template (`templates/v2/storage/template-storage-s3-access-logs.yml`) unconditionally blocks ACL access, preventing CloudFront standard (legacy) logging from writing to the bucket. CloudFront standard logging requires ACL-based write access, `ObjectOwnership: BucketOwnerPreferred`, and a bucket policy statement for `delivery.logs.amazonaws.com`.

The fix adds an opt-in `AllowLegacyCloudFrontLogs` parameter (default `false`) that conditionally relaxes `BlockPublicAcls`, adds `OwnershipControls`, and appends a CloudFront log delivery policy statement. When disabled, the bucket retains its current secure configuration. The template version increments from v0.0.1 to v0.0.2 as a non-breaking PATCH change (adding an optional parameter with a safe default).

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug — when a user sets this bucket as a CloudFront standard logging destination, the deployment fails because ACL access is unconditionally blocked
- **Property (P)**: The desired behavior — when `AllowLegacyCloudFrontLogs` is `true`, the bucket allows ACL grants, sets `BucketOwnerPreferred` ownership, and includes the CloudFront log delivery policy statement
- **Preservation**: Existing S3 log delivery, encryption, lifecycle, public access blocks (except `BlockPublicAcls` when opted in), bucket naming, retention policies, and non-secure transport denial must remain unchanged
- **AllowLegacyCloudFrontLogs**: A new `String` parameter in the template with allowed values `true`/`false` (default `false`) that controls whether CloudFront legacy logging support is enabled
- **EnableLegacyCloudFrontLogs**: A CloudFormation condition that evaluates to `true` when `AllowLegacyCloudFrontLogs` equals `"true"`
- **BlockPublicAcls**: The `PublicAccessBlockConfiguration` property that, when `true`, rejects any request that includes an ACL grant — must be `false` for CloudFront legacy logging
- **OwnershipControls**: The S3 bucket property that controls object ownership; `BucketOwnerPreferred` allows the bucket owner to take ownership of objects written via ACL grants
- **delivery.logs.amazonaws.com**: The AWS service principal used by CloudFront standard logging to deliver log files to S3

## Bug Details

### Bug Condition

The bug manifests when a user specifies this S3 bucket as the logging destination for a CloudFront distribution using standard (legacy) logging. The template unconditionally sets `BlockPublicAcls: true`, does not configure `OwnershipControls`, and does not include a bucket policy statement for `delivery.logs.amazonaws.com`. CloudFront standard logging requires all three of these to be configured.

**Formal Specification:**
```
FUNCTION isBugCondition(template_config)
  INPUT: template_config of type CloudFormationTemplate
  OUTPUT: boolean

  RETURN template_config.AllowLegacyCloudFrontLogs == "true"
         AND template_config.Bucket.PublicAccessBlockConfiguration.BlockPublicAcls == true
         AND template_config.Bucket.OwnershipControls IS NOT DEFINED
         AND template_config.BucketPolicy DOES NOT CONTAIN statement for "delivery.logs.amazonaws.com"
END FUNCTION
```

### Examples

- **Example 1**: User deploys template with default parameters, then references the bucket as a CloudFront logging destination → CloudFront deployment fails with "The S3 bucket that you specified for CloudFront logs does not enable ACL access"
- **Example 2**: User sets `AllowLegacyCloudFrontLogs: true` (after fix) → Bucket is created with `BlockPublicAcls: false`, `ObjectOwnership: BucketOwnerPreferred`, and CloudFront log delivery policy statement → CloudFront logging works
- **Example 3**: User deploys template with `AllowLegacyCloudFrontLogs: false` (default, after fix) → Bucket retains `BlockPublicAcls: true`, no ownership controls, no CloudFront policy statement → Identical to current behavior
- **Example 4 (Edge case)**: User omits `AllowLegacyCloudFrontLogs` entirely (after fix) → Parameter defaults to `false` → Existing deployments unaffected

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- S3 server access log delivery via `logging.s3.amazonaws.com` must continue to work via the existing `AllowS3LogDelivery` policy statement
- The `DenyNonSecureTransportAccess` policy statement must continue to deny non-HTTPS access
- Server-side encryption with AES256 (SSE-S3) must remain configured
- Lifecycle rule deleting logs after `LogExpirationInDays` must remain active
- `BlockPublicPolicy: true`, `IgnorePublicAcls: true`, and `RestrictPublicBuckets: true` must remain set regardless of the new parameter
- `DeletionPolicy: Retain` and `UpdateReplacePolicy: Retain` must remain on the bucket
- Bucket naming convention using Prefix, ProjectId, Region, AccountId, and optional S3BucketNameOrgPrefix must remain unchanged
- All existing outputs and exports must remain unchanged

**Scope:**
All deployments where `AllowLegacyCloudFrontLogs` is `false` (or not specified) should produce a template identical in behavior to the current template. The only changes when the parameter is `false` are:
- The new parameter exists (with default `false`)
- The new condition exists (evaluates to `false`)
- `BlockPublicAcls` is conditionally resolved to `true` (same effective value)

## Hypothesized Root Cause

Based on the bug description, the root cause is a missing feature rather than a code defect:

1. **Unconditional BlockPublicAcls**: The template hardcodes `BlockPublicAcls: true` with no conditional logic. CloudFront standard logging uses ACL grants (`bucket-owner-full-control`) to write log objects, which are rejected when `BlockPublicAcls` is `true`.

2. **Missing OwnershipControls**: The template does not set `OwnershipControls` at all. CloudFront standard logging requires `ObjectOwnership: BucketOwnerPreferred` so that the bucket owner takes ownership of objects written by CloudFront via ACL grants. Without this, even if ACLs were unblocked, the ownership model would prevent proper log delivery.

3. **Missing CloudFront Log Delivery Policy Statement**: The bucket policy only includes statements for S3 log delivery (`logging.s3.amazonaws.com`) and non-secure transport denial. There is no statement allowing `delivery.logs.amazonaws.com` to perform `s3:PutObject`, which is required by CloudFront standard logging.

4. **No Opt-In Mechanism**: There is no parameter or condition that allows users to enable CloudFront legacy logging support. The template was designed only for S3 server access logs.

## Correctness Properties

Property 1: Bug Condition - CloudFront Legacy Logging Enabled

_For any_ template deployment where `AllowLegacyCloudFrontLogs` is set to `"true"` (isBugCondition input), the fixed template SHALL produce a bucket with `BlockPublicAcls: false`, `OwnershipControls` with `ObjectOwnership: BucketOwnerPreferred`, and a bucket policy statement allowing `delivery.logs.amazonaws.com` to perform `s3:PutObject` with `s3:x-amz-acl` condition set to `bucket-owner-full-control`.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

Property 2: Preservation - Default Configuration Unchanged

_For any_ template deployment where `AllowLegacyCloudFrontLogs` is `"false"` or not specified (isBugCondition returns false), the fixed template SHALL produce a bucket with `BlockPublicAcls: true`, no `OwnershipControls`, and no CloudFront log delivery policy statement — identical in behavior to the original template.

**Validates: Requirements 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `templates/v2/storage/template-storage-s3-access-logs.yml`

**Specific Changes**:

1. **Version Increment**: Update the version comment from `v0.0.1/2025-05-10` to `v0.0.2/YYYY-MM-DD` (current date). Since PATCH > 0, this is a required auto-increment per the version control steering document.

2. **Add Parameter `AllowLegacyCloudFrontLogs`**: Add a new `String` parameter under a new "CloudFront Legacy Logging" subsection in the Parameters section:
   - Type: `String`
   - Description: Explains the purpose and effect of enabling legacy CloudFront logging
   - Default: `"false"`
   - AllowedValues: `["true", "false"]`

3. **Add Condition `EnableLegacyCloudFrontLogs`**: Add a new condition in the Conditions section:
   - `EnableLegacyCloudFrontLogs: !Equals [!Ref AllowLegacyCloudFrontLogs, "true"]`

4. **Conditional `BlockPublicAcls`**: Change the hardcoded `BlockPublicAcls: true` to a conditional expression:
   - `BlockPublicAcls: !If [EnableLegacyCloudFrontLogs, false, true]`

5. **Conditional `OwnershipControls`**: Add `OwnershipControls` to the Bucket resource, conditional on `EnableLegacyCloudFrontLogs`:
   - `OwnershipControls: !If [EnableLegacyCloudFrontLogs, {Rules: [{ObjectOwnership: BucketOwnerPreferred}]}, !Ref "AWS::NoValue"]`

6. **Conditional CloudFront Log Delivery Policy Statement**: Add a new statement to the `LoggingBucketPolicy` resource's `PolicyDocument.Statement` array, conditional on `EnableLegacyCloudFrontLogs`:
   - Sid: `"AllowCloudFrontLogDelivery"`
   - Effect: `Allow`
   - Principal: `{Service: delivery.logs.amazonaws.com}`
   - Action: `s3:PutObject`
   - Resource: `${Bucket.Arn}/*`
   - Condition: `StringEquals: {"s3:x-amz-acl": "bucket-owner-full-control"}`
   - Wrapped in `!If [EnableLegacyCloudFrontLogs, {...}, !Ref "AWS::NoValue"]`

7. **Update Metadata Parameter Groups**: Add `AllowLegacyCloudFrontLogs` to the Metadata `ParameterGroups`. Add it to the existing "Log Settings" group or create a new "CloudFront Legacy Logging" group.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior. Since this is a CloudFormation template (declarative infrastructure), testing focuses on template structure validation rather than runtime behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis.

**Test Plan**: Parse the unfixed template YAML and assert that the required CloudFront logging configurations are present. These tests will fail on the unfixed code, confirming the root cause.

**Test Cases**:
1. **BlockPublicAcls Test**: Assert that `BlockPublicAcls` can be set to `false` when CloudFront logging is enabled (will fail on unfixed code — always `true`)
2. **OwnershipControls Test**: Assert that `OwnershipControls` with `BucketOwnerPreferred` is present when CloudFront logging is enabled (will fail on unfixed code — not present)
3. **CloudFront Policy Statement Test**: Assert that a policy statement for `delivery.logs.amazonaws.com` exists when CloudFront logging is enabled (will fail on unfixed code — not present)
4. **Parameter Existence Test**: Assert that `AllowLegacyCloudFrontLogs` parameter exists (will fail on unfixed code — parameter missing)

**Expected Counterexamples**:
- `BlockPublicAcls` is unconditionally `true` with no conditional logic
- `OwnershipControls` property is entirely absent from the Bucket resource
- No policy statement references `delivery.logs.amazonaws.com`
- Possible causes: missing parameter, missing condition, hardcoded security configuration

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (CloudFront logging enabled), the fixed template produces the expected configuration.

**Pseudocode:**
```
FOR ALL template_config WHERE AllowLegacyCloudFrontLogs == "true" DO
  resolved := resolve_template(template_config)
  ASSERT resolved.Bucket.PublicAccessBlockConfiguration.BlockPublicAcls == false
  ASSERT resolved.Bucket.OwnershipControls.Rules[0].ObjectOwnership == "BucketOwnerPreferred"
  ASSERT resolved.BucketPolicy CONTAINS statement with Principal "delivery.logs.amazonaws.com"
  ASSERT resolved.BucketPolicy.CloudFrontStatement.Condition.StringEquals["s3:x-amz-acl"] == "bucket-owner-full-control"
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold (CloudFront logging disabled/default), the fixed template produces the same result as the original template.

**Pseudocode:**
```
FOR ALL template_config WHERE AllowLegacyCloudFrontLogs == "false" OR NOT SPECIFIED DO
  resolved_original := resolve_template_original(template_config)
  resolved_fixed := resolve_template_fixed(template_config)
  ASSERT resolved_fixed.Bucket.PublicAccessBlockConfiguration.BlockPublicAcls == true
  ASSERT resolved_fixed.Bucket.OwnershipControls IS NOT DEFINED
  ASSERT resolved_fixed.BucketPolicy DOES NOT CONTAIN statement for "delivery.logs.amazonaws.com"
  ASSERT resolved_fixed.Bucket.BucketEncryption == resolved_original.Bucket.BucketEncryption
  ASSERT resolved_fixed.Bucket.LifecycleConfiguration == resolved_original.Bucket.LifecycleConfiguration
  ASSERT resolved_fixed.BucketPolicy.DenyNonSecureTransport == resolved_original.BucketPolicy.DenyNonSecureTransport
  ASSERT resolved_fixed.BucketPolicy.AllowS3LogDelivery == resolved_original.BucketPolicy.AllowS3LogDelivery
END FOR
```

**Testing Approach**: Unit tests are the primary mechanism for this CloudFormation template since the input space is small and controlled (a single boolean-like parameter). Property-based tests are not critical here per project guidelines.

**Test Plan**: Parse the unfixed template to capture baseline behavior, then verify the fixed template preserves that behavior when `AllowLegacyCloudFrontLogs` is `false`.

**Test Cases**:
1. **S3 Log Delivery Preservation**: Verify the `AllowS3LogDelivery` policy statement remains unchanged in both enabled and disabled modes
2. **Non-Secure Transport Denial Preservation**: Verify the `DenyNonSecureTransportAccess` policy statement remains unchanged
3. **Encryption Preservation**: Verify AES256 encryption configuration remains unchanged
4. **Lifecycle Preservation**: Verify the `DeleteOldLogs` lifecycle rule remains unchanged
5. **Public Access Block Preservation**: Verify `BlockPublicPolicy`, `IgnorePublicAcls`, and `RestrictPublicBuckets` remain `true` in both modes
6. **Retention Policy Preservation**: Verify `DeletionPolicy: Retain` and `UpdateReplacePolicy: Retain` remain set
7. **Bucket Naming Preservation**: Verify bucket naming convention remains unchanged

### Unit Tests

- Test that `AllowLegacyCloudFrontLogs` parameter exists with correct type, default, and allowed values
- Test that `EnableLegacyCloudFrontLogs` condition exists and references the parameter correctly
- Test that `BlockPublicAcls` uses `!If` with the condition (resolves to `false` when enabled, `true` when disabled)
- Test that `OwnershipControls` is present when enabled and absent (`AWS::NoValue`) when disabled
- Test that CloudFront log delivery policy statement is present when enabled and absent when disabled
- Test that the CloudFront policy statement has correct principal, action, resource, and condition
- Test that the parameter appears in the Metadata parameter groups
- Test that the version is incremented to v0.0.2
- Test edge case: all other `PublicAccessBlockConfiguration` properties remain `true` when CloudFront logging is enabled

### Property-Based Tests

Per project testing guidelines, property-based tests are not critical for this template since the input space is small and controlled. Unit tests with concrete examples provide sufficient coverage. If implemented, minimal property-based tests could:
- Generate random combinations of parameter values and verify the condition resolves correctly
- Verify that non-CloudFront-related template sections are invariant across all parameter combinations

### Integration Tests

- Validate the fixed template passes `cfn-lint` with no errors
- Validate the template with both `AllowLegacyCloudFrontLogs: true` and `false` parameter values
- Verify the template structure is valid YAML and conforms to CloudFormation schema
