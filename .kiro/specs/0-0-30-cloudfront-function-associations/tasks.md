# Implementation Plan: CloudFront Function Associations

## Overview

Add 8 optional CloudFormation parameters to `template-network-route53-cloudfront-s3-apigw.yml` that allow users to associate existing CloudFront Functions with static and API cache behaviors. Implementation involves parameters, metadata groups, conditions, cache behavior modifications, tests, documentation, and changelog. Since PATCH=0 (development mode), no version increment is needed.

## Tasks

- [x] 1. Add CloudFront Function parameters and metadata groups
  - [x] 1.1 Add 4 static CloudFront Function ARN parameters to the Parameters section
    - Add `CloudFrontStaticFunctionViewerRequest`, `CloudFrontStaticFunctionViewerResponse`, `CloudFrontStaticFunctionOriginRequest`, `CloudFrontStaticFunctionOriginResponse`
    - Each parameter: Type String, Default "", AllowedPattern for CloudFront Function ARN or empty, ConstraintDescription
    - Place parameters after the existing Cache Policy parameters section (after `CloudFrontApiCustomCachePolicyArn`)
    - Use the ARN regex: `^arn:aws:cloudfront::[0-9]{12}:function\\/[a-zA-Z0-9-_]{1,64}$|^$`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_
  - [x] 1.2 Add 4 API CloudFront Function ARN parameters to the Parameters section
    - Add `CloudFrontApiFunctionViewerRequest`, `CloudFrontApiFunctionViewerResponse`, `CloudFrontApiFunctionOriginRequest`, `CloudFrontApiFunctionOriginResponse`
    - Same structure as static parameters but with API-specific descriptions
    - Place parameters after the static CloudFront Function parameters
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_
  - [x] 1.3 Add 2 new metadata parameter groups to `AWS::CloudFormation::Interface`
    - Add "Static CloudFront Function Associations" group after "Cache Policies" group with the 4 static parameters in order
    - Add "API CloudFront Function Associations" group after the static group with the 4 API parameters in order
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 2. Add conditions for CloudFront Function parameters
  - [x] 2.1 Add 8 new conditions to the Conditions section
    - Add `HasStaticFunctionViewerRequest`, `HasStaticFunctionViewerResponse`, `HasStaticFunctionOriginRequest`, `HasStaticFunctionOriginResponse`
    - Add `HasApiFunctionViewerRequest`, `HasApiFunctionViewerResponse`, `HasApiFunctionOriginRequest`, `HasApiFunctionOriginResponse`
    - Each condition uses `!Not [!Equals [!Ref <param>, '']]` pattern
    - Place conditions after existing conditions (e.g., after the Cache Policy conditions block)
    - _Requirements: 4.1, 4.2_

- [x] 3. Modify cache behaviors to add FunctionAssociations
  - [x] 3.1 Add FunctionAssociations to DefaultCacheBehavior with `!If StaticOriginIsRoot` branching
    - When StaticOriginIsRoot is true: include static function associations (4 items, each wrapped in `!If` with `AWS::NoValue`)
    - When StaticOriginIsRoot is false: include API function associations (4 items, each wrapped in `!If` with `AWS::NoValue`)
    - Add the `FunctionAssociations` property after the existing `CachedMethods` property in DefaultCacheBehavior
    - _Requirements: 4.3, 4.4, 5.1, 5.2, 5.3, 7.1, 7.2, 7.3, 9.2, 9.4_
  - [x] 3.2 Add FunctionAssociations to the static path cache behavior
    - Add static function associations (4 items, each wrapped in `!If` with `AWS::NoValue`) to the `HasRouteForStaticOrigin` cache behavior
    - _Requirements: 4.3, 4.4, 6.1, 6.2, 6.3, 9.1_
  - [x] 3.3 Add FunctionAssociations to the API path cache behavior
    - Add API function associations (4 items, each wrapped in `!If` with `AWS::NoValue`) to the `HasRouteForApiInCloudFront` cache behavior
    - _Requirements: 4.3, 4.4, 8.1, 8.2, 8.3, 9.3_

