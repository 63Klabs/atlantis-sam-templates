# Implementation Plan: Add Origin Path Parameters to CloudFront Network Template

## Overview

This implementation adds two new optional parameters (`StaticOriginPath` and `ApiOriginPath`) to the CloudFront network template, allowing users to customize origin paths while maintaining full backward compatibility. The implementation follows the template parameter standards and version control guidelines.

## Tasks

- [x] 1. Version Management
  - Increment template version from v0.0.14 to v0.0.15
  - Update version date to current date
  - _Requirements: All (non-breaking change)_

- [x] 2. Add Parameter Definitions
  - [x] 2.1 Add StaticOriginPath parameter to Parameters section
    - Set Type to String
    - Set Default to empty string
    - Add comprehensive Description with examples
    - Set AllowedPattern to `^$|^\/$|^\/[a-zA-Z0-9\/_-]+[^\/]$`
    - Add clear ConstraintDescription with valid examples
    - _Requirements: 1.1, 1.5, 1.6, 1.7, 3.1, 3.5, 7.1, 7.3_
  
  - [x] 2.2 Add ApiOriginPath parameter to Parameters section
    - Set Type to String
    - Set Default to empty string
    - Add comprehensive Description with examples
    - Set AllowedPattern to `^$|^\/$|^\/[a-zA-Z0-9\/_-]+[^\/]$`
    - Add clear ConstraintDescription with valid examples
    - _Requirements: 2.1, 2.5, 2.6, 2.7, 3.1, 3.5, 7.2, 7.3_

- [x] 3. Update Metadata Parameter Groups
  - [x] 3.1 Add StaticOriginPath to "Origins for S3 and/or API Gateway" parameter group
    - Position after ApiGatewayId parameter
    - _Requirements: 6.1, 6.3_
  
  - [x] 3.2 Add ApiOriginPath to "Origins for S3 and/or API Gateway" parameter group
    - Position after StaticOriginPath parameter
    - _Requirements: 6.2, 6.3_

- [x] 4. Add Conditional Logic
  - [x] 4.1 Add conditions for StaticOriginPath
    - Add StaticOriginPathIsEmpty condition
    - Add StaticOriginPathIsRoot condition
    - Add UseDefaultStaticOriginPath condition
    - Add UseRootStaticOriginPath condition
    - Add UseCustomStaticOriginPath condition
    - _Requirements: 1.2, 1.3, 1.4, 4.1, 4.2, 4.3_
  
  - [x] 4.2 Add conditions for ApiOriginPath
    - Add ApiOriginPathIsEmpty condition
    - Add ApiOriginPathIsRoot condition
    - Add UseDefaultApiOriginPath condition
    - Add UseRootApiOriginPath condition
    - Add UseCustomApiOriginPath condition
    - _Requirements: 2.2, 2.3, 2.4, 4.4, 4.5, 4.6_

- [x] 5. Update CloudFront Distribution Origins
  - [x] 5.1 Update Static S3 Origin OriginPath
    - Replace hardcoded `!Sub "/${StageId}/public"` with conditional logic
    - Use !If with UseDefaultStaticOriginPath for default path
    - Use nested !If with UseRootStaticOriginPath for empty string
    - Use !Ref StaticOriginPath for custom paths
    - _Requirements: 1.2, 1.3, 1.4, 4.1, 4.2, 4.3, 5.1_
  
  - [x] 5.2 Update API Gateway Origin OriginPath
    - Replace hardcoded `!Sub "/${ProjectId}-${StageId}"` with conditional logic
    - Use !If with UseDefaultApiOriginPath for default path
    - Use nested !If with UseRootApiOriginPath for empty string
    - Use !Ref ApiOriginPath for custom paths
    - _Requirements: 2.2, 2.3, 2.4, 4.4, 4.5, 4.6, 5.1_

- [x] 6. Update Outputs Section
  - [x] 6.1 Update S3Origin output
    - Modify to use conditional logic for origin path
    - Ensure output reflects actual origin path used
    - _Requirements: 1.2, 1.3, 1.4_
  
  - [x] 6.2 Update ApiGatewayOrigin output
    - Modify to use conditional logic for origin path
    - Ensure output reflects actual origin path used
    - _Requirements: 2.2, 2.3, 2.4_

