# Design Document: AWS Managed Cache Policies for Network Template

## Overview

This design adds support for AWS managed cache policies to the template-network-route53-cloudfront-s3-apigw.yml template. Currently, the template always creates two custom cache policies (`CloudFrontCachePolicyStatic` and `CloudFrontCachePolicyApi`). This enhancement allows users to choose between AWS managed policies (CachingOptimized, CachingDisabled, CachingOptimizedForUncompressedObjects, Elemental-MediaPackage), the existing custom default policies, or custom ARN-based policies.

The design includes environment-based overrides where DEV and TEST environments always use CachingDisabled regardless of parameter values, ensuring fresh content during development and testing.

## Architecture

### Cache Policy Selection Flow

```
User selects cache policy type via parameters
    ↓
Template evaluates DeployEnvironment
    ↓
    ├─ If DEV or TEST → Force CachingDisabled for both origins
    └─ If PROD → Use selected policy type
        ↓
        ├─ CachingOptimized → Use managed policy ID
        ├─ CachingDisabled → Use managed policy ID
        ├─ CachingOptimizedForUncompressedObjects → Use managed policy ID
        ├─ Elemental-MediaPackage → Use managed policy ID
        ├─ CustomDefault → Create and reference custom policy resource
        └─ CustomArn → Use provided ARN from parameter
```

### Template Modifications

The template will be modified in the following sections:

1. **Metadata Section**: Add cache policy parameters to a new "Cache Policies" parameter group
2. **Parameters Section**: Add four new parameters for cache policy selection
3. **Mappings Section**: Add CachePolicyIds mapping for managed policy ID lookup
4. **Conditions Section**: Add conditions for policy type detection and custom resource creation
5. **Resources Section**: 
   - Add conditions to custom cache policy resources
   - Add documentation comments with `>!` notation
   - Update CloudFront distribution to use resolved cache policy IDs
6. **Outputs Section**: No changes required

## Components and Interfaces

### Parameter Definitions

**CloudFrontStaticCachePolicy Parameter:**
```yaml
CloudFrontStaticCachePolicy:
  Type: String
  Description: "Cache policy for static S3 origin. CachingOptimized: Recommended for most use cases. CachingDisabled: Disables caching. CachingOptimizedForUncompressedObjects: Optimized for uncompressed content. Elemental-MediaPackage: For AWS Elemental MediaPackage origins. CustomDefault: Use template's default custom policy. CustomArn: Use custom ARN (requires CloudFrontStaticCustomCachePolicyArn). Note: DEV and TEST environments always use CachingDisabled regardless of this setting."
  Default: CachingOptimized
  AllowedValues:
    - CachingOptimized
    - CachingDisabled
    - CachingOptimizedForUncompressedObjects
    - Elemental-MediaPackage
    - CustomDefault
    - CustomArn
```

**CloudFrontStaticCustomCachePolicyArn Parameter:**
```yaml
CloudFrontStaticCustomCachePolicyArn:
  Type: String
  Description: "Custom cache policy ARN for static origin. Only used when CloudFrontStaticCachePolicy is set to CustomArn. Leave empty if not using custom ARN."
  Default: ""
  AllowedPattern: "^arn:aws:cloudfront::[0-9]{12}:cache-policy/[a-zA-Z0-9-]+$|^$"
  ConstraintDescription: "Must be a valid CloudFront cache policy ARN or empty."
```

**CloudFrontApiCachePolicy Parameter:**
```yaml
CloudFrontApiCachePolicy:
  Type: String
  Description: "Cache policy for API Gateway origin. CachingOptimized: Recommended for most use cases. CachingDisabled: Disables caching (recommended for APIs). CachingOptimizedForUncompressedObjects: Optimized for uncompressed content. Elemental-MediaPackage: For AWS Elemental MediaPackage origins. CustomDefault: Use template's default custom policy. CustomArn: Use custom ARN (requires CloudFrontApiCustomCachePolicyArn). Note: DEV and TEST environments always use CachingDisabled regardless of this setting."
  Default: CachingDisabled
  AllowedValues:
    - CachingOptimized
    - CachingDisabled
    - CachingOptimizedForUncompressedObjects
    - Elemental-MediaPackage
    - CustomDefault
    - CustomArn
```

