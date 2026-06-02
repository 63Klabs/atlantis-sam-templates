# S3 Artifacts Bucket Policy Fix - Bugfix Design

## Overview

The `s3-artifacts-bucket-policy.yml` module fails at stack creation time with "Invalid principal in policy" because the WhitelistedGet and WhitelistedPut statements use named `Principal.AWS` ARNs with wildcard patterns that are (a) reversed from the actual role naming convention and (b) require the roles to already exist. The fix converts these statements to use `Principal: "*"` with `aws:PrincipalArn` `ArnLike` conditions using corrected wildcard patterns that match the actual role suffix convention (`*-CodePipelineServiceRole`, `*-CodeBuildServiceRole`, `*-CloudFormationSvcRole`).

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug — named `Principal.AWS` ARNs with reversed wildcard patterns that don't match actual role names and require roles to exist at policy creation time
- **Property (P)**: The desired behavior — bucket policy deploys successfully and grants access to matching pipeline service roles regardless of whether they currently exist
- **Preservation**: The DenyNonSecureTransportAccess statement, condition gating, resource ARN scoping, and the same S3 actions (Get/Put) must remain unchanged
- **s3-artifacts-bucket-policy.yml**: The AWS::Include module snippet at `templates/v2/modules/account-wide/s3-artifacts-bucket-policy.yml` that defines the S3 bucket policy
- **RolePath**: IAM path parameter (e.g., `/` or `/app_role/`) used when creating roles; appears in role ARNs between `role` and the role name
- **Named Principal**: A `Principal.AWS` entry specifying an exact IAM ARN — S3 validates existence at policy creation time
- **Condition-based Principal**: Using `Principal: "*"` with a `Condition` block to match role ARNs via patterns — does not require roles to exist

## Bug Details

### Bug Condition

The bug manifests when the account-wide-infrastructure stack is created or updated with `EnableS3ArtifactsBucket: "true"`. The bucket policy uses `Principal.AWS` with wildcard ARN patterns where the role type is a **prefix** followed by a wildcard (e.g., `CodePipelineServiceRole-*`), but actual role names use the role type as a **suffix** (e.g., `acme-Worker-myapp-test-CodePipelineServiceRole`). Additionally, S3 validates named principals exist at creation time, so even correctly-patterned named principals would fail when no matching roles exist yet.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type BucketPolicyDocument
  OUTPUT: boolean

  RETURN input.hasStatement(sid="WhitelistedGet" OR sid="WhitelistedPut")
         AND statement.Principal.AWS contains named ARN patterns
         AND (
           arnPattern ends with "ServiceRole-*" (reversed wildcard)
           OR no IAM roles matching the pattern currently exist in the account
         )
