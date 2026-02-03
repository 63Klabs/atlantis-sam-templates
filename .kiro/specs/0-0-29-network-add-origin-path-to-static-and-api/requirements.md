# Requirements Document

## Introduction

This document specifies the requirements for adding customizable origin path parameters to the CloudFront network template. Currently, the template uses hardcoded origin paths (`/${StageId}/public` for static content and `/${ProjectId}-${StageId}` for API Gateway). This feature will allow users to override these defaults with custom paths while maintaining backward compatibility.

## Glossary

- **Origin_Path**: The path prefix used by CloudFront when requesting content from an origin (S3 or API Gateway)
- **Static_Origin**: The S3 bucket serving static content through CloudFront
- **Api_Origin**: The API Gateway serving API requests through CloudFront
- **CloudFront_Distribution**: The AWS CloudFront distribution that routes requests to origins
- **Template**: The CloudFormation template file `template-network-route53-cloudfront-s3-apigw.yml`
- **Parameter**: A CloudFormation template parameter that accepts user input during stack creation/update

## Requirements

### Requirement 1: Add StaticOriginPath Parameter

**User Story:** As a developer, I want to customize the origin path for static content in CloudFront, so that I can organize my S3 bucket structure according to my project needs.

#### Acceptance Criteria

1. THE Template SHALL include a new parameter named `StaticOriginPath`
2. WHEN `StaticOriginPath` is empty (default), THE Template SHALL use the current default path `/${StageId}/public`
3. WHEN `StaticOriginPath` is set to `/`, THE Template SHALL use an empty string for the CloudFront origin path (root path)
4. WHEN `StaticOriginPath` is set to a custom path (e.g., `/foo`), THE Template SHALL use that exact path as the CloudFront origin path
5. THE Template SHALL validate that `StaticOriginPath` starts with `/` if not empty
6. THE Template SHALL validate that `StaticOriginPath` does not end with `/` unless it is exactly `/`
7. THE Template SHALL reject `StaticOriginPath` values containing placeholder syntax like `{StageId}` or `${StageId}`

### Requirement 2: Add ApiOriginPath Parameter

**User Story:** As a developer, I want to customize the origin path for API Gateway in CloudFront, so that I can use custom stage names or path structures in my API Gateway configuration.

#### Acceptance Criteria

1. THE Template SHALL include a new parameter named `ApiOriginPath`
2. WHEN `ApiOriginPath` is empty (default), THE Template SHALL use the current default path `/${ProjectId}-${StageId}`
3. WHEN `ApiOriginPath` is set to `/`, THE Template SHALL use an empty string for the CloudFront origin path (root path)
4. WHEN `ApiOriginPath` is set to a custom path (e.g., `/api/v1`), THE Template SHALL use that exact path as the CloudFront origin path
5. THE Template SHALL validate that `ApiOriginPath` starts with `/` if not empty
6. THE Template SHALL validate that `ApiOriginPath` does not end with `/` unless it is exactly `/`
7. THE Template SHALL reject `ApiOriginPath` values containing placeholder syntax like `{StageId}` or `${StageId}`

### Requirement 3: Parameter Validation and Constraints

**User Story:** As a developer, I want clear validation messages when I provide invalid origin paths, so that I can quickly correct my configuration errors.

#### Acceptance Criteria

1. THE Template SHALL use AllowedPattern regex to validate path format
2. WHEN a path does not start with `/`, THE Template SHALL reject the value with a clear constraint description
3. WHEN a path ends with `/` (except for single `/`), THE Template SHALL reject the value with a clear constraint description
4. WHEN a path contains `{` or `}` characters, THE Template SHALL reject the value with a clear constraint description
5. THE Template SHALL provide constraint descriptions that explain valid path formats and examples

### Requirement 4: Conditional Logic for Origin Path Selection

**User Story:** As a developer, I want the template to automatically choose between default and custom paths, so that I don't need to manually calculate or construct paths.

#### Acceptance Criteria

1. WHEN `StaticOriginPath` is empty, THE Template SHALL use `/${StageId}/public` as the static origin path
2. WHEN `StaticOriginPath` is `/`, THE Template SHALL use an empty string as the static origin path
3. WHEN `StaticOriginPath` is a custom path, THE Template SHALL use that path as-is for the static origin path
4. WHEN `ApiOriginPath` is empty, THE Template SHALL use `/${ProjectId}-${StageId}` as the API origin path
5. WHEN `ApiOriginPath` is `/`, THE Template SHALL use an empty string as the API origin path
6. WHEN `ApiOriginPath` is a custom path, THE Template SHALL use that path as-is for the API origin path

### Requirement 5: Backward Compatibility

**User Story:** As an existing user, I want my current CloudFormation stacks to continue working without changes, so that I can upgrade to the new template version without disruption.

#### Acceptance Criteria

1. WHEN both `StaticOriginPath` and `ApiOriginPath` are left at their default empty values, THE Template SHALL behave identically to the previous version
2. THE Template SHALL not require any parameter changes for existing stack updates
3. THE Template SHALL maintain all existing functionality for static and API origins

### Requirement 6: Parameter Organization

**User Story:** As a developer, I want origin path parameters to be logically grouped in the CloudFormation console, so that I can easily find and configure them.

#### Acceptance Criteria

1. THE Template SHALL place `StaticOriginPath` in the "Origins for S3 and/or API Gateway" parameter group
2. THE Template SHALL place `ApiOriginPath` in the "Origins for S3 and/or API Gateway" parameter group
3. THE Template SHALL position these parameters after `S3OriginDomainName` and `ApiGatewayId` in the parameter group

### Requirement 7: Documentation Updates

**User Story:** As a developer, I want comprehensive documentation for the new parameters, so that I understand how to use them correctly.

#### Acceptance Criteria

1. THE Template SHALL include clear parameter descriptions explaining the purpose and behavior of `StaticOriginPath`
2. THE Template SHALL include clear parameter descriptions explaining the purpose and behavior of `ApiOriginPath`
3. THE Template SHALL include examples in parameter descriptions showing valid path formats
4. THE Template documentation SHALL be updated to reflect the new parameters and their usage
5. THE Template documentation SHALL include migration guidance for users who want to customize origin paths
