# Requirements Document

## Introduction

This specification adds support for AWS managed cache policies to the network infrastructure template (template-network-route53-cloudfront-s3-apigw.yml). Currently, the template creates two custom cache policies for static and API origins. This enhancement allows users to choose between AWS managed policies, custom default policies, or custom ARN-based policies, providing greater flexibility and reducing resource creation when managed policies are sufficient.

## Glossary

- **CloudFront_Distribution**: The AWS CloudFront distribution resource that serves static content and/or API Gateway endpoints
- **Cache_Policy**: A CloudFront cache policy that defines caching behavior including TTL, query strings, headers, and cookies
- **Managed_Cache_Policy**: An AWS-provided cache policy with predefined caching behavior
- **Custom_Cache_Policy**: A user-defined cache policy created as a CloudFormation resource
- **Static_Origin**: The S3 bucket origin serving static content
- **API_Origin**: The API Gateway origin serving dynamic API content
- **Template**: The CloudFormation template file template-network-route53-cloudfront-s3-apigw.yml

## Requirements

### Requirement 1: Static Origin Cache Policy Selection

**User Story:** As a DevOps engineer, I want to choose between AWS managed cache policies and custom policies for my static origin, so that I can optimize caching behavior without creating unnecessary custom resources.

#### Acceptance Criteria

1. THE Template SHALL provide a parameter named `CloudFrontStaticCachePolicy` for selecting the static origin cache policy type
2. THE Template SHALL offer the following options for `CloudFrontStaticCachePolicy`: `CachingOptimized`, `CachingDisabled`, `CachingOptimizedForUncompressedObjects`, `Elemental-MediaPackage`, `CustomDefault`, `CustomArn`
3. THE Template SHALL set the default value of `CloudFrontStaticCachePolicy` to `CachingOptimized`
4. WHEN `CloudFrontStaticCachePolicy` is set to `CustomArn`, THE Template SHALL provide a parameter named `CloudFrontStaticCustomCachePolicyArn` for specifying the custom policy ARN
5. THE Template SHALL set the default value of `CloudFrontStaticCustomCachePolicyArn` to an empty string

### Requirement 2: API Origin Cache Policy Selection

**User Story:** As a DevOps engineer, I want to choose between AWS managed cache policies and custom policies for my API origin, so that I can control API caching behavior appropriately.

#### Acceptance Criteria

1. THE Template SHALL provide a parameter named `CloudFrontApiCachePolicy` for selecting the API origin cache policy type
2. THE Template SHALL offer the following options for `CloudFrontApiCachePolicy`: `CachingOptimized`, `CachingDisabled`, `CachingOptimizedForUncompressedObjects`, `Elemental-MediaPackage`, `CustomDefault`, `CustomArn`
3. THE Template SHALL set the default value of `CloudFrontApiCachePolicy` to `CachingDisabled`
4. WHEN `CloudFrontApiCachePolicy` is set to `CustomArn`, THE Template SHALL provide a parameter named `CloudFrontApiCustomCachePolicyArn` for specifying the custom policy ARN
5. THE Template SHALL set the default value of `CloudFrontApiCustomCachePolicyArn` to an empty string

### Requirement 3: Managed Cache Policy Documentation

**User Story:** As a template user, I want clear descriptions of each managed cache policy option, so that I can choose the appropriate policy for my use case.

#### Acceptance Criteria

1. THE Template SHALL provide a description for `CachingOptimized` as "Recommended for most use cases. Caches based on query strings and headers."
2. THE Template SHALL provide a description for `CachingDisabled` as "Disables caching. Recommended for dynamic content and APIs."
3. THE Template SHALL provide a description for `CachingOptimizedForUncompressedObjects` as "Optimized for uncompressed content. Disables compression."
4. THE Template SHALL provide a description for `Elemental-MediaPackage` as "Optimized for AWS Elemental MediaPackage origins."
5. THE Template SHALL provide a description for `CustomDefault` as "Use the template's default custom cache policy."
6. THE Template SHALL provide a description for `CustomArn` as "Use a custom cache policy ARN (requires CloudFrontStaticCustomCachePolicyArn or CloudFrontApiCustomCachePolicyArn parameter)."