**CloudFrontApiCustomCachePolicyArn Parameter:**
```yaml
CloudFrontApiCustomCachePolicyArn:
  Type: String
  Description: "Custom cache policy ARN for API origin. Only used when CloudFrontApiCachePolicy is set to CustomArn. Leave empty if not using custom ARN."
  Default: ""
  AllowedPattern: "^arn:aws:cloudfront::[0-9]{12}:cache-policy/[a-zA-Z0-9-]+$|^$"
  ConstraintDescription: "Must be a valid CloudFront cache policy ARN or empty."
```

### Condition Definitions

**Environment and Policy Type Conditions:**
```yaml
# Environment-based conditions
IsProduction: !Equals [!Ref DeployEnvironment, PROD]

# Static cache policy type conditions (only for special cases)
StaticCachePolicyIsCustomDefault: !Equals [!Ref CloudFrontStaticCachePolicy, CustomDefault]
StaticCachePolicyIsCustomArn: !Equals [!Ref CloudFrontStaticCachePolicy, CustomArn]

# API cache policy type conditions (only for special cases)
ApiCachePolicyIsCustomDefault: !Equals [!Ref CloudFrontApiCachePolicy, CustomDefault]
ApiCachePolicyIsCustomArn: !Equals [!Ref CloudFrontApiCachePolicy, CustomArn]

# Custom resource creation conditions
CreateCustomStaticCachePolicy: !And
  - !Condition HasStaticOrigin
  - !Condition IsProduction
  - !Condition StaticCachePolicyIsCustomDefault

CreateCustomApiCachePolicy: !And
  - !Condition IsProduction
  - !Condition ApiCachePolicyIsCustomDefault
```

Note: We only need conditions for CustomDefault and CustomArn cases. The managed policy IDs are resolved using the Mappings section with `!FindInMap`, which eliminates the need for individual conditions for each managed policy type.

### AWS Managed Cache Policy IDs

The following managed policy IDs will be used:

| Policy Name | Policy ID |
|-------------|-----------|
| CachingOptimized | 658327ea-f89d-4fab-a63d-7e88639e58f6 |
| CachingDisabled | 4135ea2d-6df8-44a3-9df3-4b5a84be39ad |
| CachingOptimizedForUncompressedObjects | b2884449-e4de-46a7-ac36-70bc7f1ddd6d |
| Elemental-MediaPackage | 08627262-05a9-4f76-9ded-b50ca2e3a84f |

### Mappings Section

A new Mappings section will be added to the template to map cache policy types to their managed policy IDs:

```yaml
Mappings:
  CachePolicyIds:
    CachingOptimized:
      Id: 658327ea-f89d-4fab-a63d-7e88639e58f6
    CachingDisabled:
      Id: 4135ea2d-6df8-44a3-9df3-4b5a84be39ad
    CachingOptimizedForUncompressedObjects:
      Id: b2884449-e4de-46a7-ac36-70bc7f1ddd6d
    Elemental-MediaPackage:
      Id: 08627262-05a9-4f76-9ded-b50ca2e3a84f
```

### Cache Policy Resolution Logic

The cache policy ID will be resolved using mappings and conditional logic:

**Static Cache Policy Resolution:**
```yaml
!If
  - IsProduction
  - !If
      - StaticCachePolicyIsCustomDefault
      - !Ref CloudFrontCachePolicyStatic
      - !If
          - StaticCachePolicyIsCustomArn
          - !Ref CloudFrontStaticCustomCachePolicyArn
          - !FindInMap [CachePolicyIds, !Ref CloudFrontStaticCachePolicy, Id]
  - !FindInMap [CachePolicyIds, CachingDisabled, Id]  # Force CachingDisabled for non-PROD
```

**API Cache Policy Resolution:**
```yaml
!If
  - IsProduction
  - !If
      - ApiCachePolicyIsCustomDefault
      - !Ref CloudFrontCachePolicyApi
      - !If
          - ApiCachePolicyIsCustomArn
          - !Ref CloudFrontApiCustomCachePolicyArn
          - !FindInMap [CachePolicyIds, !Ref CloudFrontApiCachePolicy, Id]
  - !FindInMap [CachePolicyIds, CachingDisabled, Id]  # Force CachingDisabled for non-PROD
```

This approach is cleaner and more maintainable than deeply nested if statements. The mapping provides a clear lookup table for managed policy IDs, and the conditional logic only needs to handle the special cases (CustomDefault, CustomArn, and environment override).

