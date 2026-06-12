# Design: Fix permissions gaps in network-cloudfront-mgmt-policy.yml

## Overview

Add missing IAM policy statements and fix an S3 resource pattern in `network-cloudfront-mgmt-policy.yml` to resolve deployment failures for the `template-network-route53-cloudfront-s3-apigw.yml` template. Three gaps are addressed: CloudFront Origin Request Policy read permissions, API Gateway `/apis` resource access, and an S3 log bucket ARN pattern mismatch.

## Approach

Each gap is fixed by adding or modifying a single IAM policy statement in the existing `network-cloudfront-mgmt-policy.yml` managed policy. The fixes follow the established patterns in the template (long-form intrinsic functions, Sid naming, resource scoping).

### Gap 1: Add CloudFront Origin Request Policy Read

A new statement grants read-only access to CloudFront Origin Request Policies. This is needed for CloudFormation to validate `OriginRequestPolicyId` references during distribution creation/updates.

```yaml
- Sid: CloudFrontOriginRequestPolicyRead
  Effect: Allow
  Action:
    - cloudfront:GetOriginRequestPolicy
    - cloudfront:GetOriginRequestPolicyConfig
    - cloudfront:ListOriginRequestPolicies
  Resource: "*"
```

**Placement:** Immediately after `CloudFrontCachePolicyCRUD` — this groups all CloudFront policy-type permissions together (cache policies, then origin request policies, then functions).

### Gap 2: Add API Gateway /apis Read

A new statement grants read-only (`GET`) access to the `/apis` and `/apis/*` resources. This is needed for CloudFormation to validate API references when creating `AWS::ApiGatewayV2::ApiMapping`.

```yaml
- Sid: ApiGatewayV2ReadApis
  Effect: Allow
  Action:
    - apigateway:GET
  Resource:
    - Fn::Sub: "arn:aws:apigateway:${AWS::Region}::/apis"
    - Fn::Sub: "arn:aws:apigateway:${AWS::Region}::/apis/*"
```

**Placement:** Immediately after `ApiGatewayV2DomainCRUD` — this keeps all API Gateway permissions grouped together. Only `GET` is needed since the role is reading/validating the API, not creating or modifying it.

### Gap 3: Fix S3BucketReadForLogging Pattern

The current pattern uses `${Prefix}-${AWS::AccountId}-${AWS::Region}` as the non-org-prefix branch, which produces `acme-123456789012-us-east-1-*`. This does not match actual log bucket names that include ProjectId (e.g. `acme-myproj-access-logs-123456789012-us-east-1-an`).

The fix changes the non-org-prefix branch from `${Prefix}-${AWS::AccountId}-${AWS::Region}` to just `${Prefix}`, producing the broader pattern `acme-*` which matches all prefix-scoped buckets including those with ProjectId.

**Before:**
```yaml
- Fn::Sub:
  - "arn:aws:s3:::${BucketPrefix}-*"
  - BucketPrefix:
      Fn::If:
        - UseS3BucketNameOrgPrefix
        - Fn::Sub: "${S3BucketNameOrgPrefix}-${Prefix}"
        - Fn::Sub: "${Prefix}-${AWS::AccountId}-${AWS::Region}"
```

**After:**
```yaml
- Fn::Sub:
  - "arn:aws:s3:::${BucketPrefix}-*"
  - BucketPrefix:
      Fn::If:
        - UseS3BucketNameOrgPrefix
        - Fn::Sub: "${S3BucketNameOrgPrefix}-${Prefix}"
        - Fn::Sub: "${Prefix}"
```

## Architecture

This is a minimal IAM policy modification to one existing CloudFormation module template. No new resources, services, or architectural changes are introduced.

