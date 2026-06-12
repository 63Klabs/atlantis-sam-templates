# Implementation Plan

## Overview

Fix three permissions gaps in `network-cloudfront-mgmt-policy.yml`: add CloudFront Origin Request Policy read permissions, add API Gateway `/apis` read access for ApiMapping validation, and fix the `S3BucketReadForLogging` resource pattern to match actual bucket names that include ProjectId.

## Tasks

- [x] 1. Add CloudFront Origin Request Policy read statement
  - [x] 1.1 Add a `CloudFrontOriginRequestPolicyRead` statement immediately after `CloudFrontCachePolicyCRUD` in `templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml` with actions `cloudfront:GetOriginRequestPolicy`, `cloudfront:GetOriginRequestPolicyConfig`, `cloudfront:ListOriginRequestPolicies` and `Resource: "*"`

- [x] 2. Add API Gateway /apis read statement
  - [x] 2.1 Add an `ApiGatewayV2ReadApis` statement immediately after `ApiGatewayV2DomainCRUD` in `templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml` with action `apigateway:GET` and resources `Fn::Sub: "arn:aws:apigateway:${AWS::Region}::/apis"` and `Fn::Sub: "arn:aws:apigateway:${AWS::Region}::/apis/*"`

- [x] 3. Fix S3BucketReadForLogging resource pattern
  - [x] 3.1 In the `S3BucketReadForLogging` statement in `templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml`, change the non-org-prefix branch from `Fn::Sub: "${Prefix}-${AWS::AccountId}-${AWS::Region}"` to `Fn::Sub: "${Prefix}"` so the pattern resolves to `${Prefix}-*` matching all prefix-scoped buckets including those with ProjectId

- [x] 4. Validate template with cfn-lint
  - [x] 4.1 Run cfn-lint on `templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml` and verify no errors

- [x] 5. Unit tests for fix verification
  - [x] 5.1 Write unit test: `CloudFrontOriginRequestPolicyRead` statement exists with correct Sid, all three actions, and `Resource: "*"`
  - [x] 5.2 Write unit test: `ApiGatewayV2ReadApis` statement exists with correct Sid, action `apigateway:GET`, and both `/apis` and `/apis/*` resource ARNs
  - [x] 5.3 Write unit test: `S3BucketReadForLogging` resource pattern uses `Fn::If` with `UseS3BucketNameOrgPrefix` and the non-org-prefix branch resolves to `${Prefix}` (not `${Prefix}-${AWS::AccountId}-${AWS::Region}`)
  - [x] 5.4 Write unit test: existing statements (`CloudFrontDistributionCRUD`, `CloudFrontOACCRUD`, `CloudFrontCachePolicyCRUD`, `ApiGatewayV2DomainCRUD`) remain unchanged

- [x] 6. Update CHANGELOG.md
  - [x] 6.1 Add entry under `v0.0.38 (unreleased)` in the `Fixed` category documenting the three fixes for the network CloudFront management policy, referencing spec and issue #8

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1", "3.1"] },
    { "id": 1, "tasks": ["4.1"] },
    { "id": 2, "tasks": ["5.1", "5.2", "5.3", "5.4", "6.1"] }
  ]
}
```

## Notes

- Tasks 1, 2, and 3 are independent and can be done in parallel (all modify different sections of the same file)
- Task 4 (linting) depends on all three fixes being complete
- Task 5 (unit tests) depends on linting to confirm valid YAML structure
- Task 6 (changelog) can be done after the template fixes are validated
- All new statements must use long-form intrinsic functions (no YAML shorthand) per the template header comments
- The `CloudFrontOriginRequestPolicyRead` statement should be placed between `CloudFrontCachePolicyCRUD` and `CloudFrontFunctionRead` to group CloudFront policy-type permissions together
- The `ApiGatewayV2ReadApis` statement should be placed between `ApiGatewayV2DomainCRUD` and `S3BucketReadForLogging` to keep API Gateway permissions grouped
