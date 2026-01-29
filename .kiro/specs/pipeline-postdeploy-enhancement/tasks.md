# Implementation Plan

- [x] 1. Fix parameter naming inconsistencies and add missing condition
  - Fix metadata reference to use correct parameter name "PostDeployStageEnabled"
  - Add missing "IsPostDeployEnabled" condition to CloudFormation conditions section
  - Update any incorrect parameter references throughout the template
  - _Requirements: 2.1, 2.2_

- [x] 2. Implement conditional resource creation for PostDeploy components
- [x] 2.1 Add conditional logic to PostDeployServiceRole
  - Add "IsPostDeployEnabled" condition to PostDeployServiceRole resource
  - Ensure role is only created when PostDeploy stage is enabled
  - _Requirements: 1.5_

- [x] 2.2 Add conditional logic to PostDeployProject
  - Add "IsPostDeployEnabled" condition to PostDeployProject resource
  - Ensure CodeBuild project is only created when PostDeploy stage is enabled
  - _Requirements: 1.3, 1.4_

- [x] 2.3 Add conditional logic to PostDeployLogGroup
  - Add "IsPostDeployEnabled" condition to PostDeployLogGroup resource
  - Ensure log group is only created when PostDeploy stage is enabled
  - _Requirements: 4.5_

- [x] 3. Fix IAM permissions for PostDeploy S3 buildspec access
- [x] 3.1 Correct S3 buildspec permissions in PostDeployServiceRole
  - Fix the IAM policy statement that references incorrect BuildSpec parameter
  - Update to properly reference PostDeployBuildSpec parameter for S3 permissions
  - Ensure conditional S3 permissions are only added when S3 buildspec is used
  - _Requirements: 2.4, 5.3_

- [x] 3.2 Add missing condition for PostDeploy S3 buildspec location
  - Create "HasPostDeployBuildSpecS3Location" condition that combines IsPostDeployEnabled with S3 buildspec check
  - Update IAM policy to use the new condition
  - _Requirements: 2.4_

- [x] 4. Implement conditional PostDeploy stage in pipeline
- [x] 4.1 Make PostDeploy stage conditional in pipeline definition
  - Modify ProjectPipeline resource to conditionally include PostDeploy stage
  - Use CloudFormation conditional logic to include/exclude the stage based on IsPostDeployEnabled
  - Ensure proper stage ordering and dependencies
  - _Requirements: 1.1, 1.2_

- [x] 4.2 Update pipeline dependencies
  - Ensure PostDeployProject is included in DependsOn when PostDeploy is enabled
  - Verify proper artifact flow between Deploy and PostDeploy stages
  - _Requirements: 1.1_

- [x] 5. Enhance PostDeploy CodeBuild project configuration
- [x] 5.1 Add missing environment variable for PostDeploy S3 bucket
  - Ensure POST_DEPLOY_S3_STATIC_HOST_BUCKET environment variable is properly configured
  - Verify it references the PostDeployS3StaticHostBucket parameter
  - _Requirements: 2.5, 4.4_

- [x] 5.2 Verify environment variable consistency with Build stage
  - Compare PostDeployProject environment variables with CodeBuildProject
  - Ensure all core environment variables are consistent between stages
  - _Requirements: 4.1, 4.4_

- [x] 6. Create comprehensive property-based tests for PostDeploy functionality
- [x] 6.1 Write property test for conditional resource creation
  - **Property 1: Conditional Resource Creation**
  - **Validates: Requirements 1.3, 1.4, 1.5**

- [x] 6.2 Write property test for pipeline stage conditional inclusion
  - **Property 2: Pipeline Stage Conditional Inclusion**
  - **Validates: Requirements 1.1, 1.2**

- [x] 6.3 Write property test for parameter naming consistency
  - **Property 3: Parameter Naming Consistency**
  - **Validates: Requirements 2.1**

- [x] 6.4 Write property test for condition name consistency
  - **Property 4: Condition Name Consistency**
  - **Validates: Requirements 2.2**

- [x] 6.5 Write property test for BuildSpec parameter reference
  - **Property 5: BuildSpec Parameter Reference**
  - **Validates: Requirements 2.3**

- [x] 6.6 Write property test for S3 BuildSpec IAM permissions
  - **Property 6: S3 BuildSpec IAM Permissions**
  - **Validates: Requirements 2.4**

- [x] 6.7 Write property test for environment variable configuration
  - **Property 7: Environment Variable Configuration**
  - **Validates: Requirements 2.5**

- [x] 6.8 Write property test for compute environment consistency
  - **Property 8: Compute Environment Consistency**
  - **Validates: Requirements 4.1**

- [x] 6.9 Write property test for S3 permission consistency
  - **Property 9: S3 Permission Consistency**
  - **Validates: Requirements 4.2**

- [x] 6.10 Write property test for SSM permission consistency
  - **Property 10: SSM Permission Consistency**
  - **Validates: Requirements 4.3**

- [x] 6.11 Write property test for core environment variable consistency
  - **Property 11: Core Environment Variable Consistency**
  - **Validates: Requirements 4.4**

- [x] 6.12 Write property test for log group configuration
  - **Property 12: Log Group Configuration**
  - **Validates: Requirements 4.5**

- [x] 6.13 Write property test for BuildSpec path validation
  - **Property 13: BuildSpec Path Validation**
  - **Validates: Requirements 5.1**

- [x] 6.14 Write property test for S3 URI validation
  - **Property 14: S3 URI Validation**
  - **Validates: Requirements 5.2**

- [x] 6.15 Write property test for default BuildSpec configuration
  - **Property 15: Default BuildSpec Configuration**
  - **Validates: Requirements 5.4, 5.5**

- [x] 7. Create unit tests for specific PostDeploy scenarios
- [x] 7.1 Write unit tests for parameter validation examples
  - Test specific valid/invalid buildspec paths and S3 URIs
  - Test specific valid/invalid S3 bucket names
  - Test parameter constraint edge cases
  - _Requirements: 5.1, 5.2_

- [x] 7.2 Write unit tests for resource configuration examples
  - Test specific PostDeploy resource configurations
  - Test IAM permission structure examples
  - Test environment variable configuration examples
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 8. Update buildspec and testing infrastructure
- [x] 8.1 Enhance buildspec to run PostDeploy tests
  - Update buildspec.yml to include PostDeploy template testing
  - Ensure tests run as part of the CI/CD pipeline
  - Add test reporting and failure handling
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 8.2 Create test utilities for CloudFormation template validation
  - Create helper functions for loading and parsing CloudFormation templates
  - Create utilities for validating conditional logic and parameter constraints
  - Ensure test utilities support both unit and property-based testing
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Documentation and validation
- [x] 10.1 Update template documentation and comments
  - Add clear documentation for PostDeploy conditional logic
  - Update parameter descriptions to reflect proper usage
  - Add examples of PostDeploy stage usage patterns
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 10.2 Create integration test examples
  - Create example buildspec-postdeploy.yml files
  - Create example parameter configurations for different use cases
  - Test end-to-end PostDeploy functionality with sample projects
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.