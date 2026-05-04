# S3 OAC Domain Format Bugfix Design

## Overview

The `OriginBucketDomainForCloudFront` output in `template-storage-s3-oac-for-cloudfront.yml` uses `!GetAtt OriginBucketRegional.DomainName`, which returns the old global S3 domain format (`<bucketname>.s3.amazonaws.com`). AWS now requires the regional format (`<bucketname>.s3.<region>.amazonaws.com`) for CloudFront distributions using Origin Access Control (OAC). The global format causes a 307 redirect from CloudFront to the S3 bucket domain instead of serving content.

The fix replaces the `!GetAtt` intrinsic with a `!Sub` expression that constructs the regional domain explicitly. This is a non-breaking PATCH change (v0.1.1 → v0.1.2) since it corrects the output value format without changing parameters, resources, or other outputs. Additional tasks include updating the template version/date, adding a changelog entry, and updating template documentation.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug — when the `OriginBucketDomainForCloudFront` output value uses the global S3 domain format (`<bucketname>.s3.amazonaws.com`) instead of the regional format
- **Property (P)**: The desired behavior — the output SHALL produce the regional S3 domain format `https://<bucketname>.s3.<region>.amazonaws.com`
- **Preservation**: All other template resources, parameters, conditions, and outputs must remain unchanged by the fix
- **OriginBucketRegional**: The `AWS::S3::Bucket` resource in the template that serves as the CloudFront origin
- **OAC (Origin Access Control)**: The AWS mechanism for granting CloudFront access to S3 buckets, which requires regional S3 endpoints
- **307 Redirect**: The HTTP redirect that S3 returns when a request hits the global endpoint for a bucket in a different region

## Bug Details

### Bug Condition

The bug manifests when the `OriginBucketDomainForCloudFront` output value is used as the origin domain for a CloudFront distribution configured with OAC. The `!GetAtt OriginBucketRegional.DomainName` intrinsic returns the global S3 domain format, which causes S3 to issue a 307 redirect to the regional endpoint instead of serving the content directly.

**Formal Specification:**
```
FUNCTION isBugCondition(template)
  INPUT: template of type CloudFormationTemplate
  OUTPUT: boolean

  output := template.Outputs["OriginBucketDomainForCloudFront"]
  RETURN output.Value uses "!GetAtt OriginBucketRegional.DomainName"
         AND output.Value does NOT contain AWS::Region
         AND output.Value produces format "<bucketname>.s3.amazonaws.com"
END FUNCTION
```

### Examples

- **Example 1**: Bucket `acme-webapp-us-east-1-123456789012` in `us-east-1` — output produces `acme-webapp-us-east-1-123456789012.s3.amazonaws.com` (global format, causes 307 redirect) instead of `https://acme-webapp-us-east-1-123456789012.s3.us-east-1.amazonaws.com` (regional format, works correctly)
- **Example 2**: Bucket `myorg-myapp-eu-west-1-987654321098` in `eu-west-1` — output produces `myorg-myapp-eu-west-1-987654321098.s3.amazonaws.com` (global format) instead of `https://myorg-myapp-eu-west-1-987654321098.s3.eu-west-1.amazonaws.com` (regional format)
- **Example 3**: Any bucket in any region — the `!GetAtt DomainName` always returns the global format, so the bug affects all deployments of this template regardless of region

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- S3 bucket (`OriginBucketRegional`) creation with the same naming convention, encryption (AES256), public access block, and logging configuration
- S3 bucket policy (`BucketPolicy`) granting CloudFront read-only access and CodeBuild read/write/delete access with the same conditions
- `BucketName` output returning the bucket name via `!Ref OriginBucketRegional`
- `AllowedCloudFrontAndCodeBuild` output returning `${Prefix}-${ProjectId}`
- Lambda permission (`S3InvokeLambdaPermission`) and S3 event notification configuration when `InvalidatorArn` is provided
- `LoggingBucketName`, `InvalidatorArn`, and `InvalidationEventsEnabled` outputs unchanged
- All parameters, conditions, and metadata unchanged

**Scope:**
All template content other than the `OriginBucketDomainForCloudFront` output `Value` field and the version comment in the header should be completely unaffected by this fix.

## Hypothesized Root Cause

Based on the bug description, the root cause is:

1. **Incorrect Intrinsic Function Usage**: The template uses `!GetAtt OriginBucketRegional.DomainName` which returns the legacy global S3 domain format (`<bucketname>.s3.amazonaws.com`). AWS changed S3 behavior so that requests to the global endpoint for buckets in regions other than `us-east-1` receive a 307 redirect to the regional endpoint. CloudFront does not follow this redirect when using OAC, resulting in failed content delivery.

2. **Missing Region in Domain**: The fix requires explicitly constructing the regional domain using `!Sub` with the `AWS::Region` pseudo-parameter to produce the format `https://<bucketname>.s3.<region>.amazonaws.com`, which CloudFront can use directly without encountering a redirect.

