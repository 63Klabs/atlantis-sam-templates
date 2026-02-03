# Spec: Add Origin Path Parameters to CloudFront Network Template

## Overview

This spec adds two new optional parameters (`StaticOriginPath` and `ApiOriginPath`) to the CloudFront network template (`template-network-route53-cloudfront-s3-apigw.yml`), allowing users to customize the origin paths used by CloudFront when fetching content from S3 and API Gateway origins.

## Feature Name

`0-0-29-network-add-origin-path-to-static-and-api`

## Status

**Planning Complete** - Ready for implementation

## Documents

- [Requirements](./requirements.md) - User stories and acceptance criteria
- [Design](./design.md) - Technical design and correctness properties
- [Tasks](./tasks.md) - Implementation task list

## Key Changes

### New Parameters

1. **StaticOriginPath** - Customizes the origin path for S3 static content
   - Default: Empty string (uses `/${StageId}/public`)
   - Accepts: `/` (root), or custom paths like `/static`, `/v1/content`

2. **ApiOriginPath** - Customizes the origin path for API Gateway
   - Default: Empty string (uses `/${ProjectId}-${StageId}`)
   - Accepts: `/` (root), or custom paths like `/api`, `/v2/services`

### Behavior

- **Empty (default):** Uses current hardcoded paths with variable substitution
- **Single `/`:** Uses empty string for CloudFront (root path, no prefix)
- **Custom path:** Uses the provided path as-is (e.g., `/custom/path`)

### Validation

- Paths must start with `/` if not empty
- Paths must not end with `/` unless exactly `/`
- Placeholder syntax like `{StageId}` or `${StageId}` is rejected

## Backward Compatibility

Fully backward compatible. When both parameters are left at their default empty values, the template behaves identically to the previous version.

## Template Version

- **Current:** v0.0.14
- **After Implementation:** v0.0.15 (PATCH increment - non-breaking change)

## Testing Strategy

- **Unit Tests:** Verify parameter structure, edge cases, and validation
- **Property-Based Tests:** Verify universal properties across 100+ iterations per test
- **6 Correctness Properties:** Cover default behavior, custom paths, validation, and backward compatibility

## Implementation Notes

- Follows template-parameter-standards.md for parameter definitions
- Follows template-version-control.md for version management
- Follows documentation-end-user-cfn-templates.md for documentation updates
- Follows changelog.md for CHANGELOG updates

## Next Steps

To begin implementation:
1. Open `tasks.md`
2. Click "Start task" next to task 1 to begin with version increment
3. Follow the task list sequentially through implementation, testing, and documentation