- [x] 7. Checkpoint - Validate Template Syntax
  - Run cfn-lint on the modified template
  - Ensure no syntax errors or warnings
  - Verify all conditions are properly defined
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Write Unit Tests
  - [x] 8.1 Write unit test for StaticOriginPath parameter structure
    - Verify parameter exists in template
    - Verify parameter has correct Type, Default, AllowedPattern
    - Verify parameter has ConstraintDescription
    - Verify parameter is in correct metadata group
    - _Requirements: 1.1, 6.1, 6.3, 7.1_
  
  - [x] 8.2 Write unit test for ApiOriginPath parameter structure
    - Verify parameter exists in template
    - Verify parameter has correct Type, Default, AllowedPattern
    - Verify parameter has ConstraintDescription
    - Verify parameter is in correct metadata group
    - _Requirements: 2.1, 6.2, 6.3, 7.2_
  
  - [x] 8.3 Write unit test for root path edge case
    - Test StaticOriginPath = "/" produces empty string
    - Test ApiOriginPath = "/" produces empty string
    - _Requirements: 1.3, 2.3_
  
  - [x] 8.4 Write unit test for regex validation
    - Test regex rejects paths without leading /
    - Test regex rejects paths with trailing / (except /)
    - Test regex rejects paths with { or } characters
    - Test regex accepts valid custom paths
    - _Requirements: 1.5, 1.6, 1.7, 2.5, 2.6, 2.7, 3.2, 3.3, 3.4_

- [x] 9. Write Property-Based Tests
  - [x] 9.1 Write property test for default static origin path
    - **Property 1: Default Static Origin Path**
    - **Validates: Requirements 1.2, 4.1**
    - Generate random valid StageId values
    - Verify origin path equals /${StageId}/public when StaticOriginPath is empty
    - Run minimum 100 iterations
  
  - [x] 9.2 Write property test for default API origin path
    - **Property 2: Default API Origin Path**
    - **Validates: Requirements 2.2, 4.4**
    - Generate random valid ProjectId and StageId values
    - Verify origin path equals /${ProjectId}-${StageId} when ApiOriginPath is empty
    - Run minimum 100 iterations
  
  - [x] 9.3 Write property test for custom static origin path passthrough
    - **Property 3: Custom Static Origin Path Passthrough**
    - **Validates: Requirements 1.4, 4.3**
    - Generate random valid custom paths
    - Verify origin path equals input path exactly
    - Run minimum 100 iterations
  
  - [x] 9.4 Write property test for custom API origin path passthrough
    - **Property 4: Custom API Origin Path Passthrough**
    - **Validates: Requirements 2.4, 4.6**
    - Generate random valid custom paths
    - Verify origin path equals input path exactly
    - Run minimum 100 iterations
  
  - [x] 9.5 Write property test for path validation
    - **Property 5: Path Validation Rejects Invalid Formats**
    - **Validates: Requirements 1.5, 1.6, 1.7, 2.5, 2.6, 2.7, 3.2, 3.3, 3.4**
    - Generate random invalid paths (missing /, trailing /, with {})
    - Verify all invalid paths are rejected by regex
    - Run minimum 100 iterations
  
  - [x] 9.6 Write property test for backward compatibility
    - **Property 6: Backward Compatibility**
    - **Validates: Requirements 5.1**
    - Generate random valid ProjectId and StageId values
    - Set both origin paths to empty string
    - Verify static origin path equals /${StageId}/public
    - Verify API origin path equals /${ProjectId}-${StageId}
    - Run minimum 100 iterations

- [x] 10. Final Checkpoint - Run All Tests
  - Run all unit tests
  - Run all property-based tests
  - Verify all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Update Template Documentation
  - [x] 11.1 Update template-network-route53-cloudfront-s3-apigw-README.md
    - Add StaticOriginPath parameter documentation
    - Add ApiOriginPath parameter documentation
    - Include examples of valid path formats
    - Add migration guidance for customizing origin paths
    - Update version number and date
    - _Requirements: 7.4, 7.5_
  
  - [x] 11.2 Update category README if needed
    - Verify network category README references updated template
    - Update any version references

- [x] 12. Update CHANGELOG.md
  - Add entry under "Unreleased" section in "Changed" category
  - Format: **Network: template-network-route53-cloudfront-s3-apigw.yml v0.0.15** - Added StaticOriginPath and ApiOriginPath parameters for customizable CloudFront origin paths
  - Reference spec: [Spec: 0-0-29-network-add-origin-path-to-static-and-api](../.kiro/specs/0-0-29-network-add-origin-path-to-static-and-api/)

## Notes

- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties with minimum 100 iterations
- Unit tests validate specific examples and edge cases
- Template version increment happens first as this is a non-breaking change (PATCH increment)
- All parameter changes follow template-parameter-standards.md guidelines
- Documentation updates follow documentation-end-user-cfn-templates.md guidelines
- CHANGELOG updates follow changelog.md guidelines
