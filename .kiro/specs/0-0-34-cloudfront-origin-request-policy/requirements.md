# Requirements Document

## Introduction

This specification adds the AWS managed Origin Request Policy "AllViewerExceptHostHeader" to the API Gateway cache behaviors in the network infrastructure template (template-network-route53-cloudfront-s3-apigw.yml). When API Gateway is placed behind CloudFront, the default behavior strips most viewer headers (including User-Agent) before forwarding requests to the origin. The AllViewerExceptHostHeader origin request policy forwards all viewer headers except the Host header to the origin, ensuring headers like User-Agent reach API Gateway while preserving the correct Host header required for API Gateway routing. This is an AWS managed policy with a well-known fixed ID (b689b0a8-53d0-40ab-baf2-68738e2966ac) that does not need to be created as a custom resource.

Currently, the template uses the `HeadersToForwardToApi` parameter with a custom cache policy to whitelist specific headers. The origin request policy approach is the modern, recommended method for forwarding headers to the origin without affecting the cache key. By using an origin request policy, headers are forwarded to the origin independently of the cache policy, providing a cleaner separation of concerns. The existing `HeadersToForwardToApi` parameter and its associated custom cache policy header forwarding will be replaced by this origin request policy for API behaviors.

## Glossary

- **CloudFront_Distribution**: The AWS CloudFront distribution resource that serves static content and/or API Gateway endpoints
- **Origin_Request_Policy**: A CloudFront policy that specifies the headers, cookies, and query strings that CloudFront includes in requests it sends to the origin, independent of the cache key
- **AllViewerExceptHostHeader**: An AWS managed origin request policy (ID: b689b0a8-53d0-40ab-baf2-68738e2966ac) that forwards all viewer headers, cookies, and query strings to the origin except the Host header
- **API_Behavior**: A cache behavior in the CloudFront distribution that serves content from the API Gateway origin, including both the default behavior (when API is root) and the path-based behavior
- **Default_Cache_Behavior**: The cache behavior that handles requests not matching any path-based cache behavior pattern
- **Template**: The CloudFormation template file template-network-route53-cloudfront-s3-apigw.yml
- **Cache_Policy**: A CloudFront policy that determines what values are included in the cache key and how long objects are cached
- **HeadersToForwardToApi**: The existing template parameter that specifies a comma-delimited list of headers to forward to API Gateway via the custom cache policy

## Requirements

### Requirement 1: Origin Request Policy on Default Cache Behavior for API

**User Story:** As a DevOps engineer, I want the AllViewerExceptHostHeader origin request policy applied to the default cache behavior when API Gateway is the root origin, so that viewer headers like User-Agent are forwarded to API Gateway.

#### Acceptance Criteria

1. WHEN the API origin is the root (StaticOriginIsRoot condition is false and ApiIsBehindCloudFront condition is true), THE Template SHALL set the OriginRequestPolicyId on the DefaultCacheBehavior to the AllViewerExceptHostHeader managed policy ID (b689b0a8-53d0-40ab-baf2-68738e2966ac)
2. WHEN the static origin is the root (StaticOriginIsRoot condition is true), THE Template SHALL NOT set an OriginRequestPolicyId on the DefaultCacheBehavior

### Requirement 2: Origin Request Policy on Path-Based API Cache Behavior

**User Story:** As a DevOps engineer, I want the AllViewerExceptHostHeader origin request policy applied to the path-based API cache behavior, so that viewer headers like User-Agent are forwarded to API Gateway when it is served from a specific path.

#### Acceptance Criteria

1. WHEN an API path is configured behind CloudFront (HasRouteForApiInCloudFront condition is true), THE Template SHALL set the OriginRequestPolicyId on the API path cache behavior to the AllViewerExceptHostHeader managed policy ID (b689b0a8-53d0-40ab-baf2-68738e2966ac)

### Requirement 3: Remove HeadersToForwardToApi from Custom Cache Policy

**User Story:** As a DevOps engineer, I want header forwarding removed from the custom API cache policy, so that header forwarding is handled exclusively by the origin request policy and does not conflict with the cache key.

#### Acceptance Criteria

1. THE Template SHALL remove the HeadersConfig section from the CloudFrontCachePolicyApi resource that references the HeadersToForwardToApi parameter
2. THE Template SHALL set the HeadersConfig in the CloudFrontCachePolicyApi resource to HeaderBehavior: none
3. THE Template SHALL remove the HasHeadersToForwardToApi condition from the Conditions section

### Requirement 4: Deprecate HeadersToForwardToApi Parameter

**User Story:** As a DevOps engineer, I want the HeadersToForwardToApi parameter deprecated, so that the template transitions to the origin request policy approach while maintaining backward compatibility.

#### Acceptance Criteria

1. THE Template SHALL retain the HeadersToForwardToApi parameter definition to maintain backward compatibility with existing stack deployments
2. THE Template SHALL update the HeadersToForwardToApi parameter description to indicate it is deprecated and that header forwarding is now handled by the AllViewerExceptHostHeader origin request policy
3. THE Template SHALL NOT use the HeadersToForwardToApi parameter value in any resource configuration

### Requirement 5: No Origin Request Policy on Static Behaviors

**User Story:** As a DevOps engineer, I want static content behaviors to remain unaffected by the origin request policy, so that S3 origin requests are not modified.

#### Acceptance Criteria

1. THE Template SHALL NOT set an OriginRequestPolicyId on the static path cache behavior
2. THE Template SHALL NOT set an OriginRequestPolicyId on the DefaultCacheBehavior when the static origin is the root (StaticOriginIsRoot condition is true)

### Requirement 6: Parameter Organization Update

**User Story:** As a template user, I want the parameter groups in the CloudFormation console to reflect the deprecation of HeadersToForwardToApi, so that the console interface is clear and accurate.

#### Acceptance Criteria

1. THE Template SHALL update the Metadata parameter group label "API behind CloudFront Forwarding" to indicate the section contains deprecated parameters
2. THE Template SHALL retain the HeadersToForwardToApi parameter in the Metadata parameter group for backward compatibility

### Requirement 7: Backward Compatibility

**User Story:** As an existing template user, I want my existing stacks to continue working without modification, so that I can update to the new template version without disruption.

#### Acceptance Criteria

1. THE Template SHALL maintain backward compatibility by retaining the HeadersToForwardToApi parameter with its existing default value
2. WHEN an existing stack is updated with the new template version, THE Template SHALL apply the origin request policy to API behaviors without requiring parameter changes
3. THE Template SHALL NOT introduce any new required parameters

### Requirement 8: Version Management

**User Story:** As a repository maintainer, I want the template version to be properly managed, so that users can track changes and understand compatibility.

#### Acceptance Criteria

1. WHEN the current template PATCH version is greater than 0, THE Template SHALL increment the PATCH version and update the date
2. WHEN the current template PATCH version is 0, THE Template SHALL NOT increment the version
3. THE Template SHALL follow semantic versioning rules as defined in template-version-control.md
