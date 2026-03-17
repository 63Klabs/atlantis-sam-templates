# Design Document

## Overview

This design describes the creation of a new CloudFormation template (`template-storage-s3-oac-for-cloudfront-v2.yml`) that removes the embedded Lambda invalidator function and replaces it with support for external invalidator services. The template will use conditional logic to optionally configure S3 event notifications that trigger external services (Lambda, SQS, Step Functions, or SNS) based on a provided ARN parameter. Tag-based permissions will control which services can be invoked by S3 events.

The design maintains full backward compatibility with the original template's parameter structure and resource naming conventions while providing a more flexible, centralized approach to cache invalidation across multiple S3 buckets.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ CloudFormation Stack (v2 Template)                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ S3 Bucket                                             │  │
│  │ - Tags: AllowInvalidationEvents=true (conditional)   │  │
│  │ - Event Notifications (conditional)                  │  │
│  │   • ObjectCreated:*                                  │  │
│  │   • ObjectRemoved:*                                  │  │
│  │   • LifecycleExpiration:*                            │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                          │
│                   │ S3 Events (if InvalidatorArn provided)   │
│                   ▼                                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Lambda Permission (conditional)                       │  │
│  │ - Grants s3.amazonaws.com invoke permission          │  │
│  │ - Source: S3 Bucket ARN                              │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                    │
                    │ Invokes (via ARN parameter)
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ External Invalidator Service (Separate Stack)               │
│                                                              │
│  Lambda / SQS / Step Functions / SNS                        │
│  - Tags: AllowInvalidationEvents=true                       │
│  - Handles CloudFront cache invalidation logic              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Conditional Resource Creation**: Use CloudFormation conditions to create event notifications and permissions only when InvalidatorArn is provided
2. **Tag-Based Security**: Use resource tags (`AllowInvalidationEvents=true`) to control which services can be invoked by S3 events
3. **Service-Agnostic ARN Parameter**: Accept any valid ARN (Lambda, SQS, Step Functions, SNS) to support future service type changes
4. **Minimal Template Scope**: Do not create IAM roles/policies for external services; let the invalidator stack manage its own permissions
5. **Backward Compatibility**: Retain all original parameters and resource structures to ensure existing deployments are not disrupted

## Components and Interfaces

### Parameters

#### New Parameters

**InvalidatorArn**
- Type: String
- Description: ARN of the external invalidator service (Lambda, SQS, Step Functions, or SNS). Leave empty to disable cache invalidation.
- Default: "" (empty string)
- AllowedPattern: `^$|^arn:aws:(lambda|sqs|states|sns):[a-z0-9-]+:\d{12}:(function|queue|stateMachine|topic)\/[a-zA-Z0-9-_]+$`
- ConstraintDescription: Must be empty or a valid ARN for Lambda, SQS, Step Functions, or SNS

#### Retained Parameters

All existing parameters from the original template are retained:
- Prefix
- ProjectId
- S3BucketNameOrgPrefix
- RolePath
- AlarmNotificationEmail
- PermissionsBoundaryArn
- S3LogBucketName

### Conditions

#### New Conditions

**HasInvalidatorArn**
- Logic: `!Not [!Equals [!Ref InvalidatorArn, ""]]`
- Purpose: Determines whether to create event notifications and permissions

#### Retained Conditions

- UseS3BucketNameOrgPrefix
- HasPermissionsBoundaryArn
- HasLoggingBucket

### Resources

#### Modified Resources

**Bucket (AWS::S3::Bucket)**
- Add conditional Tags property:
  - Key: `AllowInvalidationEvents`
  - Value: `true`
  - Condition: HasInvalidatorArn
- Modify NotificationConfiguration:
  - Use conditional logic to include LambdaConfigurations only when HasInvalidatorArn is true
  - Replace hardcoded Lambda ARN with `!Ref InvalidatorArn`
  - Retain event types: ObjectCreated:*, ObjectRemoved:*, LifecycleExpiration:*