```
┌─────────────────────────────────────────────────────────────┐
│  CloudFormation Service (assumes network mgmt role)         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Existing Statements (unchanged):                           │
│    ManageCloudFormationStacksByResourcePrefix                │
│    AllowTransformOperations                                 │
│    CloudFrontDistributionCRUD                               │
│    CloudFrontOACCRUD                                        │
│    CloudFrontCachePolicyCRUD                                │
│    CloudFrontFunctionRead                                   │
│    ApiGatewayV2DomainCRUD                                   │
│    AcmCertificateRead                                       │
│                                                             │
│  New Statements:                                            │
│    CloudFrontOriginRequestPolicyRead  ← NEW (after Cache)   │
│    ApiGatewayV2ReadApis               ← NEW (after Domain)  │
│                                                             │
│  Modified Statement:                                        │
│    S3BucketReadForLogging             ← FIX (pattern)       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### Affected Components

| Component | File | Role |
|-----------|------|------|
| Network CloudFront Management Policy | `templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml` | Managed policy for CloudFormation service role when deploying network/CloudFront stacks |

### Interfaces

No new interfaces are introduced. The changes add permissions that CloudFormation already attempts to use (and currently fails):

1. CloudFormation calls `GetOriginRequestPolicy` to validate `OriginRequestPolicyId` → `CloudFrontOriginRequestPolicyRead` permits this
2. CloudFormation calls `GET /apis/{apiId}` to validate API reference for ApiMapping → `ApiGatewayV2ReadApis` permits this
3. CloudFormation calls `GetBucketLocation`/`ListBucket` on the log bucket → `S3BucketReadForLogging` (fixed pattern) permits this

## Data Models

No data models are affected. This change modifies IAM policy documents only.

## Affected Files

| File | Change |
|------|--------|
| `templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml` | Add `CloudFrontOriginRequestPolicyRead` statement, add `ApiGatewayV2ReadApis` statement, fix `S3BucketReadForLogging` resource pattern |

## Design Decisions

1. **CloudFront Origin Request Policy uses `Resource: "*"`**: CloudFront is a global service and Origin Request Policies (both custom and AWS-managed) do not have per-resource ARNs that can be scoped. This matches the existing pattern for `CloudFrontCachePolicyCRUD` and `CloudFrontOACCRUD`.

2. **API Gateway read-only (`GET` only)**: The role only needs to validate the API exists for ApiMapping creation. It does not need to create or modify the API itself (that's handled by a different stack/role). This follows least privilege.

3. **S3 pattern uses `${Prefix}-*` instead of `${Prefix}-${AccountId}-${Region}-*`**: The original pattern was too specific and did not account for ProjectId in bucket names. Using `${Prefix}-*` matches all bucket names under the prefix regardless of internal structure. This is acceptable because the S3 actions are read-only (`GetBucketLocation`, `ListBucket`) and the bucket must already exist.

4. **Org prefix branch unchanged**: The `UseS3BucketNameOrgPrefix` branch already uses `${S3BucketNameOrgPrefix}-${Prefix}` which is sufficiently broad. Only the non-org-prefix branch needs fixing.

5. **Statement ordering**: New statements are placed adjacent to related existing statements to maintain logical grouping within the policy document.

## Correctness Properties

Property 1: Origin Request Policy read access

_For any_ deployment using `OriginRequestPolicyId` in the network template, the service role SHALL have `cloudfront:GetOriginRequestPolicy`, `cloudfront:GetOriginRequestPolicyConfig`, and `cloudfront:ListOriginRequestPolicies` permissions.

**Validates: Requirements 1.1**

Property 2: API Gateway /apis read access

_For any_ deployment creating `AWS::ApiGatewayV2::ApiMapping`, the service role SHALL have `apigateway:GET` on both `arn:aws:apigateway:${Region}::/apis` and `arn:aws:apigateway:${Region}::/apis/*`.

**Validates: Requirements 2.1**

Property 3: S3 log bucket pattern matches all prefix-scoped buckets

_For any_ S3 bucket name starting with `${Prefix}-` (non-org-prefix) or `${S3BucketNameOrgPrefix}-${Prefix}-` (org-prefix), the `S3BucketReadForLogging` resource ARN SHALL match that bucket.

**Validates: Requirements 3.1**

Property 4: Existing statements unchanged

_For any_ existing statement in `network-cloudfront-mgmt-policy.yml` other than `S3BucketReadForLogging`, the statement SHALL remain unmodified.

**Validates: Requirements 1.1, 2.1, 3.1**

Property 5: Template validity

The modified template SHALL pass cfn-lint validation with no errors.

**Validates: Requirements 4.1**

## Error Handling

This change does not introduce runtime error handling logic. The fix is purely declarative (IAM policy). Error scenarios:

| Scenario | Behavior |
|----------|----------|
| Origin Request Policy statement omitted | Unit test verifies statement exists with correct Sid and actions |
| API Gateway statement uses wrong actions | Unit test verifies only `apigateway:GET` is granted |
| S3 pattern still uses AccountId/Region | Unit test verifies the simplified pattern |
| Template YAML syntax error | cfn-lint validation catches malformed YAML |

## Security Considerations

- `CloudFrontOriginRequestPolicyRead` grants read-only access to Origin Request Policies. No ability to create, modify, or delete policies.
- `ApiGatewayV2ReadApis` grants only `GET` (read) access to APIs. No ability to create, modify, or delete APIs.
- The S3 pattern change broadens the match from `${Prefix}-${AccountId}-${Region}-*` to `${Prefix}-*`, but the actions remain read-only (`GetBucketLocation`, `ListBucket`). This is acceptable because:
  - The role is scoped to a specific prefix
  - Only read actions are permitted on the broader pattern
  - The broader pattern is necessary to match actual bucket names
- The principle of least privilege is maintained: only minimum actions needed on minimum resources.

## Testing Strategy

- **cfn-lint validation**: Run cfn-lint on the modified template to confirm valid YAML and CloudFormation structure.
- **Unit tests**: Verify:
  - `CloudFrontOriginRequestPolicyRead` statement exists with correct Sid, actions, and `Resource: "*"`
  - `ApiGatewayV2ReadApis` statement exists with correct Sid, action (`apigateway:GET`), and correct resource ARNs
  - `S3BucketReadForLogging` resource pattern uses `Fn::If` with `UseS3BucketNameOrgPrefix` and the non-org branch resolves to `${Prefix}` (not `${Prefix}-${AccountId}-${Region}`)
  - Existing statements remain unchanged

## Requirement Traceability

| Requirement | Design Element |
|-------------|----------------|
| 1.1 | `CloudFrontOriginRequestPolicyRead` statement added after `CloudFrontCachePolicyCRUD` |
| 2.1 | `ApiGatewayV2ReadApis` statement added after `ApiGatewayV2DomainCRUD` |
| 3.1 | `S3BucketReadForLogging` resource pattern fixed to use `${Prefix}` instead of `${Prefix}-${AccountId}-${Region}` |
| 4.1 | cfn-lint validation task |
| 4.2 | Unit tests for statement presence, actions, resources, and S3 pattern |
