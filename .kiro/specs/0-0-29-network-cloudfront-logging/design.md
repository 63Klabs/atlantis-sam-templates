# Design Document: CloudFront Logging for Network Template

## Overview

This design adds optional CloudFront logging functionality to the template-network-route53-cloudfront-s3-apigw.yml template. The implementation uses a conditional approach where logging is enabled only when a valid S3 bucket name is provided via the `S3LogBucketName` parameter. This maintains backward compatibility while providing users the flexibility to enable logging when needed.

The design also includes the creation of a new steering document that standardizes parameter naming and definitions across all CloudFormation templates in the repository.

## Architecture

### Template Modifications

The template will be modified in the following sections:

1. **Metadata Section**: Add `S3LogBucketName` to a "Supporting Resources" parameter group
2. **Parameters Section**: Add the `S3LogBucketName` parameter with validation
3. **Conditions Section**: Add `HasLogBucket` condition to determine if logging should be enabled
4. **Resources Section**: Uncomment and configure the Logging property in the CloudFrontDistribution resource
5. **Outputs Section**: Add outputs for log bucket name and prefix when logging is enabled

### Conditional Logic Flow

```
User provides S3LogBucketName parameter
    ↓
Template evaluates HasLogBucket condition
    ↓
    ├─ If empty string → HasLogBucket = false → No logging configuration
    └─ If valid bucket name → HasLogBucket = true → Enable logging with prefix
```

### Logging Configuration Structure

When enabled, the CloudFront distribution will include:

```yaml
Logging:
  IncludeCookies: 'false'
  Bucket: !Sub "${S3LogBucketName}.s3.amazonaws.com"
  Prefix: !Sub "cloudfront/${Prefix}-${ProjectId}-${StageId}"
```

## Components and Interfaces

### Parameter Definition

**S3LogBucketName Parameter:**
- Type: String
- Default: "" (empty string)
- AllowedPattern: `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$|^$`
- Description: "The name of the S3 bucket used for CloudFront logging. Leave empty to disable logging. Must be a valid S3 bucket name (without .s3.amazonaws.com suffix)."
- ConstraintDescription: "Must be a valid S3 bucket name or empty. Must be between 3 and 63 characters long. Lower case alphanumeric and dashes. Must start and end with a letter or number."

### Condition Definition

**HasLogBucket Condition:**
```yaml
HasLogBucket: !Not
  - !Equals
    - !Ref S3LogBucketName
    - ''
```

This condition evaluates to true when S3LogBucketName is not an empty string.

### Resource Modification

**CloudFrontDistribution Resource:**

The Logging property will be added conditionally using CloudFormation intrinsic functions:

```yaml
Logging: !If
  - HasLogBucket
  - IncludeCookies: 'false'
    Bucket: !Sub "${S3LogBucketName}.s3.amazonaws.com"
    Prefix: !Sub "cloudfront/${Prefix}-${ProjectId}-${StageId}"
  - !Ref AWS::NoValue
```

### Metadata Organization

The parameter will be added to the Metadata section in a "Supporting Resources" parameter group. If this group doesn't exist, it will be created. The group will be positioned logically after "Deployment Environment" and before routing configuration groups.

```yaml
Metadata:
  AWS::CloudFormation::Interface:
    ParameterGroups:
      # ... existing groups ...
      - Label:
          default: "Supporting Resources"
        Parameters:
          - S3LogBucketName
      # ... remaining groups ...
```

### Output Definitions

Two conditional outputs will be added:

1. **CloudFrontLogBucket**: The S3 bucket name used for logging
2. **CloudFrontLogPrefix**: The complete prefix used for log files

Both outputs will use the `HasLogBucket` condition.

## Data Models

### Parameter Value Format

- **Valid bucket name**: `my-log-bucket`, `acme-logs-prod`, `cloudfront-logs-123`
- **Invalid bucket name**: `MyBucket` (uppercase), `bucket_name` (underscore), `ab` (too short)
- **Disabled logging**: `` (empty string)

### Log Prefix Format

The log prefix follows the pattern: `cloudfront/{Prefix}-{ProjectId}-{StageId}`

Examples:
- `cloudfront/acme-myapp-prod`
- `cloudfront/ws-api-test`
- `cloudfront/devops-website-dev`

This format ensures logs are organized by:
1. Service type (cloudfront)
2. Application ownership (Prefix-ProjectId)
3. Deployment stage (StageId)

## Steering Document: Parameter Standards

A new steering document will be created at `.kiro/steering/template-parameter-standards.md` that defines standard parameters used across CloudFormation templates.

### Document Structure

The steering document will include:

1. **Overview**: Purpose and scope of parameter standards
2. **Standard Parameters**: Detailed definitions for each common parameter
3. **Parameter Groups**: Standard Metadata parameter group labels
4. **Validation Patterns**: Reusable regex patterns for common validations
5. **Usage Guidelines**: When and how to use each parameter

### Standard Parameters to Document

1. **Prefix**
   - Metadata Group: "Application Resource Naming"
   - Type: String
   - Pattern: `^[a-z][a-z0-9-]{0,6}[a-z0-9]$`
   - Length: 2-8 characters