**BucketPolicy (AWS::S3::BucketPolicy)**
- Retain all existing policy statements (DenyNonSecureTransportAccess, AllowCloudFrontServicePrincipalReadOnly, AllowCodeBuildReadWriteDelete)
- No modifications needed for tag-based permissions (handled by external service's resource policy)

#### New Resources

**S3InvokeLambdaPermission (AWS::Lambda::Permission)**
- Condition: HasInvalidatorArn
- FunctionName: !Ref InvalidatorArn
- Action: lambda:InvokeFunction
- Principal: s3.amazonaws.com
- SourceAccount: !Ref AWS::AccountId
- SourceArn: !GetAtt Bucket.Arn

#### Removed Resources

- CloudFrontInvalidator (AWS::Lambda::Function)
- CloudFrontInvalidatorRole (AWS::IAM::Role)
- CloudFrontInvalidatorLogGroup (AWS::Logs::LogGroup)
- CloudFrontInvalidatorErrorsAlarm (AWS::CloudWatch::Alarm)
- CloudFrontInvalidatorErrorAlarmNotification (AWS::SNS::Topic)
- S3InvokeLambdaPermission (replaced with new conditional version)

### Outputs

#### New Outputs

**InvalidatorArn**
- Condition: HasInvalidatorArn
- Description: ARN of the external invalidator service configured for S3 event notifications
- Value: !Ref InvalidatorArn

**InvalidationEventsEnabled**
- Description: Indicates whether S3 event notifications for cache invalidation are enabled
- Value: !If [HasInvalidatorArn, "true", "false"]

#### Retained Outputs

- BucketName
- OriginBucketDomainForCloudFront
- AllowedCloudFrontAndCodeBuild
- LoggingBucketName (conditional)

## Data Models

### S3 Event Notification Structure

```yaml
NotificationConfiguration:
  LambdaConfigurations:
    - Event: "s3:ObjectCreated:*"
      Function: !Ref InvalidatorArn
    - Event: "s3:ObjectRemoved:*"
      Function: !Ref InvalidatorArn
    - Event: "s3:LifecycleExpiration:*"
      Function: !Ref InvalidatorArn
```

### Tag Structure

```yaml
Tags:
  - Key: "AllowInvalidationEvents"
    Value: "true"
```

### Lambda Permission Structure

```yaml
Type: AWS::Lambda::Permission
Properties:
  FunctionName: !Ref InvalidatorArn
  Action: lambda:InvokeFunction
  Principal: s3.amazonaws.com
  SourceAccount: !Ref AWS::AccountId
  SourceArn: !GetAtt Bucket.Arn
```

## 
Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, several properties were identified as redundant:
- Criteria 3.4 (ObjectCreated:Copy events) is redundant with 3.1 since ObjectCreated:* includes all ObjectCreated event types
- Criteria 6.1 is redundant with 1.2 as both test parameter retention
- Criteria 4.2 is incorrectly specified (s3:InvokeFunction is not a valid S3 action; permissions are handled via AWS::Lambda::Permission)

The remaining testable properties focus on:
1. Template structure validation (parameters, resources, outputs)
2. Conditional logic correctness
3. ARN pattern validation
4. Backward compatibility verification

### Properties

**Property 1: Parameter retention**
*For any* parameter name in the original template, that parameter name must exist in the new template with the same Type
**Validates: Requirements 1.2, 6.1**

**Property 2: ARN pattern validation**
*For any* valid Lambda, SQS, Step Functions, or SNS ARN, the InvalidatorArn parameter's AllowedPattern regex must accept it, and for any invalid ARN format, the regex must reject it
**Validates: Requirements 2.4**

**Property 3: Resource naming consistency**
*For any* resource in the new template that also exists in the original template, the resource name pattern must be identical
**Validates: Requirements 6.2**

**Property 4: S3 bucket property preservation**
*For any* S3 bucket property in the original template (excluding NotificationConfiguration and Tags), that property must exist in the new template with identical structure
**Validates: Requirements 6.3**

**Property 5: Bucket policy statement preservation**
*For any* bucket policy statement with Sid "AllowCloudFrontServicePrincipalReadOnly" or "AllowCodeBuildReadWriteDelete", the statement structure must be identical between original and new templates
**Validates: Requirements 6.4**

**Property 6: Output retention**
*For any* output name in the original template, that output name must exist in the new template
**Validates: Requirements 6.5**

## Error Handling

### CloudFormation Validation Errors

**Invalid ARN Format**
- Error: Parameter validation fails if InvalidatorArn does not match the AllowedPattern
- Handling: CloudFormation will reject the stack creation/update with a clear error message
- User Action: Provide a valid ARN in the correct format

**Missing Lambda Function**
- Error: Stack creation fails if InvalidatorArn references a non-existent Lambda function
- Handling: CloudFormation will roll back the stack creation
- User Action: Ensure the Lambda function exists before deploying the stack, or deploy the invalidator stack first

**Insufficient Permissions**
- Error: S3 events fail to invoke the external service due to missing permissions
- Handling: S3 will log the error but continue operating normally
- User Action: Ensure the external service has appropriate resource-based policies and tags

### Runtime Errors

**S3 Event Notification Failures**
- Error: S3 cannot deliver events to the external service
- Handling: S3 will retry delivery and eventually drop the event
- User Action: Monitor CloudWatch Logs for the external service to detect missing events

**Tag Mismatch**
- Error: External service lacks the AllowInvalidationEvents=true tag
- Handling: S3 event invocation will be denied by IAM
- User Action: Add the required tag to the external service resource

## Testing Strategy

### Unit Testing

Unit tests will verify specific template structures and configurations:

1. **File Creation Test**: Verify that `template-storage-s3-oac-for-cloudfront-v2.yml` is created
2. **Resource Removal Tests**: Verify that CloudFrontInvalidator, CloudFrontInvalidatorRole, CloudFrontInvalidatorLogGroup, and related alarm resources are not present in the new template
3. **Parameter Presence Test**: Verify that InvalidatorArn parameter exists with correct properties
4. **Condition Presence Test**: Verify that HasInvalidatorArn condition exists with correct logic
5. **Event Type Tests**: Verify that ObjectCreated:*, ObjectRemoved:*, and LifecycleExpiration:* events are configured
6. **Tag Presence Test**: Verify that AllowInvalidationEvents tag is conditionally added to S3 bucket
7. **Lambda Permission Tests**: Verify that AWS::Lambda::Permission resource has correct Principal, SourceArn, and SourceAccount properties
8. **Output Tests**: Verify that InvalidatorArn and InvalidationEventsEnabled outputs exist
9. **Comment Tests**: Verify that commented examples for SQS, Step Functions, and SNS exist with appropriate content
10. **Metadata Test**: Verify that InvalidatorArn is added to a parameter group in Metadata

### Property-Based Testing

Property-based tests will verify universal properties across all valid inputs:

1. **Property Test: Parameter Retention** (Property 1)
   - Generate: Parse both original and new templates
   - Test: For each parameter in original, verify it exists in new template with same Type
   - Validates: Requirements 1.2, 6.1

2. **Property Test: ARN Pattern Validation** (Property 2)
   - Generate: Valid and invalid ARNs for Lambda, SQS, Step Functions, SNS
   - Test: Verify AllowedPattern regex accepts valid ARNs and rejects invalid ones
   - Validates: Requirements 2.4

3. **Property Test: Resource Naming Consistency** (Property 3)
   - Generate: Parse both templates and extract resource name patterns
   - Test: For each common resource, verify naming pattern is identical
   - Validates: Requirements 6.2

4. **Property Test: S3 Bucket Property Preservation** (Property 4)
   - Generate: Parse S3 bucket properties from both templates
   - Test: For each property (excluding NotificationConfiguration and Tags), verify identical structure
   - Validates: Requirements 6.3

5. **Property Test: Bucket Policy Statement Preservation** (Property 5)
   - Generate: Parse bucket policy statements from both templates
   - Test: For CloudFront and CodeBuild statements, verify identical structure
   - Validates: Requirements 6.4

6. **Property Test: Output Retention** (Property 6)
   - Generate: Parse outputs from both templates
   - Test: For each output in original, verify it exists in new template
   - Validates: Requirements 6.5

### Testing Tools

- **YAML Parser**: PyYAML or ruamel.yaml for parsing CloudFormation templates
- **Property Testing Library**: Hypothesis (Python) for generating test cases
- **CloudFormation Linter**: cfn-lint for validating template syntax and best practices
- **Unit Testing Framework**: pytest for running unit and property tests

### Test Execution Strategy

1. **Development Phase**: Run unit tests after each template modification to catch structural errors early
2. **Pre-Commit**: Run all unit tests and property tests before committing changes
3. **CI/CD Pipeline**: Run full test suite including cfn-lint validation
4. **Manual Validation**: Deploy test stacks with and without InvalidatorArn to verify conditional behavior

## Implementation Notes

### CloudFormation Conditional Syntax

The template will use CloudFormation intrinsic functions for conditional logic:

```yaml
# Condition definition
Conditions:
  HasInvalidatorArn: !Not [!Equals [!Ref InvalidatorArn, ""]]

# Conditional resource creation
S3InvokeLambdaPermission:
  Type: AWS::Lambda::Permission
  Condition: HasInvalidatorArn
  Properties:
    # ...

# Conditional property inclusion
Bucket:
  Type: AWS::S3::Bucket
  Properties:
    Tags: !If
      - HasInvalidatorArn
      - - Key: "AllowInvalidationEvents"
          Value: "true"
      - !Ref AWS::NoValue
    NotificationConfiguration: !If
      - HasInvalidatorArn
      - LambdaConfigurations:
          - Event: "s3:ObjectCreated:*"
            Function: !Ref InvalidatorArn
          # ...
      - !Ref AWS::NoValue
```

### ARN Pattern Regex

The InvalidatorArn parameter will use a comprehensive regex pattern to validate ARNs:

```
^$|^arn:aws:(lambda|sqs|states|sns):[a-z0-9-]+:\d{12}:(function|queue|stateMachine|topic)\/[a-zA-Z0-9-_]+$
```

This pattern:
- Allows empty string (^$)
- Validates service type (lambda|sqs|states|sns)
- Validates region format ([a-z0-9-]+)
- Validates account ID (\d{12})
- Validates resource type (function|queue|stateMachine|topic)
- Validates resource name ([a-zA-Z0-9-_]+)

### Future Service Type Support

The template includes commented examples for future service types:

```yaml
# Example for SQS Queue invocation (future support)
# QueueConfigurations:
#   - Event: "s3:ObjectCreated:*"
#     Queue: !Ref InvalidatorArn
#     # External SQS queue must have tag: AllowInvalidationEvents=true
#     # Required permission: sqs:SendMessage

# Example for SNS Topic invocation (future support)
# TopicConfigurations:
#   - Event: "s3:ObjectCreated:*"
#     Topic: !Ref InvalidatorArn
#     # External SNS topic must have tag: AllowInvalidationEvents=true
#     # Required permission: sns:Publish

# Example for Step Functions (via Lambda or EventBridge)
# Step Functions cannot be directly invoked by S3 events
# Use Lambda or EventBridge as an intermediary
```

### Tag-Based Permission Model

The tag-based permission model works as follows:

1. **S3 Bucket Tagging**: When InvalidatorArn is provided, the S3 bucket is tagged with `AllowInvalidationEvents=true`
2. **External Service Tagging**: The external invalidator service (Lambda, SQS, etc.) must also be tagged with `AllowInvalidationEvents=true`
3. **Permission Granting**: The AWS::Lambda::Permission resource grants s3.amazonaws.com permission to invoke the Lambda function, restricted by SourceArn and SourceAccount
4. **Future IAM Policies**: For centralized permission management, a separate IAM policy could be created that uses tag conditions to grant permissions across multiple services

### Version and Documentation Updates

- Version: Increment to v0.1.0 (major feature change)
- Date: Update to current date
- Description: Update to reflect external invalidator support
- Comments: Add detailed comments explaining conditional logic and tag-based permissions

## Dependencies

### External Dependencies

- **Invalidator Service Stack**: Must be deployed before or alongside this template
- **IAM Permissions**: The invalidator service must have appropriate resource-based policies
- **CloudFront Distributions**: Must exist and be properly configured to use the S3 bucket as an origin

### Internal Dependencies

- **S3 Bucket**: Must be created before Lambda permission can reference its ARN
- **Conditions**: Must be defined before being used in resource properties
- **Parameters**: Must be defined before being referenced in conditions and resources

## Deployment Considerations

### Deployment Order

1. Deploy invalidator service stack (if not already deployed)
2. Tag invalidator service with `AllowInvalidationEvents=true`
3. Deploy S3 storage stack with InvalidatorArn parameter
4. Verify S3 event notifications are configured correctly
5. Test by uploading/deleting objects and monitoring invalidator service logs

### Migration from v1 to v2

For existing deployments using the v1 template:

1. **Deploy Invalidator Service**: Create a separate stack with the invalidator Lambda function
2. **Update Stack**: Update existing S3 stack to use v2 template with InvalidatorArn parameter
3. **Verify**: Confirm event notifications are working correctly
4. **Cleanup**: Remove old CloudFrontInvalidator resources (handled automatically by CloudFormation)

### Rollback Strategy

If issues occur during deployment:

1. **CloudFormation Rollback**: CloudFormation will automatically roll back failed stack updates
2. **Manual Rollback**: Update stack back to v1 template if v2 causes issues
3. **Event Notification Removal**: Set InvalidatorArn to empty string to disable event notifications

## Security Considerations

### Least Privilege Principle

- S3 bucket only grants invoke permission to specific external service ARN
- SourceArn and SourceAccount conditions restrict invocation to specific S3 bucket
- Tag-based permissions allow fine-grained access control

### Data Protection

- S3 bucket maintains encryption at rest (AES256)
- S3 bucket blocks all public access
- Secure transport enforced via bucket policy (DenyNonSecureTransportAccess)

### Audit and Monitoring

- CloudTrail logs all S3 API calls
- External invalidator service should implement its own logging and monitoring
- S3 event notification failures should be monitored via CloudWatch

## Performance Considerations

### S3 Event Notification Latency

- S3 event notifications are typically delivered within seconds
- High-volume buckets may experience slight delays during peak times
- External service should be designed to handle burst traffic

### Cost Optimization

- No Lambda function in this stack reduces costs
- Centralized invalidator service reduces duplication across multiple buckets
- S3 event notifications are free; costs are incurred by the external service

## Maintenance and Support

### Template Updates

- Version number should be incremented for any changes
- Backward compatibility should be maintained for parameter structure
- New features should use conditional logic to avoid breaking existing deployments

### Documentation

- Template comments should be kept up-to-date
- README or separate documentation should explain tag-based permission model
- Examples should be provided for common deployment scenarios
