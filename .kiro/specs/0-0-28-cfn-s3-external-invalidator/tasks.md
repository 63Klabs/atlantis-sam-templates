# Implementation Plan

- [x] 1. Create new template file and update metadata
  - Copy `template-storage-s3-oac-for-cloudfront.yml` to `template-storage-s3-oac-for-cloudfront-v2.yml`
  - Update Description field to indicate support for external invalidator services
  - Update version comment to v0.1.0 with current date
  - Update Metadata section to include InvalidatorArn in parameter groups
  - _Requirements: 1.1, 8.1, 8.2, 8.5_

- [x] 2. Add InvalidatorArn parameter and condition
  - Add InvalidatorArn parameter with appropriate description, default value, and AllowedPattern regex
  - Add HasInvalidatorArn condition that checks if InvalidatorArn is not empty
  - _Requirements: 2.1, 2.4, 2.5_

- [x] 2.1 Write property test for ARN pattern validation
  - **Property 2: ARN pattern validation**
  - **Validates: Requirements 2.4**

- [x] 3. Remove embedded invalidator resources
  - Remove CloudFrontInvalidator Lambda function resource
  - Remove CloudFrontInvalidatorRole IAM role resource
  - Remove CloudFrontInvalidatorLogGroup log group resource
  - Remove CloudFrontInvalidatorErrorsAlarm alarm resource
  - Remove CloudFrontInvalidatorErrorAlarmNotification SNS topic resource
  - Remove old S3InvokeLambdaPermission resource
  - _Requirements: 1.3, 1.4, 1.5_

- [x] 4. Modify S3 bucket resource with conditional logic
  - Add conditional Tags property with AllowInvalidationEvents=true tag using HasInvalidatorArn condition
  - Modify NotificationConfiguration to use conditional logic with HasInvalidatorArn
  - Update LambdaConfigurations to reference InvalidatorArn parameter instead of hardcoded function
  - Ensure event types include ObjectCreated:*, ObjectRemoved:*, and LifecycleExpiration:*
  - _Requirements: 2.2, 2.3, 3.1, 3.2, 3.3, 3.5, 4.1, 4.5_

- [x] 5. Create conditional Lambda permission resource
  - Create new AWS::Lambda::Permission resource with HasInvalidatorArn condition
  - Set FunctionName to reference InvalidatorArn parameter
  - Set Principal to s3.amazonaws.com
  - Set SourceAccount to AWS::AccountId
  - Set SourceArn to reference Bucket ARN
  - _Requirements: 4.3, 4.4, 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 6. Add documentation comments for future service types
  - Add commented example for SQS queue invocation with required permissions and tag condition
  - Add commented example for Step Functions invocation with required permissions and tag condition
  - Add commented example for SNS topic invocation with required permissions and tag condition
  - Include appropriate IAM actions for each service type in comments
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 7. Add new outputs
  - Add InvalidatorArn output with HasInvalidatorArn condition
  - Add InvalidationEventsEnabled output that returns true/false based on HasInvalidatorArn
  - _Requirements: 8.3, 8.4_

- [x] 8. Verify backward compatibility
  - Confirm all original parameters are retained
  - Confirm S3 bucket properties (excluding NotificationConfiguration and Tags) are identical
  - Confirm bucket policy statements for CloudFront and CodeBuild are unchanged
  - Confirm all original outputs are retained
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 8.1 Write property test for parameter retention
  - **Property 1: Parameter retention**
  - **Validates: Requirements 1.2, 6.1**

- [x] 8.2 Write property test for resource naming consistency
  - **Property 3: Resource naming consistency**
  - **Validates: Requirements 6.2**

- [x] 8.3 Write property test for S3 bucket property preservation
  - **Property 4: S3 bucket property preservation**
  - **Validates: Requirements 6.3**

- [x] 8.4 Write property test for bucket policy statement preservation
  - **Property 5: Bucket policy statement preservation**
  - **Validates: Requirements 6.4**

- [x] 8.5 Write property test for output retention
  - **Property 6: Output retention**
  - **Validates: Requirements 6.5**

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