2. **ProjectId**
   - Metadata Group: "Application Resource Naming"
   - Type: String
   - Pattern: `^[a-z][a-z0-9-]{0,24}[a-z0-9]$`
   - Length: 2-26 characters

3. **StageId**
   - Metadata Group: "Application Resource Naming"
   - Type: String
   - Pattern: `^[a-z][a-z0-9-]{0,6}[a-z0-9]$`
   - Length: 2-8 characters

4. **S3LogBucketName**
   - Metadata Group: "Supporting Resources"
   - Type: String
   - Pattern: `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$|^$`
   - Length: 3-63 characters (or empty)

5. **S3BucketNameOrgPrefix**
   - Metadata Group: "Application Resource Naming"
   - Type: String
   - Pattern: `^[a-z0-9][a-z0-9-]{1,18}[a-z0-9]$|^$`
   - Length: 3-20 characters (or empty)

6. **DeployEnvironment**
   - Metadata Group: "Deployment Environment"
   - Type: String
   - AllowedValues: DEV, TEST, PROD

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property Reflection

After analyzing all acceptance criteria, I've identified the following testable properties and redundancies:

**Redundancies Identified:**
- Criteria 1.3 and 3.4 both test that empty bucket name results in no logging configuration - these can be combined into one property
- Criteria 2.1, 2.2, 2.3, and 2.4 all test different aspects of bucket name validation - these can be combined into one comprehensive validation property
- Criteria 1.4, 3.1, and 3.3 all test logging configuration when enabled - these can be combined into one property that validates the complete logging configuration

**Properties to Implement:**

1. **Logging disabled when bucket name empty** (combines 1.3, 3.4)
2. **Bucket name validation** (combines 2.1, 2.2, 2.3, 2.4, 2.6)
3. **Logging configuration format** (combines 1.4, 3.1, 3.3)
4. **Conditional outputs** (combines 6.2, 6.3)
5. **Template structure validation** (examples for 1.1, 1.2, 4.1, 4.2, 5.1, 5.2)
6. **Steering document structure** (examples for 8.1-8.5)
7. **Parameter consistency** (8.8)
8. **Existing conditions compatibility** (5.3)

### Correctness Properties

Property 1: Logging disabled for empty bucket name
*For any* CloudFormation template configuration where S3LogBucketName is an empty string, the rendered CloudFront distribution resource should not contain a Logging property.
**Validates: Requirements 1.3, 3.4**

Property 2: Bucket name validation
*For any* string value, if it is provided as S3LogBucketName, then CloudFormation should accept it if and only if it matches the pattern `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$` or is an empty string, and reject it with a constraint error message otherwise.
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.6**

Property 3: Logging configuration format when enabled
*For any* valid S3LogBucketName (non-empty), Prefix, ProjectId, and StageId combination, when the template is rendered, the CloudFront distribution Logging property should have IncludeCookies set to false, Bucket set to `{S3LogBucketName}.s3.amazonaws.com`, and Prefix set to `cloudfront/{Prefix}-{ProjectId}-{StageId}`.
**Validates: Requirements 1.4, 3.1, 3.3**

Property 4: Conditional outputs presence
*For any* template configuration where S3LogBucketName is non-empty, the template outputs should include CloudFrontLogBucket and CloudFrontLogPrefix outputs, and for any configuration where S3LogBucketName is empty, these outputs should not be present.
**Validates: Requirements 6.2, 6.3**

Property 5: Existing conditions compatibility
*For any* existing condition in the template (IsProduction, IsProdStage, HasStaticOrigin, etc.), after adding the HasLogBucket condition, all existing conditions should continue to evaluate correctly with their original logic unchanged.
**Validates: Requirements 5.3**

Property 6: Parameter consistency with steering document
*For any* standard parameter defined in the steering document (Prefix, ProjectId, StageId, S3LogBucketName, S3BucketNameOrgPrefix), if that parameter exists in the template, then its Type, AllowedPattern, MinLength, MaxLength, and ConstraintDescription should match the definition in the steering document.
**Validates: Requirements 8.8**

## Error Handling

### Invalid Parameter Values

The template uses CloudFormation's built-in parameter validation to handle errors:

1. **Invalid bucket name format**: CloudFormation will reject stack creation/update with the constraint error message
2. **Empty string**: Explicitly allowed and results in logging being disabled
3. **Bucket name too short/long**: Caught by the AllowedPattern regex

### Missing Dependencies

The template does not create the S3 log bucket. Users must:
1. Create the S3 bucket before deploying the template
2. Configure the bucket policy to allow CloudFront to write logs
3. Ensure the bucket is in a region that supports CloudFront logging

The template documentation should clearly state these prerequisites.

### Conditional Logic Errors

The `HasLogBucket` condition is straightforward and has minimal error potential:
- If S3LogBucketName is empty → condition is false → no logging
- If S3LogBucketName is non-empty → condition is true → logging enabled

The use of `!Ref AWS::NoValue` ensures that when the condition is false, the Logging property is completely omitted from the CloudFront distribution, which is the correct CloudFormation behavior.

## Testing Strategy

### Unit Tests

