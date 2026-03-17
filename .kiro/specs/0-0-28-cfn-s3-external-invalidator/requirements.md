# Requirements Document

## Introduction

This feature creates a new version (v2) of the CloudFormation template for S3 storage with CloudFront Origin Access Control (OAC). The new template will remove the embedded Lambda invalidator function and instead support invoking an external invalidator service (Lambda, SQS, Step Functions, or SNS) via S3 event notifications. The template will use tag-based permissions to control which external services can be invoked by S3 events, providing a flexible and secure approach to cache invalidation across multiple stacks.

## Glossary

- **CFN Template**: AWS CloudFormation template - an infrastructure-as-code file that defines AWS resources
- **S3 Bucket**: Amazon Simple Storage Service bucket for object storage
- **OAC**: Origin Access Control - AWS CloudFront feature for secure access to S3 origins
- **Invalidator Service**: An external AWS service (Lambda, SQS, Step Functions, or SNS) that handles CloudFront cache invalidation
- **S3 Event Notification**: AWS S3 feature that triggers external services when objects are created, deleted, or modified
- **Tag-based Permission**: AWS IAM permission model using resource tags to control access
- **Stack**: A collection of AWS resources managed as a single unit via CloudFormation
- **Template Parameter**: A configurable input value for CloudFormation templates
- **Conditional Resource**: A CloudFormation resource that is only created when certain conditions are met

## Requirements

### Requirement 1

**User Story:** As a DevOps engineer, I want to create a new CloudFormation template version that removes the embedded invalidator function, so that I can use a centralized invalidator service across multiple S3 buckets.

#### Acceptance Criteria

1. WHEN the template is deployed THEN the system SHALL create a new file named `template-storage-s3-oac-for-cloudfront-v2.yml`
2. WHEN the new template is created THEN the system SHALL retain all existing parameters from the original template
3. WHEN the new template is created THEN the system SHALL remove the CloudFrontInvalidator Lambda function resource
4. WHEN the new template is created THEN the system SHALL remove the CloudFrontInvalidatorRole IAM role resource
5. WHEN the new template is created THEN the system SHALL remove the CloudFrontInvalidatorLogGroup resource

### Requirement 2

**User Story:** As a DevOps engineer, I want to configure an external invalidator service via a parameter, so that I can optionally enable cache invalidation for my S3 bucket.

#### Acceptance Criteria

1. WHEN defining template parameters THEN the system SHALL add an InvalidatorArn parameter that accepts Lambda, SQS, Step Functions, or SNS ARNs
2. WHEN the InvalidatorArn parameter is empty THEN the system SHALL create the S3 bucket without event notifications
3. WHEN the InvalidatorArn parameter contains a valid ARN THEN the system SHALL configure S3 event notifications to invoke the specified service
4. WHEN the InvalidatorArn parameter is validated THEN the system SHALL accept ARN patterns for Lambda functions, SQS queues, Step Functions state machines, and SNS topics
5. WHEN the InvalidatorArn parameter is provided THEN the system SHALL create a condition named HasInvalidatorArn that evaluates to true

### Requirement 3

**User Story:** As a DevOps engineer, I want S3 event notifications to trigger the external invalidator service, so that CloudFront cache is invalidated when objects change.

#### Acceptance Criteria

1. WHEN the InvalidatorArn parameter is provided THEN the system SHALL configure S3 event notifications for ObjectCreated events
2. WHEN the InvalidatorArn parameter is provided THEN the system SHALL configure S3 event notifications for ObjectRemoved events
3. WHEN the InvalidatorArn parameter is provided THEN the system SHALL configure S3 event notifications for LifecycleExpiration events
4. WHEN the InvalidatorArn parameter is provided THEN the system SHALL configure S3 event notifications for ObjectCreated:Copy events
5. WHEN S3 event notifications are configured THEN the system SHALL use conditional logic to include notifications only when HasInvalidatorArn is true

### Requirement 4

**User Story:** As a security engineer, I want tag-based permissions to control S3 event invocations, so that only authorized invalidator services can be triggered by S3 events.

#### Acceptance Criteria

1. WHEN the InvalidatorArn parameter is provided THEN the system SHALL add the tag `AllowInvalidationEvents` with value `true` to the S3 bucket
2. WHEN the S3 bucket policy is created THEN the system SHALL grant s3:InvokeFunction permission to Lambda services with the tag `AllowInvalidationEvents=true`
3. WHEN the S3 bucket policy is created THEN the system SHALL restrict invocation permissions to the source S3 bucket ARN
4. WHEN the S3 bucket policy is created THEN the system SHALL restrict invocation permissions to the AWS account that owns the bucket
5. WHEN the InvalidatorArn parameter is empty THEN the system SHALL not add the `AllowInvalidationEvents` tag to the S3 bucket

### Requirement 5

**User Story:** As a DevOps engineer, I want Lambda permission resources for S3 event invocations, so that S3 can successfully trigger the external Lambda function.

#### Acceptance Criteria

1. WHEN the InvalidatorArn parameter contains a Lambda ARN THEN the system SHALL create an AWS::Lambda::Permission resource
2. WHEN the Lambda permission is created THEN the system SHALL grant s3.amazonaws.com principal permission to invoke the Lambda function
3. WHEN the Lambda permission is created THEN the system SHALL restrict the source to the S3 bucket ARN
4. WHEN the Lambda permission is created THEN the system SHALL restrict the source to the current AWS account
5. WHEN the InvalidatorArn parameter is empty THEN the system SHALL not create the Lambda permission resource

### Requirement 6

**User Story:** As a DevOps engineer, I want the template to maintain backward compatibility, so that existing deployments are not disrupted.

#### Acceptance Criteria

1. WHEN comparing parameters THEN the system SHALL retain all parameters from the original template
2. WHEN the template is deployed THEN the system SHALL maintain the same resource naming conventions as the original template
3. WHEN the template is deployed THEN the system SHALL maintain the same S3 bucket properties as the original template
4. WHEN the template is deployed THEN the system SHALL maintain the same bucket policy statements for CloudFront and CodeBuild as the original template
5. WHEN the template outputs are defined THEN the system SHALL retain all outputs from the original template

### Requirement 7

**User Story:** As a DevOps engineer, I want clear documentation in the template, so that I understand how to configure tag-based permissions for future service types.

#### Acceptance Criteria

1. WHEN the bucket policy is created THEN the system SHALL include commented examples for SQS queue invocation permissions
2. WHEN the bucket policy is created THEN the system SHALL include commented examples for Step Functions state machine invocation permissions
3. WHEN the bucket policy is created THEN the system SHALL include commented examples for SNS topic invocation permissions
4. WHEN permission examples are provided THEN the system SHALL include the required tag condition for each service type
5. WHEN permission examples are provided THEN the system SHALL include the appropriate IAM actions for each service type

### Requirement 8

**User Story:** As a DevOps engineer, I want updated template metadata and outputs, so that the template accurately reflects its purpose and provides useful information.

#### Acceptance Criteria

1. WHEN the template description is updated THEN the system SHALL indicate support for external invalidator services
2. WHEN the template version is updated THEN the system SHALL increment the version number and update the date
3. WHEN template outputs are defined THEN the system SHALL add an output for the InvalidatorArn parameter value
4. WHEN template outputs are defined THEN the system SHALL add an output indicating whether invalidation events are enabled
5. WHEN the Metadata section is updated THEN the system SHALL add the InvalidatorArn parameter to the appropriate parameter group