### Requirement 4: Conditional Custom Policy Creation

**User Story:** As a DevOps engineer, I want custom cache policy resources to be created only when needed, so that I minimize resource creation and stack complexity.

#### Acceptance Criteria

1. WHEN `CloudFrontStaticCachePolicy` is set to `CustomDefault`, THE Template SHALL create the `CloudFrontCachePolicyStatic` resource
2. WHEN `CloudFrontStaticCachePolicy` is NOT set to `CustomDefault`, THE Template SHALL NOT create the `CloudFrontCachePolicyStatic` resource
3. WHEN `CloudFrontApiCachePolicy` is set to `CustomDefault`, THE Template SHALL create the `CloudFrontCachePolicyApi` resource
4. WHEN `CloudFrontApiCachePolicy` is NOT set to `CustomDefault`, THE Template SHALL NOT create the `CloudFrontCachePolicyApi` resource
5. THE Template SHALL add a condition to the `CloudFrontCachePolicyApi` resource (currently it has no condition)

### Requirement 5: Cache Policy ARN Resolution

**User Story:** As a CloudFormation developer, I want the template to correctly resolve cache policy ARNs based on the selected policy type, so that the CloudFront distribution uses the appropriate policy.

#### Acceptance Criteria

1. WHEN `CloudFrontStaticCachePolicy` is `CachingOptimized`, THE Template SHALL use the managed policy ID `658327ea-f89d-4fab-a63d-7e88639e58f6`
2. WHEN `CloudFrontStaticCachePolicy` is `CachingDisabled`, THE Template SHALL use the managed policy ID `4135ea2d-6df8-44a3-9df3-4b5a84be39ad`
3. WHEN `CloudFrontStaticCachePolicy` is `CachingOptimizedForUncompressedObjects`, THE Template SHALL use the managed policy ID `b2884449-e4de-46a7-ac36-70bc7f1ddd6d`
4. WHEN `CloudFrontStaticCachePolicy` is `Elemental-MediaPackage`, THE Template SHALL use the managed policy ID `08627262-05a9-4f76-9ded-b50ca2e3a84f`
5. WHEN `CloudFrontStaticCachePolicy` is `CustomDefault`, THE Template SHALL use the reference to the `CloudFrontCachePolicyStatic` resource
6. WHEN `CloudFrontStaticCachePolicy` is `CustomArn`, THE Template SHALL use the value from `CloudFrontStaticCustomCachePolicyArn` parameter
7. WHEN `CloudFrontApiCachePolicy` is `CachingOptimized`, THE Template SHALL use the managed policy ID `658327ea-f89d-4fab-a63d-7e88639e58f6`
8. WHEN `CloudFrontApiCachePolicy` is `CachingDisabled`, THE Template SHALL use the managed policy ID `4135ea2d-6df8-44a3-9df3-4b5a84be39ad`
9. WHEN `CloudFrontApiCachePolicy` is `CachingOptimizedForUncompressedObjects`, THE Template SHALL use the managed policy ID `b2884449-e4de-46a7-ac36-70bc7f1ddd6d`
10. WHEN `CloudFrontApiCachePolicy` is `Elemental-MediaPackage`, THE Template SHALL use the managed policy ID `08627262-05a9-4f76-9ded-b50ca2e3a84f`
11. WHEN `CloudFrontApiCachePolicy` is `CustomDefault`, THE Template SHALL use the reference to the `CloudFrontCachePolicyApi` resource
12. WHEN `CloudFrontApiCachePolicy` is `CustomArn`, THE Template SHALL use the value from `CloudFrontApiCustomCachePolicyArn` parameter

### Requirement 6: CloudFront Distribution Integration

**User Story:** As a DevOps engineer, I want the CloudFront distribution to use the selected cache policies, so that caching behavior matches my configuration.

#### Acceptance Criteria