### Resource Modifications

**CloudFrontCachePolicyStatic Resource:**
```yaml
CloudFrontCachePolicyStatic:
  Type: AWS::CloudFront::CachePolicy
  Condition: CreateCustomStaticCachePolicy
  Properties:
    # ... existing properties ...
```

**CloudFrontCachePolicyApi Resource:**
```yaml
CloudFrontCachePolicyApi:
  Type: AWS::CloudFront::CachePolicy
  Condition: CreateCustomApiCachePolicy
  Properties:
    # ... existing properties ...
```

**CloudFrontDistribution Resource:**

The distribution will be updated to use the resolved cache policy IDs. Documentation comments with `>!` notation will be added:

```yaml
CloudFrontDistribution:
  Type: AWS::CloudFront::Distribution
  Condition: CreateDistribution
  Properties:
    DistributionConfig:
      # ... other properties ...
      
      # >! Cache Policy Selection
      # >! This template supports AWS managed cache policies and custom policies.
      # >! For more information, see: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-cache-policies.html
      # >! Note: DEV and TEST environments always use CachingDisabled regardless of parameter settings.
      
      DefaultCacheBehavior:
        CachePolicyId: !If 
          - StaticOriginIsRoot
          - # Static cache policy resolution (using !FindInMap and conditionals)
          - # API cache policy resolution (using !FindInMap and conditionals)
        # ... other properties ...
      
      CacheBehaviors:
        - !If 
          - HasRouteForStaticOrigin
          - PathPattern: !Sub "/${PathStatic}/*"
            CachePolicyId: # Static cache policy resolution
            # ... other properties ...
          - !Ref AWS::NoValue
        - !If 
          - HasRouteForApiInCloudFront
          - PathPattern: !Sub "/${PathApi}/*"
            CachePolicyId: # API cache policy resolution
            # ... other properties ...
          - !Ref AWS::NoValue
```

### Metadata Organization

```yaml
Metadata:
  AWS::CloudFormation::Interface:
    ParameterGroups:
      # ... existing groups ...
      
      - Label:
          default: "Cache Policies"
        Parameters:
          - CloudFrontStaticCachePolicy
          - CloudFrontStaticCustomCachePolicyArn
          - CloudFrontApiCachePolicy
          - CloudFrontApiCustomCachePolicyArn
      
      # ... remaining groups ...
```

## Data Models

### Parameter Value Combinations

**Valid Static Cache Policy Configurations:**
- `CloudFrontStaticCachePolicy: CachingOptimized` (default)
- `CloudFrontStaticCachePolicy: CachingDisabled`
- `CloudFrontStaticCachePolicy: CachingOptimizedForUncompressedObjects`
- `CloudFrontStaticCachePolicy: Elemental-MediaPackage`
- `CloudFrontStaticCachePolicy: CustomDefault`
- `CloudFrontStaticCachePolicy: CustomArn` + `CloudFrontStaticCustomCachePolicyArn: arn:aws:cloudfront::123456789012:cache-policy/abc123`

**Valid API Cache Policy Configurations:**
- `CloudFrontApiCachePolicy: CachingDisabled` (default)
- `CloudFrontApiCachePolicy: CachingOptimized`
- `CloudFrontApiCachePolicy: CachingOptimizedForUncompressedObjects`
- `CloudFrontApiCachePolicy: Elemental-MediaPackage`
- `CloudFrontApiCachePolicy: CustomDefault`
- `CloudFrontApiCachePolicy: CustomArn` + `CloudFrontApiCustomCachePolicyArn: arn:aws:cloudfront::123456789012:cache-policy/xyz789`

### Environment-Based Overrides

| DeployEnvironment | User Selection | Actual Policy Used |
|-------------------|----------------|-------------------|
| DEV | Any | CachingDisabled |
| TEST | Any | CachingDisabled |
| PROD | CachingOptimized | CachingOptimized |
| PROD | CachingDisabled | CachingDisabled |
| PROD | CustomDefault | Custom Policy |
| PROD | CustomArn | Custom ARN |

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Conditional static cache policy resource creation
*For any* template configuration, the `CloudFrontCachePolicyStatic` resource should be created if and only if `HasStaticOrigin` is true AND `DeployEnvironment` is `PROD` AND `CloudFrontStaticCachePolicy` is `CustomDefault`.
**Validates: Requirements 4.1, 4.2**

