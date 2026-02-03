# Implementation Plan: AWS Managed Cache Policies for Network Template

## Overview

This implementation plan adds support for AWS managed cache policies to the template-network-route53-cloudfront-s3-apigw.yml template. The implementation will allow users to choose between AWS managed policies, custom default policies, or custom ARN-based policies for both static and API origins, with environment-based overrides for DEV and TEST environments.

## Tasks

- [x] 1. Version Management and Template Preparation
  - Increment template version from v0.0.15 to v0.0.16
  - Update version date to current date
  - _Requirements: 12.1, 12.2_

- [x] 2. Add Mappings Section
  - [x] 2.1 Create CachePolicyIds mapping with managed policy IDs
    - Add mapping for CachingOptimized: 658327ea-f89d-4fab-a63d-7e88639e58f6
    - Add mapping for CachingDisabled: 4135ea2d-6df8-44a3-9df3-4b5a84be39ad
    - Add mapping for CachingOptimizedForUncompressedObjects: b2884449-e4de-46a7-ac36-70bc7f1ddd6d
    - Add mapping for Elemental-MediaPackage: 08627262-05a9-4f76-9ded-b50ca2e3a84f
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.7, 5.8, 5.9, 5.10_

- [x] 3. Add Cache Policy Parameters
  - [x] 3.1 Add CloudFrontStaticCachePolicy parameter
    - Type: String
    - Default: CachingOptimized
    - AllowedValues: CachingOptimized, CachingDisabled, CachingOptimizedForUncompressedObjects, Elemental-MediaPackage, CustomDefault, CustomArn
    - Include descriptions for each option
    - Include note about DEV/TEST environment override
    - _Requirements: 1.1, 1.2, 1.3, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 11.4_
  
  - [x] 3.2 Add CloudFrontStaticCustomCachePolicyArn parameter
    - Type: String
    - Default: "" (empty string)
    - AllowedPattern: ^arn:aws:cloudfront::[0-9]{12}:cache-policy/[a-zA-Z0-9-]+$|^$
    - ConstraintDescription for invalid ARN format
    - _Requirements: 1.4, 1.5, 9.1, 9.3_
  
  - [x] 3.3 Add CloudFrontApiCachePolicy parameter
    - Type: String
    - Default: CachingDisabled
    - AllowedValues: CachingOptimized, CachingDisabled, CachingOptimizedForUncompressedObjects, Elemental-MediaPackage, CustomDefault, CustomArn
    - Include descriptions for each option
    - Include note about DEV/TEST environment override
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 11.4_
  
  - [x] 3.4 Add CloudFrontApiCustomCachePolicyArn parameter
    - Type: String
    - Default: "" (empty string)
    - AllowedPattern: ^arn:aws:cloudfront::[0-9]{12}:cache-policy/[a-zA-Z0-9-]+$|^$
    - ConstraintDescription for invalid ARN format
    - _Requirements: 2.4, 2.5, 9.2, 9.4_

- [-] 4. Update Metadata Section
  - [x] 4.1 Create "Cache Policies" parameter group
    - Add group label "Cache Policies"
    - Add parameters in order: CloudFrontStaticCachePolicy, CloudFrontStaticCustomCachePolicyArn, CloudFrontApiCachePolicy, CloudFrontApiCustomCachePolicyArn
    - Position group logically in parameter groups list (after "Deployment Environment", before "Supporting Resources")
    - _Requirements: 8.1, 8.2, 8.3_

- [x] 5. Add Conditions for Cache Policy Types
  - [x] 5.1 Add conditions for static cache policy types
    - StaticCachePolicyIsCustomDefault: !Equals [!Ref CloudFrontStaticCachePolicy, CustomDefault]
    - StaticCachePolicyIsCustomArn: !Equals [!Ref CloudFrontStaticCachePolicy, CustomArn]
    - _Requirements: 4.1, 4.2, 5.5, 5.6_
  
  - [x] 5.2 Add conditions for API cache policy types
    - ApiCachePolicyIsCustomDefault: !Equals [!Ref CloudFrontApiCachePolicy, CustomDefault]
    - ApiCachePolicyIsCustomArn: !Equals [!Ref CloudFrontApiCachePolicy, CustomArn]
    - _Requirements: 4.3, 4.4, 5.11, 5.12_
  
  - [x] 5.3 Add conditions for custom resource creation
    - CreateCustomStaticCachePolicy: !And [HasStaticOrigin, IsProduction, StaticCachePolicyIsCustomDefault]
    - CreateCustomApiCachePolicy: !And [IsProduction, ApiCachePolicyIsCustomDefault]
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 11.3_

- [x] 6. Update Custom Cache Policy Resources
  - [x] 6.1 Add condition to CloudFrontCachePolicyStatic resource
    - Add Condition: CreateCustomStaticCachePolicy
    - _Requirements: 4.1, 4.2_
  
  - [x] 6.2 Add condition to CloudFrontCachePolicyApi resource
    - Add Condition: CreateCustomApiCachePolicy
    - _Requirements: 4.3, 4.4, 4.5_