1. THE Template SHALL apply the resolved static cache policy to the default cache behavior when the static origin is the root
2. THE Template SHALL apply the resolved static cache policy to the static path cache behavior when a static path is configured
3. THE Template SHALL apply the resolved API cache policy to the default cache behavior when the API origin is the root
4. THE Template SHALL apply the resolved API cache policy to the API path cache behavior when an API path is configured

### Requirement 7: Documentation Comments for README Generation

**User Story:** As a documentation maintainer, I want important cache policy information to be included in the generated README, so that users understand the available options and AWS documentation references.

#### Acceptance Criteria

1. THE Template SHALL include a comment block with the `>!` notation before the cache policy resolution logic in the CloudFront distribution resource
2. THE Comment_Block SHALL reference AWS documentation for managed cache policies
3. THE Comment_Block SHALL explain the available managed policy options
4. THE Comment_Block SHALL be positioned to ensure inclusion in the generated README

### Requirement 8: Parameter Organization

**User Story:** As a template user, I want cache policy parameters to be logically grouped, so that I can easily find and configure caching settings.

#### Acceptance Criteria

1. THE Template SHALL add cache policy parameters to the Metadata section
2. THE Template SHALL create a new parameter group labeled "Cache Policies" or add to an existing appropriate group
3. THE Template SHALL list parameters in a logical order: `CloudFrontStaticCachePolicy`, `CloudFrontStaticCustomCachePolicyArn`, `CloudFrontApiCachePolicy`, `CloudFrontApiCustomCachePolicyArn`

### Requirement 9: Custom ARN Validation

**User Story:** As a template user, I want validation of custom cache policy ARNs, so that I receive clear error messages if I provide an invalid ARN.

#### Acceptance Criteria

1. THE Template SHALL validate that `CloudFrontStaticCustomCachePolicyArn` matches the CloudFront cache policy ARN pattern when non-empty
2. THE Template SHALL validate that `CloudFrontApiCustomCachePolicyArn` matches the CloudFront cache policy ARN pattern when non-empty
3. THE Template SHALL accept an empty string as a valid value for both custom ARN parameters
4. WHEN an invalid ARN is provided, THE Template SHALL display a constraint error message

### Requirement 10: Backward Compatibility

**User Story:** As an existing template user, I want my existing stacks to continue working without modification, so that I can update to the new template version without disruption.

#### Acceptance Criteria

1. THE Template SHALL maintain backward compatibility by using default values that preserve existing behavior
2. WHEN no cache policy parameters are specified AND `DeployEnvironment` is `PROD`, THE Template SHALL use `CachingOptimized` for static origins
3. WHEN no cache policy parameters are specified AND `DeployEnvironment` is `PROD`, THE Template SHALL use `CachingDisabled` for API origins
4. WHEN no cache policy parameters are specified AND `DeployEnvironment` is `DEV` or `TEST`, THE Template SHALL use `CachingDisabled` for both static and API origins
5. THE Template SHALL NOT require existing stacks to provide new parameters during stack updates

### Requirement 11: Environment-Based Cache Policy Override

**User Story:** As a DevOps engineer, I want non-production environments to always use disabled caching, so that I can test with fresh content and avoid caching issues during development and testing.

#### Acceptance Criteria

1. WHEN `DeployEnvironment` is `DEV` or `TEST`, THE Template SHALL use `CachingDisabled` managed policy for both static and API origins regardless of the `CloudFrontStaticCachePolicy` and `CloudFrontApiCachePolicy` parameter values
2. WHEN `DeployEnvironment` is `PROD`, THE Template SHALL use the cache policies specified by `CloudFrontStaticCachePolicy` and `CloudFrontApiCachePolicy` parameters
3. THE Template SHALL NOT create custom cache policy resources when `DeployEnvironment` is `DEV` or `TEST`
4. THE Template SHALL document this environment-based override behavior in parameter descriptions

### Requirement 12: Version Management

**User Story:** As a repository maintainer, I want the template version to be properly incremented, so that users can track changes and understand compatibility.

#### Acceptance Criteria

1. WHEN the current template PATCH version is greater than 0, THE Template SHALL increment the PATCH version
2. THE Template SHALL update the version date to the date of the change
3. THE Template SHALL follow semantic versioning rules as defined in template-version-control.md