### Property 2: Conditional API cache policy resource creation
*For any* template configuration, the `CloudFrontCachePolicyApi` resource should be created if and only if `DeployEnvironment` is `PROD` AND `CloudFrontApiCachePolicy` is `CustomDefault`.
**Validates: Requirements 4.3, 4.4**

### Property 3: Static cache policy ARN resolution
*For any* valid combination of `DeployEnvironment` and `CloudFrontStaticCachePolicy` parameters, the resolved static cache policy ID should match the expected value: CachingDisabled (4135ea2d-6df8-44a3-9df3-4b5a84be39ad) for non-PROD environments, or the appropriate managed policy ID, custom resource reference, or custom ARN for PROD environments based on the selected policy type.
**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 11.1, 11.2**

### Property 4: API cache policy ARN resolution
*For any* valid combination of `DeployEnvironment` and `CloudFrontApiCachePolicy` parameters, the resolved API cache policy ID should match the expected value: CachingDisabled (4135ea2d-6df8-44a3-9df3-4b5a84be39ad) for non-PROD environments, or the appropriate managed policy ID, custom resource reference, or custom ARN for PROD environments based on the selected policy type.
**Validates: Requirements 5.7, 5.8, 5.9, 5.10, 5.11, 5.12, 11.1, 11.2**

### Property 5: Cache policy application to distribution
*For any* CloudFront distribution configuration with static and/or API origins, the cache policy IDs applied to the default cache behavior and cache behaviors should match the resolved cache policy IDs for the respective origin types.
**Validates: Requirements 6.1, 6.2, 6.3, 6.4**

### Property 6: Environment-based cache policy override
*For any* template configuration where `DeployEnvironment` is `DEV` or `TEST`, both static and API cache policies should resolve to CachingDisabled (4135ea2d-6df8-44a3-9df3-4b5a84be39ad) regardless of the `CloudFrontStaticCachePolicy` and `CloudFrontApiCachePolicy` parameter values.
**Validates: Requirements 11.1, 11.2, 11.3**

### Property 7: Custom ARN validation
*For any* string value provided as `CloudFrontStaticCustomCachePolicyArn` or `CloudFrontApiCustomCachePolicyArn`, CloudFormation should accept it if and only if it matches the pattern `^arn:aws:cloudfront::[0-9]{12}:cache-policy/[a-zA-Z0-9-]+$` or is an empty string, and reject it with a constraint error message otherwise.
**Validates: Requirements 9.1, 9.2, 9.3, 9.4**

## Error Handling

### Invalid Parameter Values

The template uses CloudFormation's built-in parameter validation to handle errors:

1. **Invalid cache policy type**: CloudFormation will reject stack creation/update if a value not in AllowedValues is provided
2. **Invalid custom ARN format**: CloudFormation will reject stack creation/update with the constraint error message
3. **Empty custom ARN when CustomArn selected**: The template will use an empty string, which may cause CloudFormation to fail during stack creation with a more specific error about invalid cache policy ID

### Missing Custom ARN

If a user selects `CustomArn` but doesn't provide a value in the corresponding custom ARN parameter:
- The parameter will default to an empty string
- CloudFormation will attempt to use an empty string as the cache policy ID
- CloudFormation will fail with an error indicating an invalid cache policy ID
- The user should update the stack with a valid ARN

This is acceptable behavior as it provides clear feedback about the missing required value.

### Custom Resource Creation in Non-PROD

The conditions ensure that custom cache policy resources are never created in DEV or TEST environments, even if `CustomDefault` is selected. This prevents unnecessary resource creation and ensures consistent behavior across environments.

### Conditional Logic Errors

The nested `!If` statements are complex but deterministic:
- Each condition is mutually exclusive (a parameter can only have one value)
- The final fallback in each nested structure handles the remaining case
- Environment-based override is the outermost condition, ensuring it takes precedence

## Testing Strategy

### Unit Tests

Unit tests should focus on specific examples and edge cases:

1. **Template Structure Tests**:
   - Verify all four cache policy parameters exist with correct properties
   - Verify all cache policy type conditions exist
   - Verify custom resource creation conditions exist
   - Verify Metadata includes cache policy parameters in correct group
   - Verify parameter descriptions include environment override note

2. **Edge Case Tests**:
   - Default parameter values (CachingOptimized for static, CachingDisabled for API)
   - Each managed policy type selection
   - CustomDefault selection
   - CustomArn selection with valid ARN
   - Empty custom ARN parameters