## Correctness Properties

Property 1: Bug Condition - Regional Domain Format in Output

_For any_ template where the `OriginBucketDomainForCloudFront` output exists, the output value SHALL use `!Sub` with the `AWS::Region` pseudo-parameter to produce the regional S3 domain format `https://<bucketname>.s3.<region>.amazonaws.com`, and SHALL NOT use `!GetAtt OriginBucketRegional.DomainName`.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation - All Other Template Content Unchanged

_For any_ template content outside the `OriginBucketDomainForCloudFront` output `Value` field and the version/date comment, the fixed template SHALL be identical to the original template, preserving all parameters, conditions, resources, bucket policies, other outputs, and metadata.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `templates/v2/storage/template-storage-s3-oac-for-cloudfront.yml`

**Specific Changes**:

1. **Version Increment**: Update the version comment from `v0.1.1/2026-03-29` to `v0.1.2/<current-date>` (PATCH increment for non-breaking bug fix, per template version control guidelines)

2. **Fix Output Value**: Replace the `OriginBucketDomainForCloudFront` output value:
   - **Before**: `Value: !GetAtt OriginBucketRegional.DomainName`
   - **After**: `Value: !Sub "https://${OriginBucketRegional}.s3.${AWS::Region}.amazonaws.com"`

3. **Update Output Description** (optional): Consider clarifying the description to mention the regional domain format

**File**: `CHANGELOG.md`

4. **Add Changelog Entry**: Add a `### Fixed` entry under the `v0.0.35 (unreleased)` section referencing the spec and GitHub issue #3

**File**: `docs/templates/v2/storage/template-storage-s3-oac-for-cloudfront-README.md`

5. **Update Template Documentation**: Update the version number and the `OriginBucketDomainForCloudFront` output description to reflect the regional domain format

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior. Per project testing guidelines, unit tests are prioritized over property-based tests.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis.

**Test Plan**: Parse the UNFIXED template YAML and inspect the `OriginBucketDomainForCloudFront` output value. Verify that it uses `!GetAtt OriginBucketRegional.DomainName` (the buggy intrinsic) and does not contain `AWS::Region`.

**Test Cases**:
1. **Output Value Check**: Parse the template and verify the output uses `!GetAtt` with `DomainName` attribute (will confirm bug on unfixed code)
2. **Region Absence Check**: Verify the output value does not reference `AWS::Region` (will confirm bug on unfixed code)
3. **Domain Format Check**: Verify the output would produce the global format pattern (will confirm bug on unfixed code)

**Expected Counterexamples**:
- The output value is `!GetAtt OriginBucketRegional.DomainName` which produces the global domain format
- The `AWS::Region` pseudo-parameter is not used in the output value construction

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL template WHERE isBugCondition(template) DO
  result := parseFixedTemplate(template)
  output := result.Outputs["OriginBucketDomainForCloudFront"]
  ASSERT output.Value uses "!Sub"
  ASSERT output.Value contains "AWS::Region"
  ASSERT output.Value matches pattern "https://${OriginBucketRegional}.s3.${AWS::Region}.amazonaws.com"
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL section IN template WHERE section != OriginBucketDomainForCloudFront.Value
                              AND section != versionComment DO
  ASSERT originalTemplate[section] = fixedTemplate[section]
END FOR
```

**Testing Approach**: Unit tests comparing the fixed template structure against the original for all sections except the changed output value and version comment. This is sufficient because the template is a single known file with a deterministic structure.

**Test Cases**:
1. **Parameter Preservation**: Verify all parameters remain identical between original and fixed templates
2. **Condition Preservation**: Verify all conditions remain identical
3. **Resource Preservation**: Verify all resources (OriginBucketRegional, BucketPolicy, S3InvokeLambdaPermission) remain identical
4. **Other Output Preservation**: Verify BucketName, AllowedCloudFrontAndCodeBuild, LoggingBucketName, InvalidatorArn, and InvalidationEventsEnabled outputs remain identical

### Unit Tests

- Parse fixed template YAML and verify `OriginBucketDomainForCloudFront` output uses `!Sub` with regional domain pattern
- Verify the `!Sub` expression contains `${OriginBucketRegional}` for the bucket name
- Verify the `!Sub` expression contains `${AWS::Region}` for the region
- Verify the `!Sub` expression produces the `https://` prefixed regional format
- Verify all other outputs are unchanged
- Verify all resources are unchanged
- Verify all parameters are unchanged
- Verify template version is incremented to v0.1.2

### Property-Based Tests

Per project testing guidelines, property-based tests are minimized. The template is a single known file, so unit tests with concrete examples provide sufficient coverage. No property-based tests are planned for this fix.

### Integration Tests

- Validate the fixed template passes `cfn-lint` validation (existing CI/CD integration)
- Verify the template can be parsed as valid YAML after the fix