- [x] 7. Update CloudFront Distribution Resource
  - [x] 7.1 Add documentation comments with >! notation
    - Add comment block before DefaultCacheBehavior
    - Include: "Cache Policy Selection"
    - Include: "This template supports AWS managed cache policies and custom policies."
    - Include: Link to AWS documentation
    - Include: Note about DEV/TEST environment override
    - _Requirements: 7.1, 7.2, 7.3_
  
  - [x] 7.2 Update DefaultCacheBehavior cache policy resolution
    - Replace hardcoded !Ref with conditional logic
    - Use !If [IsProduction, ..., !FindInMap [CachePolicyIds, CachingDisabled, Id]]
    - For PROD: Use !If [IsCustomDefault, !Ref Resource, !If [IsCustomArn, !Ref ArnParam, !FindInMap]]
    - Apply to both static and API origin cases
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 5.11, 5.12, 6.1, 6.3, 11.1, 11.2_
  
  - [x] 7.3 Update static path CacheBehavior cache policy resolution
    - Replace hardcoded !Ref CloudFrontCachePolicyStatic with conditional logic
    - Use same resolution pattern as DefaultCacheBehavior for static origin
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.2, 11.1, 11.2_
  
  - [x] 7.4 Update API path CacheBehavior cache policy resolution
    - Replace hardcoded !Ref CloudFrontCachePolicyApi with conditional logic
    - Use same resolution pattern as DefaultCacheBehavior for API origin
    - _Requirements: 5.7, 5.8, 5.9, 5.10, 5.11, 5.12, 6.4, 11.1, 11.2_

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Unit Tests for Template Structure
  - [x] 9.1 Write unit tests for parameter definitions
    - Test CloudFrontStaticCachePolicy parameter exists with correct properties
    - Test CloudFrontStaticCustomCachePolicyArn parameter exists with correct properties
    - Test CloudFrontApiCachePolicy parameter exists with correct properties
    - Test CloudFrontApiCustomCachePolicyArn parameter exists with correct properties
    - Test default values are correct
    - Test AllowedValues lists are correct
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5_
  
  - [x] 9.2 Write unit tests for mappings section
    - Test CachePolicyIds mapping exists
    - Test all four managed policy IDs are correct
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [x] 9.3 Write unit tests for conditions
    - Test StaticCachePolicyIsCustomDefault condition exists
    - Test StaticCachePolicyIsCustomArn condition exists
    - Test ApiCachePolicyIsCustomDefault condition exists
    - Test ApiCachePolicyIsCustomArn condition exists
    - Test CreateCustomStaticCachePolicy condition exists
    - Test CreateCustomApiCachePolicy condition exists
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  
  - [x] 9.4 Write unit tests for metadata organization
    - Test "Cache Policies" parameter group exists
    - Test all four parameters are in the group
    - Test parameters are in correct order
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [x] 9.5 Write unit tests for documentation comments
    - Test >! notation comments exist in CloudFront distribution resource
    - Test comments reference AWS documentation
    - Test comments mention environment override
    - _Requirements: 7.1, 7.2, 7.3_
  
  - [x] 9.6 Write unit tests for backward compatibility
    - Test default values preserve existing behavior
    - Test PROD environment with defaults uses CachingOptimized for static
    - Test PROD environment with defaults uses CachingDisabled for API
    - _Requirements: 10.1, 10.2, 10.3_
  
  - [x] 9.7 Write unit tests for environment override
    - Test DEV environment forces CachingDisabled for both origins
    - Test TEST environment forces CachingDisabled for both origins
    - Test PROD environment respects parameter values
    - _Requirements: 11.1, 11.2, 10.4_

- [x] 10. Property-Based Tests
  - [x] 10.1 Write property test for custom ARN validation
    - Generate random strings (valid and invalid ARNs)
    - Verify CloudFormation accepts/rejects according to pattern
    - Run with 20 iterations
    - **Property 7: Custom ARN validation**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
  
  - [x] 10.2 Write property test for cache policy resolution
    - Generate random valid parameter combinations (DeployEnvironment, policy types)
    - Verify resolved cache policy IDs match expected values
    - Test managed policy lookups via FindInMap
    - Test CustomDefault resolves to resource reference
    - Test CustomArn resolves to parameter value
    - Test environment override for DEV/TEST
    - Run with 20 iterations
    - **Property 3: Static cache policy ARN resolution**
    - **Property 4: API cache policy ARN resolution**
    - **Property 6: Environment-based cache policy override**
    - **Validates: Requirements 5.1-5.12, 11.1, 11.2**

- [x] 11. Update Template Documentation
  - [x] 11.1 Update template-network-route53-cloudfront-s3-apigw-README.md
    - Add "Cache Policies" parameter group section
    - Document all four cache policy parameters with tables
    - Include examples of each policy type selection
    - Explain environment-based override behavior
    - Update CloudFrontCachePolicyStatic resource documentation (conditional creation)
    - Update CloudFrontCachePolicyApi resource documentation (conditional creation)
    - Update CloudFrontDistribution resource documentation (cache policy selection)
    - Add examples section for managed policies, CustomDefault, and CustomArn
    - Create "AWS Managed Cache Policies" section with AWS documentation link
    - _Requirements: All requirements (documentation coverage)_

- [x] 12. Update CHANGELOG.md
  - Add entry under "Unreleased" section
  - Format: "Network: template-network-route53-cloudfront-s3-apigw.yml v0.0.16 - Added support for AWS managed cache policies with environment-based overrides"
  - Reference spec: [Spec: 0-0-29-network-add-managed-cache-policies]
  - _Requirements: 12.1, 12.2_

## Notes

- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties with minimal iterations (20) per testing-guidelines.md
- Unit tests provide comprehensive coverage for CI/CD confidence
- The implementation uses CloudFormation mappings for cleaner, more maintainable code
- Environment-based overrides ensure DEV/TEST always use CachingDisabled
- Backward compatibility is maintained through default parameter values