3. **Environment Override Tests**:
   - DEV environment with various policy selections
   - TEST environment with various policy selections
   - PROD environment with various policy selections

4. **Documentation Comment Tests**:
   - Verify `>!` notation comments exist in CloudFront distribution resource
   - Verify comments reference AWS documentation
   - Verify comments list all managed policy options

### Property-Based Tests

Following testing-guidelines.md, property-based tests should be minimal and focused on core validation logic:

**Recommended Property Tests** (minimal set):

1. **Custom ARN Validation Property**:
   - Generate random strings (valid and invalid ARNs)
   - Verify CloudFormation accepts/rejects according to the pattern
   - Run with 20 iterations

2. **Cache Policy Resolution Property**:
   - Generate random valid parameter combinations (DeployEnvironment, policy types)
   - Verify resolved cache policy IDs match expected values
   - Run with 20 iterations

**Property Tests to Skip** (covered by unit tests):
- Conditional resource creation (simple boolean logic, well-covered by unit tests)
- Cache policy application (straightforward mapping, better as unit test)
- Environment override (specific cases, better as unit tests)

### Integration Tests

Integration tests should verify end-to-end workflows:

1. **Template Deployment Tests**:
   - Deploy template with managed policies in PROD
   - Deploy template with CustomDefault in PROD
   - Deploy template with CustomArn in PROD
   - Deploy template in DEV/TEST environments
   - Verify CloudFront distribution is created correctly in all cases

2. **Cache Behavior Tests** (optional, requires AWS resources):
   - Deploy with CachingOptimized
   - Deploy with CachingDisabled
   - Verify caching behavior matches policy selection

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
   - Add "Cache Policies" parameter group section
   - Document all four cache policy parameters with tables
   - Include examples of each policy type selection
   - Explain environment-based override behavior

2. **Resources Section**:
   - Update CloudFrontCachePolicyStatic documentation to mention conditional creation
   - Update CloudFrontCachePolicyApi documentation to mention conditional creation
   - Update CloudFrontDistribution documentation to explain cache policy selection

3. **Examples Section**:
   - Provide example configurations for each managed policy type
   - Provide example configuration with CustomDefault
   - Provide example configuration with CustomArn
   - Show environment-based override examples

4. **AWS Managed Cache Policies Section** (new):
   - Create a dedicated section explaining AWS managed cache policies
   - Link to AWS documentation
   - Provide guidance on when to use each policy type
   - Explain the benefits of managed policies vs custom policies

### CHANGELOG Update

The CHANGELOG.md must be updated with:

```markdown
### Added
- **AWS Managed Cache Policy Support** [Spec: 0-0-29-network-add-managed-cache-policies](../.kiro/specs/0-0-29-network-add-managed-cache-policies/)
  - Network: template-network-route53-cloudfront-s3-apigw.yml v0.0.16 - Added support for AWS managed cache policies with environment-based overrides
```

## Implementation Notes

### Version Increment

The current template version is v0.0.15. Since PATCH = 15 (> 0), the version should be incremented to v0.0.16 as the first step of implementation.

### Backward Compatibility

This change is fully backward compatible:
- New parameters have default values that preserve existing behavior
- Default for static is CachingOptimized (similar to existing custom policy for PROD)
- Default for API is CachingDisabled (similar to existing custom policy)
- Existing stacks can be updated without providing new parameters
- No breaking changes

### CloudFormation Intrinsic Function Complexity

The use of mappings with `!FindInMap` significantly simplifies the cache policy resolution logic:
- Mappings provide a clean lookup table for managed policy IDs
- Conditional logic only handles special cases (CustomDefault, CustomArn, environment override)
- Much more maintainable than deeply nested if statements
- Easy to add new managed policies in the future
- Clear separation between policy ID lookup and conditional logic

### AWS Managed Policy Benefits

Using AWS managed policies provides several benefits:
- No custom resources to create and manage
- AWS maintains and updates the policies
- Reduced stack complexity
- Faster stack creation/update times
- Industry-standard caching configurations

### Future Enhancements

Potential future enhancements (not in scope for this spec):
- Add support for custom response headers policies
- Add support for origin request policies
- Create a library of recommended policy combinations for common use cases
- Add CloudWatch metrics for cache hit rates
