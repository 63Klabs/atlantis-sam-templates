# Requirements Document

## Introduction

This specification adds support for associating CloudFront Functions with both the static content behaviors and the API origin behaviors of the network infrastructure template (template-network-route53-cloudfront-s3-apigw.yml). CloudFront Functions enable lightweight edge compute for tasks such as URL rewriting (e.g., rewriting directory root requests to index.html), header manipulation, and request/response transformations. The CloudFront Function resources themselves are created separately; this feature adds parameters that allow users to associate existing CloudFront Function ARNs with the four supported event types on static content cache behaviors and, separately, the four supported event types on API origin cache behaviors. This does not cover Lambda@Edge associations.

## Glossary

- **CloudFront_Distribution**: The AWS CloudFront distribution resource that serves static content and/or API Gateway endpoints
- **CloudFront_Function**: A lightweight JavaScript function that runs at CloudFront edge locations for request/response manipulation. Created as a separate resource outside this template.
- **Function_Association**: A configuration that links a CloudFront Function to a specific event type on a cache behavior
- **Event_Type**: One of four stages in the CloudFront request/response lifecycle where a function can execute: viewer-request, viewer-response, origin-request, origin-response
- **Static_Behavior**: A cache behavior in the CloudFront distribution that serves content from the S3 static origin, including both the default behavior (when static is root) and the path-based behavior
- **API_Behavior**: A cache behavior in the CloudFront distribution that serves content from the API Gateway origin, including both the default behavior (when API is root, i.e., StaticOriginIsRoot is false) and the path-based behavior (HasRouteForApiInCloudFront)
- **Template**: The CloudFormation template file template-network-route53-cloudfront-s3-apigw.yml
- **Function_ARN**: The Amazon Resource Name that uniquely identifies a CloudFront Function

## Requirements

### Requirement 1: Static CloudFront Function ARN Parameters

**User Story:** As a DevOps engineer, I want to provide CloudFront Function ARNs for each event type on static behaviors, so that I can associate functions with my static content behaviors.

#### Acceptance Criteria

1. THE Template SHALL provide a parameter named `CloudFrontStaticFunctionViewerRequest` for specifying a CloudFront Function ARN to associate with the viewer-request event type on static behaviors
2. THE Template SHALL provide a parameter named `CloudFrontStaticFunctionViewerResponse` for specifying a CloudFront Function ARN to associate with the viewer-response event type on static behaviors
3. THE Template SHALL provide a parameter named `CloudFrontStaticFunctionOriginRequest` for specifying a CloudFront Function ARN to associate with the origin-request event type on static behaviors
4. THE Template SHALL provide a parameter named `CloudFrontStaticFunctionOriginResponse` for specifying a CloudFront Function ARN to associate with the origin-response event type on static behaviors
5. THE Template SHALL set the default value of each static CloudFront Function parameter to an empty string
6. THE Template SHALL validate that each non-empty static CloudFront Function parameter matches the CloudFront Function ARN pattern
7. WHEN an invalid ARN is provided for a static CloudFront Function parameter, THE Template SHALL display a constraint description explaining the expected format

### Requirement 2: API CloudFront Function ARN Parameters

**User Story:** As a DevOps engineer, I want to provide CloudFront Function ARNs for each event type on API behaviors, so that I can associate functions with my API origin behaviors.

#### Acceptance Criteria

1. THE Template SHALL provide a parameter named `CloudFrontApiFunctionViewerRequest` for specifying a CloudFront Function ARN to associate with the viewer-request event type on API behaviors
2. THE Template SHALL provide a parameter named `CloudFrontApiFunctionViewerResponse` for specifying a CloudFront Function ARN to associate with the viewer-response event type on API behaviors
3. THE Template SHALL provide a parameter named `CloudFrontApiFunctionOriginRequest` for specifying a CloudFront Function ARN to associate with the origin-request event type on API behaviors
4. THE Template SHALL provide a parameter named `CloudFrontApiFunctionOriginResponse` for specifying a CloudFront Function ARN to associate with the origin-response event type on API behaviors
5. THE Template SHALL set the default value of each API CloudFront Function parameter to an empty string
6. THE Template SHALL validate that each non-empty API CloudFront Function parameter matches the CloudFront Function ARN pattern
7. WHEN an invalid ARN is provided for an API CloudFront Function parameter, THE Template SHALL display a constraint description explaining the expected format

### Requirement 3: Parameter Organization

**User Story:** As a template user, I want CloudFront Function parameters to be logically grouped in the CloudFormation console, so that I can easily find and configure function associations for static and API behaviors separately.

#### Acceptance Criteria

1. THE Template SHALL add a parameter group in the Metadata section labeled "Static CloudFront Function Associations"
2. THE Template SHALL list the four static CloudFront Function parameters in the "Static CloudFront Function Associations" group in this order: `CloudFrontStaticFunctionViewerRequest`, `CloudFrontStaticFunctionViewerResponse`, `CloudFrontStaticFunctionOriginRequest`, `CloudFrontStaticFunctionOriginResponse`
3. THE Template SHALL add a parameter group in the Metadata section labeled "API CloudFront Function Associations"
4. THE Template SHALL list the four API CloudFront Function parameters in the "API CloudFront Function Associations" group in this order: `CloudFrontApiFunctionViewerRequest`, `CloudFrontApiFunctionViewerResponse`, `CloudFrontApiFunctionOriginRequest`, `CloudFrontApiFunctionOriginResponse`
5. THE Template SHALL place the "Static CloudFront Function Associations" parameter group after the "Cache Policies" group in the Metadata section
6. THE Template SHALL place the "API CloudFront Function Associations" parameter group after the "Static CloudFront Function Associations" group in the Metadata section

