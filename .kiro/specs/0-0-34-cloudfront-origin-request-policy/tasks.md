# Implementation Plan: CloudFront Origin Request Policy

## Overview

Add the AWS managed Origin Request Policy "AllViewerExceptHostHeader" (ID: `b689b0a8-53d0-40ab-baf2-68738e2966ac`) to API Gateway cache behaviors in the network template. This replaces the custom header forwarding approach in the cache policy with the modern origin request policy approach, deprecates the `HeadersToForwardToApi` parameter, and removes the `HasHeadersToForwardToApi` condition.

## Tasks

- [x] 1. Increment template version and update date
  - Update the version comment in `templates/v2/network/template-network-route53-cloudfront-s3-apigw.yml` from `v0.0.17/2026-03-17` to `v0.0.18` with today's date
  - Current PATCH version is 17 (> 0), so increment is required per version control steering
  - _Requirements: 8.1, 8.2, 8.3_

- [x] 2. Modify CloudFront distribution to add Origin Request Policy
  - [x] 2.1 Add OriginRequestPolicyId to DefaultCacheBehavior
    - Add `OriginRequestPolicyId` property to the `DefaultCacheBehavior` in the `CloudFrontDistribution` resource
    - Use `!If [StaticOriginIsRoot, !Ref "AWS::NoValue", "b689b0a8-53d0-40ab-baf2-68738e2966ac"]` to conditionally apply the policy only when API is the root origin
    - When `StaticOriginIsRoot` is true, no origin request policy is set (static behaviors are unaffected)
    - _Requirements: 1.1, 1.2, 5.2_

  - [x] 2.2 Add OriginRequestPolicyId to API path cache behavior
    - Add `OriginRequestPolicyId: b689b0a8-53d0-40ab-baf2-68738e2966ac` to the API path cache behavior in `CacheBehaviors` (the one gated by `HasRouteForApiInCloudFront`)
    - Do NOT add `OriginRequestPolicyId` to the static path cache behavior
    - _Requirements: 2.1, 5.1_

- [x] 3. Update CloudFrontCachePolicyApi HeadersConfig
  - Replace the conditional `HeadersConfig` block in `CloudFrontCachePolicyApi` resource with a static `HeaderBehavior: none`
  - Remove the `!If` conditional that references `HasHeadersToForwardToApi`
  - The new HeadersConfig should simply be `HeadersConfig:` with `HeaderBehavior: none`
  - _Requirements: 3.1, 3.2_

- [x] 4. Remove HasHeadersToForwardToApi condition
  - Remove the `HasHeadersToForwardToApi` condition from the `Conditions` section entirely
  - Verify no other resource or output references this condition before removing
  - _Requirements: 3.3_

- [x] 5. Deprecate HeadersToForwardToApi parameter
  - [x] 5.1 Update parameter description to deprecated
    - Update the `HeadersToForwardToApi` parameter description to indicate it is deprecated
    - Add notice that header forwarding is now handled by the AllViewerExceptHostHeader origin request policy
    - Retain the parameter definition and its existing default value (`'Accept,Origin,Referer,User-Agent,Authorization'`)
    - _Requirements: 4.1, 4.2, 4.3, 7.1_

  - [x] 5.2 Update Metadata parameter group label
    - Change the label `"API behind CloudFront Forwarding"` to `"API behind CloudFront Forwarding (Deprecated)"` in the `Metadata` `ParameterGroups` section
    - Retain the `HeadersToForwardToApi` parameter in the group
    - _Requirements: 6.1, 6.2_

- [x] 6. Checkpoint - Validate template
  - Ensure all tests pass, ask the user if questions arise.
  - Run cfn-lint validation against the modified template to ensure it remains valid CloudFormation
  - Verify no references to the removed `HasHeadersToForwardToApi` condition remain
  - Verify the `HeadersToForwardToApi` parameter is retained but unused by any resource
  - _Requirements: 7.2, 7.3_

- [x] 7. Update documentation
  - [x] 7.1 Update template README documentation
    - Update `docs/templates/v2/network/template-network-route53-cloudfront-s3-apigw-README.md`
    - Update the version number to match the new template version
    - Document the new origin request policy behavior on API cache behaviors
    - Document the deprecation of `HeadersToForwardToApi` parameter
    - Document the removal of the `HasHeadersToForwardToApi` condition
    - Preserve all existing blockquotes and custom content
    - _Requirements: 4.2, 6.1_

  - [x] 7.2 Update CHANGELOG.md
    - Add entry under the `v0.0.34 (unreleased)` section
    - Include template name with new version number
    - Reference the spec: `[Spec: cloudfront-origin-request-policy](../.kiro/specs/0-0-34-cloudfront-origin-request-policy/)`
    - Categorize under `Changed` for the origin request policy addition and `Deprecated` for the HeadersToForwardToApi parameter
    - _Requirements: 8.1_

- [x] 8. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Run cfn-lint validation one final time
  - Verify backward compatibility: parameter retained, no new required parameters, origin request policy applied to API behaviors

## Notes

- No new CloudFormation resources are created — only existing resource properties are modified
- The AWS managed Origin Request Policy ID `b689b0a8-53d0-40ab-baf2-68738e2966ac` is a stable, well-known identifier
- Property-based testing is not applicable for this feature (IaC template changes only)
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation via cfn-lint