END FUNCTION
```

### Examples

- **Reversed pattern**: `arn:aws:iam::123456789012:role/CodePipelineServiceRole-*` does NOT match actual role `arn:aws:iam::123456789012:role/acme-Worker-myapp-test-CodePipelineServiceRole` — the wildcard is on the wrong end
- **Non-existent role**: Even if the pattern were `arn:aws:iam::123456789012:role/*-CodePipelineServiceRole`, using it as a named `Principal.AWS` would fail because S3 validates the principal exists at policy creation time
- **CloudFormation role**: `arn:aws:iam::123456789012:role/CloudFormationSvcRole-*` doesn't match `arn:aws:iam::123456789012:role/acme-Worker-myapp-test-CloudFormationSvcRole`
- **With RolePath**: `arn:aws:iam::123456789012:role/app_role/CodeBuildServiceRole-*` doesn't match `arn:aws:iam::123456789012:role/app_role/acme-Worker-myapp-test-CodeBuildServiceRole`

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- The DenyNonSecureTransportAccess statement must remain exactly as-is (Principal: "*", Effect: Deny, Action: "s3:*", Condition: aws:SecureTransport = false)
- The `Condition: EnableS3ArtifactsBucket` on the resource must remain
- Resource references must continue to use `Fn::GetAtt: [S3ArtifactsBucketRegional, Arn]` for the bucket and bucket/* ARNs
- WhitelistedGet actions must remain: s3:GetObject, s3:GetObjectVersion, s3:GetBucketVersioning
- WhitelistedPut actions must remain: s3:PutObject
- The overall policy structure (Version, Id: SSEAndSSLPolicy, three statements) must remain

**Scope:**
All inputs that do NOT involve the Principal/Condition mechanism of WhitelistedGet and WhitelistedPut should be completely unaffected by this fix. This includes:
- The DenyNonSecureTransportAccess statement (unchanged)
- The bucket resource reference (S3ArtifactsBucketRegional)
- The condition gating (EnableS3ArtifactsBucket)
- The S3 actions allowed in each statement
- The resource ARN scoping in each statement

## Hypothesized Root Cause

Based on the bug description, there are two compounding issues:

1. **Reversed Wildcard Patterns**: The current patterns place the role type as a prefix with a trailing wildcard (`CodePipelineServiceRole-*`), but the pipeline template creates roles named `${Prefix}-Worker-${ProjectId}-${StageId}-CodePipelineServiceRole` where the role type is the suffix. The correct pattern should be `*-CodePipelineServiceRole`.

2. **Named Principal Validation**: S3 bucket policies validate that named `Principal.AWS` ARNs resolve to existing IAM entities at policy creation time. Since the account-wide infrastructure deploys before any project pipelines, no matching roles exist yet — causing immediate failure regardless of pattern correctness.

3. **Fix Mechanism**: AWS supports `Principal: "*"` with `Condition` blocks using `aws:PrincipalArn` and `ArnLike` operator. This allows wildcard matching without requiring the roles to exist, solving both the pattern and existence issues simultaneously.

## Correctness Properties

Property 1: Bug Condition - Policy Deploys Without Principal Validation Error

_For any_ bucket policy document where the WhitelistedGet and WhitelistedPut statements use `Principal: "*"` with `aws:PrincipalArn` `ArnLike` conditions, the policy SHALL be accepted by S3 without "Invalid principal in policy" errors, regardless of whether matching IAM roles currently exist.

**Validates: Requirements 2.1**

Property 2: Bug Condition - Wildcard Patterns Match Role Suffix Convention

_For any_ role name following the convention `${Prefix}-Worker-${ProjectId}-${StageId}-{RoleType}` where RoleType is one of CodePipelineServiceRole, CodeBuildServiceRole, or CloudFormationSvcRole, the ArnLike condition patterns `arn:aws:iam::${AccountId}:role${RolePath}*-{RoleType}` SHALL match that role's ARN.

**Validates: Requirements 2.2, 2.3, 2.4**

Property 3: Preservation - DenyNonSecureTransport Statement Unchanged

_For any_ fix applied to the bucket policy, the DenyNonSecureTransportAccess statement SHALL remain identical to the original (Principal: "*", Effect: Deny, Action: "s3:*", Condition: Bool aws:SecureTransport false), preserving the security posture.

**Validates: Requirements 3.1**

Property 4: Preservation - Actions and Resource Scoping Unchanged

_For any_ fix applied to the bucket policy, the WhitelistedGet and WhitelistedPut statements SHALL continue to allow the same S3 actions (GetObject, GetObjectVersion, GetBucketVersioning for Get; PutObject for Put) scoped to the same resources (S3ArtifactsBucketRegional ARN and ARN/*).

**Validates: Requirements 3.2, 3.3, 3.4**

Property 5: Preservation - Condition Gating Unchanged

_For any_ fix applied to the bucket policy, the resource-level `Condition: EnableS3ArtifactsBucket` SHALL remain, ensuring the policy is not created when the feature is disabled.

**Validates: Requirements 3.5**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `templates/v2/modules/account-wide/s3-artifacts-bucket-policy.yml`

**Statements**: `WhitelistedGet` and `WhitelistedPut`

**Specific Changes**:

1. **Replace named Principal with wildcard Principal**: Change `Principal.AWS` (list of ARNs) to `Principal: "*"` in both WhitelistedGet and WhitelistedPut statements.

2. **Add Condition block with ArnLike**: Add a `Condition` block to each statement using the `ArnLike` operator on `aws:PrincipalArn` with the corrected patterns.

3. **Fix wildcard placement in patterns**: Change patterns from `{RoleType}-*` (prefix) to `*-{RoleType}` (suffix) to match the actual naming convention where the role type is a suffix.

4. **WhitelistedGet condition patterns** (CodePipeline, CodeBuild, and CloudFormation roles):
   ```yaml
   Condition:
     ArnLike:
       "aws:PrincipalArn":
         - !Sub "arn:aws:iam::${AWS::AccountId}:role${RolePath}*-CodePipelineServiceRole"
         - !Sub "arn:aws:iam::${AWS::AccountId}:role${RolePath}*-CodeBuildServiceRole"
         - !Sub "arn:aws:iam::${AWS::AccountId}:role${RolePath}*-CloudFormationSvcRole"
   ```

5. **WhitelistedPut condition patterns** (CodePipeline and CodeBuild roles only — CloudFormation role does not need Put):
   ```yaml
   Condition:
     ArnLike:
       "aws:PrincipalArn":
         - !Sub "arn:aws:iam::${AWS::AccountId}:role${RolePath}*-CodePipelineServiceRole"
         - !Sub "arn:aws:iam::${AWS::AccountId}:role${RolePath}*-CodeBuildServiceRole"
   ```

6. **Preserve all other aspects**: DenyNonSecureTransportAccess statement, resource-level Condition, bucket references, actions, and resource ARN scoping remain unchanged.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior. Per project testing guidelines, focus is on fast-running unit tests.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis.

**Test Plan**: Write unit tests that parse the unfixed YAML template and verify:
1. The Principal structure uses named ARNs (which will fail S3 validation)
2. The wildcard patterns are reversed (role type as prefix instead of suffix)

**Test Cases**:
1. **Named Principal Detection**: Parse WhitelistedGet/WhitelistedPut and assert Principal.AWS is a list of ARNs (will demonstrate the named-principal problem)
2. **Reversed Pattern Detection**: Assert that current patterns end with `-*` suffix after the role type (will demonstrate the reversed wildcard)
3. **Pattern Mismatch Test**: Given a real role name like `acme-Worker-myapp-test-CodePipelineServiceRole`, assert that the current pattern `CodePipelineServiceRole-*` does NOT match it via fnmatch/glob

**Expected Counterexamples**:
- Current patterns use named Principal.AWS (not condition-based)
- Current patterns have role type as prefix: `CodePipelineServiceRole-*` instead of `*-CodePipelineServiceRole`

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL statement IN [WhitelistedGet, WhitelistedPut] DO
  ASSERT statement.Principal == "*"
  ASSERT statement.Condition.ArnLike["aws:PrincipalArn"] exists
  FOR ALL pattern IN statement.Condition.ArnLike["aws:PrincipalArn"] DO
    ASSERT pattern ends with "-CodePipelineServiceRole"
           OR pattern ends with "-CodeBuildServiceRole"
           OR pattern ends with "-CloudFormationSvcRole"
    ASSERT pattern contains "*-" before the role type suffix
  END FOR
END FOR

FOR ALL roleName IN generatedRoleNames DO
  ASSERT fnmatch(roleName, correctedPattern) == True
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL statement IN fixedPolicy.Statements DO
  IF statement.Sid == "DenyNonSecureTransportAccess" THEN
    ASSERT statement == originalPolicy.getStatement("DenyNonSecureTransportAccess")
  END IF
END FOR

ASSERT fixedPolicy.resource_condition == "EnableS3ArtifactsBucket"
ASSERT fixedPolicy.bucket_ref == originalPolicy.bucket_ref
ASSERT fixedPolicy.WhitelistedGet.actions == originalPolicy.WhitelistedGet.actions
ASSERT fixedPolicy.WhitelistedPut.actions == originalPolicy.WhitelistedPut.actions
ASSERT fixedPolicy.WhitelistedGet.resources == originalPolicy.WhitelistedGet.resources
ASSERT fixedPolicy.WhitelistedPut.resources == originalPolicy.WhitelistedPut.resources
```

**Testing Approach**: Unit tests are recommended per project testing guidelines. The template is a single YAML file with a known, fixed structure — exhaustive unit tests with concrete assertions provide sufficient coverage.

### Unit Tests

- Parse unfixed template and verify named Principal.AWS patterns are reversed (exploration)
- Parse fixed template and verify Principal is "*" with Condition block (fix verification)
- Verify ArnLike patterns use correct suffix convention (`*-{RoleType}`)
- Verify DenyNonSecureTransportAccess statement is unchanged between original and fixed
- Verify WhitelistedGet actions are unchanged
- Verify WhitelistedPut actions are unchanged
- Verify resource ARN references are unchanged (Fn::GetAtt S3ArtifactsBucketRegional)
- Verify resource-level Condition: EnableS3ArtifactsBucket is preserved
- Test pattern matching: `*-CodePipelineServiceRole` matches `acme-Worker-myapp-test-CodePipelineServiceRole`
- Test pattern matching: `*-CodeBuildServiceRole` matches `acme-Worker-myapp-test-CodeBuildServiceRole`
- Test pattern matching: `*-CloudFormationSvcRole` matches `acme-Worker-myapp-test-CloudFormationSvcRole`
- Test pattern non-matching: patterns do NOT match unrelated role names

### Property-Based Tests

Per project testing guidelines, property-based tests are not critical for this repository. If implemented, keep iterations minimal (10-20):
- Generate random role names following `${Prefix}-Worker-${ProjectId}-${StageId}-{RoleType}` convention and verify pattern match
- Generate random non-pipeline role names and verify patterns do NOT match

### Integration Tests

- Validate the fixed YAML template is well-formed and parseable
- Validate the fixed template integrates correctly with the parent account-wide-infrastructure.yml template structure (parameters referenced exist, conditions referenced exist)