### Requirement 4: Conditional Function Association

**User Story:** As a DevOps engineer, I want function associations to be applied only when I provide a function ARN, so that behaviors without functions remain unchanged.

#### Acceptance Criteria

1. THE Template SHALL create a condition for each static CloudFront Function parameter that evaluates to true when the parameter value is not empty
2. THE Template SHALL create a condition for each API CloudFront Function parameter that evaluates to true when the parameter value is not empty
3. WHEN a CloudFront Function parameter is empty, THE Template SHALL NOT include a function association for that event type in the corresponding cache behavior
4. WHEN a CloudFront Function parameter is not empty, THE Template SHALL include a function association for that event type in the corresponding cache behavior

### Requirement 5: Default Cache Behavior Static Function Associations

**User Story:** As a DevOps engineer, I want static CloudFront Functions to be associated with the default cache behavior when static content is served from the root, so that functions apply to all static content requests.

#### Acceptance Criteria

1. WHEN the static origin is the root (StaticOriginIsRoot condition is true), THE Template SHALL apply configured static function associations to the DefaultCacheBehavior
2. THE Template SHALL include a FunctionAssociations list in the DefaultCacheBehavior only when at least one static CloudFront Function parameter is not empty and the static origin is the root
3. WHEN the static origin is the root, THE Template SHALL associate each non-empty static CloudFront Function ARN with its corresponding event type in the DefaultCacheBehavior

### Requirement 6: Path-Based Static Cache Behavior Function Associations

**User Story:** As a DevOps engineer, I want static CloudFront Functions to be associated with the path-based static cache behavior, so that functions apply to static content served from a specific path.

#### Acceptance Criteria

1. WHEN a static path is configured (HasRouteForStaticOrigin condition is true), THE Template SHALL apply configured static function associations to the static path cache behavior
2. THE Template SHALL include a FunctionAssociations list in the static path cache behavior only when at least one static CloudFront Function parameter is not empty
3. THE Template SHALL associate each non-empty static CloudFront Function ARN with its corresponding event type in the static path cache behavior

### Requirement 7: Default Cache Behavior API Function Associations

**User Story:** As a DevOps engineer, I want API CloudFront Functions to be associated with the default cache behavior when the API origin is the root, so that functions apply to all API requests.

#### Acceptance Criteria

1. WHEN the API origin is the root (StaticOriginIsRoot condition is false and ApiIsBehindCloudFront condition is true), THE Template SHALL apply configured API function associations to the DefaultCacheBehavior
2. THE Template SHALL include a FunctionAssociations list in the DefaultCacheBehavior only when at least one API CloudFront Function parameter is not empty and the API origin is the root
3. WHEN the API origin is the root, THE Template SHALL associate each non-empty API CloudFront Function ARN with its corresponding event type in the DefaultCacheBehavior

### Requirement 8: Path-Based API Cache Behavior Function Associations

**User Story:** As a DevOps engineer, I want API CloudFront Functions to be associated with the path-based API cache behavior, so that functions apply to API requests served from a specific path.

#### Acceptance Criteria

1. WHEN an API path is configured behind CloudFront (HasRouteForApiInCloudFront condition is true), THE Template SHALL apply configured API function associations to the API path cache behavior
2. THE Template SHALL include a FunctionAssociations list in the API path cache behavior only when at least one API CloudFront Function parameter is not empty
3. THE Template SHALL associate each non-empty API CloudFront Function ARN with its corresponding event type in the API path cache behavior

### Requirement 9: Isolation of Static and API Function Associations

**User Story:** As a DevOps engineer, I want static function associations to apply only to static behaviors and API function associations to apply only to API behaviors, so that each origin type has independent function configuration.

#### Acceptance Criteria

1. THE Template SHALL NOT apply static CloudFront Function associations to the API path cache behavior
2. THE Template SHALL NOT apply static CloudFront Function associations to the DefaultCacheBehavior when the API origin is the root (StaticOriginIsRoot condition is false)
3. THE Template SHALL NOT apply API CloudFront Function associations to the static path cache behavior
4. THE Template SHALL NOT apply API CloudFront Function associations to the DefaultCacheBehavior when the static origin is the root (StaticOriginIsRoot condition is true)

### Requirement 10: Backward Compatibility

**User Story:** As an existing template user, I want my existing stacks to continue working without modification, so that I can update to the new template version without disruption.

#### Acceptance Criteria

1. THE Template SHALL maintain backward compatibility by defaulting all static and API CloudFront Function parameters to empty strings
2. WHEN no CloudFront Function parameters are specified (neither static nor API), THE Template SHALL produce cache behaviors identical to the current template behavior
3. THE Template SHALL NOT require existing stacks to provide new parameters during stack updates

### Requirement 11: Version Management

**User Story:** As a repository maintainer, I want the template version to be properly managed, so that users can track changes and understand compatibility.

#### Acceptance Criteria

1. WHEN the current template PATCH version is 0, THE Template SHALL NOT increment the version
2. WHEN the current template PATCH version is greater than 0, THE Template SHALL increment the PATCH version and update the date
3. THE Template SHALL follow semantic versioning rules as defined in template-version-control.md