Unit tests should focus on specific examples and edge cases:

1. **Template Structure Tests**:
   - Verify S3LogBucketName parameter exists with correct properties
   - Verify HasLogBucket condition exists with correct logic
   - Verify Metadata includes S3LogBucketName in "Supporting Resources" group
   - Verify conditional outputs exist

2. **Edge Case Tests**:
   - Empty string for S3LogBucketName (logging disabled)
   - Minimum length bucket name (3 characters)
   - Maximum length bucket name (63 characters)
   - Bucket name with dashes in valid positions

3. **Steering Document Tests**:
   - Verify steering document file exists
   - Verify all required parameters are documented
   - Verify each parameter has required fields (Type, Pattern, Description, Metadata Group)

### Property-Based Tests

Property-based tests should verify universal properties across all inputs. Given the testing guidelines steering document that prioritizes fast-running unit tests for this repository, property-based tests should be minimal and focused on core validation logic.

**Recommended Property Tests** (minimal set):

1. **Bucket Name Validation Property**:
   - Generate random strings (valid and invalid bucket names)
   - Verify CloudFormation accepts/rejects according to the pattern
   - This provides unique value as it tests the regex pattern comprehensively
   - Run with 20 iterations (per testing-guidelines.md)

2. **Logging Configuration Format Property**:
   - Generate random valid parameter combinations
   - Verify logging configuration format is always correct when enabled
   - This validates the template logic across parameter space
   - Run with 20 iterations

**Property Tests to Skip** (covered by unit tests):
- Conditional outputs (simple boolean logic, well-covered by unit tests)
- Existing conditions compatibility (regression test, better as unit test)
- Parameter consistency (comparison test, better as unit test)

### Integration Tests

Integration tests should verify end-to-end workflows:

1. **Template Deployment Tests**:
   - Deploy template with logging enabled (requires test S3 bucket)
   - Deploy template with logging disabled
   - Verify CloudFront distribution is created correctly in both cases

2. **Log Delivery Tests** (optional, requires AWS resources):
   - Deploy with logging enabled
   - Generate CloudFront traffic
   - Verify logs appear in S3 bucket with correct prefix

### Test Organization

Following testing-guidelines.md:
- Unit tests should complete in < 1 second per test
- Property tests should be in separate files for easy identification
- Total test suite should complete in under 30 seconds
- Focus on comprehensive unit test coverage for CI/CD confidence

## Documentation Updates

### Template Documentation

The template-network-route53-cloudfront-s3-apigw-README.md file must be updated to include:

1. **Parameters Section**:
   - Add S3LogBucketName parameter documentation under "Supporting Resources" group
   - Include parameter table with Type, Default, Allowed Pattern, and Constraint Description
   - Provide examples of valid bucket names

2. **Resources Section**:
   - Update CloudFrontDistribution documentation to mention optional logging
   - Note that logging is conditional based on S3LogBucketName parameter

3. **Outputs Section**:
   - Add CloudFrontLogBucket output documentation (conditional)
   - Add CloudFrontLogPrefix output documentation (conditional)

4. **Prerequisites Section**:
   - Add note about S3 log bucket requirements
   - Link to AWS documentation on CloudFront logging setup
   - Mention bucket policy requirements

5. **Examples Section**:
   - Provide example parameter configuration with logging enabled
   - Provide example parameter configuration with logging disabled

### Steering Document Creation

A new file `.kiro/steering/template-parameter-standards.md` must be created with:

1. **Overview**: Purpose and scope
2. **Standard Parameters**: Detailed definitions for each common parameter
3. **Parameter Groups**: Standard Metadata labels
4. **Validation Patterns**: Reusable regex patterns
5. **Usage Guidelines**: When and how to use each parameter
6. **Examples**: Sample parameter definitions

### CHANGELOG Update

The CHANGELOG.md must be updated with:

```markdown
### Added
- **CloudFront Logging Support** [Spec: 0-0-29-network-cloudfront-logging](../.kiro/specs/0-0-29-network-cloudfront-logging/)
  - Network: template-network-route53-cloudfront-s3-apigw.yml v0.0.14 - Added optional CloudFront logging with S3LogBucketName parameter
  - Steering Document: template-parameter-standards.md - Standardized parameter naming and definitions across templates
```

## Implementation Notes

### Version Increment

The current template version is v0.0.13. Since PATCH = 13 (> 0), the version should be incremented to v0.0.14 as the first step of implementation.

### Backward Compatibility

This change is fully backward compatible:
- New parameter has a default value (empty string)
- Existing stacks can be updated without providing the new parameter
- No existing functionality is modified
- No breaking changes

### CloudFront Logging Best Practices

The design follows AWS best practices:
- IncludeCookies set to false (reduces log size, cookies not typically needed)
- Organized prefix structure for easy log management
- Bucket name validation prevents common errors
- Optional nature allows users to control costs (logging incurs S3 storage costs)

### Future Enhancements

Potential future enhancements (not in scope for this spec):
- Add parameter for custom log prefix
- Add parameter for IncludeCookies option
- Add parameter for log retention period
- Create a companion template for S3 log bucket with proper policies