- [x] 4. Checkpoint - Verify template structure
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Write unit tests for CloudFront Function Associations
  - [x] 5.1 Add unit tests for parameter definitions and metadata groups
    - Test all 8 parameters exist with correct Type, Default, AllowedPattern, ConstraintDescription
    - Test ARN regex with concrete valid/invalid examples
    - Test both metadata parameter groups exist with correct parameters in correct order
    - Test metadata group ordering (Static after Cache Policies, API after Static)
    - Extend `tests/test_network_template_unit.py` with a new test class
    - _Requirements: 1.1–1.7, 2.1–2.7, 3.1–3.6_
  - [x] 5.2 Add unit tests for conditions
    - Test all 8 Has* conditions exist in the template
    - Test each condition uses the `!Not [!Equals [!Ref <param>, '']]` pattern
    - _Requirements: 4.1, 4.2_
  - [x] 5.3 Add unit tests for DefaultCacheBehavior FunctionAssociations
    - Test FunctionAssociations property exists in DefaultCacheBehavior
    - Test the top-level `!If StaticOriginIsRoot` branching
    - Test static branch has 4 function association items with correct event types and parameter refs
    - Test API branch has 4 function association items with correct event types and parameter refs
    - _Requirements: 5.1, 5.2, 5.3, 7.1, 7.2, 7.3, 9.2, 9.4_
  - [x] 5.4 Add unit tests for path-based cache behavior FunctionAssociations
    - Test static path behavior has static FunctionAssociations (4 items with correct event types)
    - Test API path behavior has API FunctionAssociations (4 items with correct event types)
    - Test isolation: no API function refs in static path behavior, no static function refs in API path behavior
    - _Requirements: 6.1, 6.2, 6.3, 8.1, 8.2, 8.3, 9.1, 9.3_
  - [x] 5.5 Add unit tests for backward compatibility
    - Test template version remains v0.0.16
    - Test all 8 parameters default to empty string (Property 1)
    - _Requirements: 10.1, 10.2, 10.3, 11.1_

- [x] 6. Checkpoint - Ensure all unit tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Write property-based test for ARN regex validation
  - [x] 7.1 Add property test for CloudFront Function ARN regex
    - **Property 2: ARN validation regex accepts valid CloudFront Function ARNs and rejects invalid strings**
    - **Validates: Requirements 1.6, 2.6**
    - Generate random valid ARNs (random 12-digit account IDs, random valid function names) and verify they match
    - Generate random invalid strings (missing components, wrong formats) and verify they don't match
    - Use 10-20 iterations per steering guidelines
    - Extend `tests/test_network_template_property.py`
    - Tag: `Feature: cloudfront-function-associations, Property 2`

- [x] 8. Update documentation and changelog
  - [x] 8.1 Update template documentation
    - Update `docs/templates/v2/network/template-network-route53-cloudfront-s3-apigw-README.md`
    - Add the 8 new parameters under two new parameter group sections ("Static CloudFront Function Associations" and "API CloudFront Function Associations")
    - Document each parameter with its attributes table (Type, Default, AllowedPattern, ConstraintDescription)
    - Add the 8 new conditions to the Conditions section if documented
    - Preserve all existing blockquotes and custom content
    - _Requirements: 1.1–1.7, 2.1–2.7, 3.1–3.6_
  - [x] 8.2 Update CHANGELOG.md
    - Add entry under the "v0.0.30 - unreleased" section
    - Reference the spec: `[Spec: cloudfront-function-associations](../.kiro/specs/cloudfront-function-associations/)`
    - Categorize as "Added" with description of CloudFront Function association support
    - Note template remains at v0.0.16 (PATCH=0, development mode)
    - _Requirements: 11.1_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Since PATCH=0 (development mode), no version increment task is included per template-version-control.md
- Property-based tests are minimal (1 test, 10-20 iterations) per testing-guidelines.md steering rules
- Unit tests are the primary testing mechanism and are required
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
