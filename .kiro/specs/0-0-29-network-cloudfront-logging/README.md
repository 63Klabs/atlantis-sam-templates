# CloudFront Logging for Network Template

## Overview

This specification adds optional CloudFront logging functionality to the network infrastructure template (template-network-route53-cloudfront-s3-apigw.yml) and creates a steering document for standardized parameter naming across all CloudFormation templates.

## Specification Documents

- [Requirements](./requirements.md) - Detailed requirements using EARS patterns
- [Design](./design.md) - Technical design with architecture, components, and correctness properties
- [Tasks](./tasks.md) - Implementation plan with actionable tasks

## Summary

### What's Being Added

1. **CloudFront Logging Parameter**: New optional `S3LogBucketName` parameter that allows users to enable CloudFront access logging
2. **Conditional Logging**: Logging is only enabled when a valid S3 bucket name is provided
3. **Organized Log Prefix**: Logs are organized with prefix `cloudfront/{Prefix}-{ProjectId}-{StageId}`
4. **Parameter Standards Document**: New steering document defining standard parameters used across all templates

### Key Features

- **Optional**: Logging is disabled by default (empty string parameter)
- **Validated**: Bucket name validation ensures correct S3 naming conventions
- **Organized**: Consistent log prefix structure for easy log management
- **Backward Compatible**: Existing stacks can be updated without changes
- **Well Documented**: Comprehensive documentation updates for users

### Template Changes

- **Version**: v0.0.13 → v0.0.14
- **New Parameter**: S3LogBucketName (optional, validated)
- **New Condition**: HasLogBucket (determines if logging is enabled)
- **Modified Resource**: CloudFrontDistribution (adds conditional Logging property)
- **New Outputs**: CloudFrontLogBucket, CloudFrontLogPrefix (conditional)

### New Steering Document

`.kiro/steering/template-parameter-standards.md` will define:
- Standard parameter names (Prefix, ProjectId, StageId, etc.)
- Validation patterns for each parameter
- Metadata parameter group labels
- Usage guidelines for template developers

## Implementation Status

- [x] Requirements defined
- [x] Design completed
- [x] Tasks created
- [ ] Implementation pending

## Related Templates

- `templates/v2/network/template-network-route53-cloudfront-s3-apigw.yml` - Template being modified
- `templates/v2/storage/template-storage-s3-oac-for-cloudfront.yml` - Related storage template (for reference)

## Testing Approach

- **Unit Tests**: Comprehensive coverage of template structure, parameters, conditions, and outputs
- **Property Tests**: Minimal set (2 tests) focusing on core validation logic per testing-guidelines.md
- **Integration Tests**: Optional end-to-end deployment verification

## Documentation Updates

- Template README: Add parameter, resource, and output documentation
- Steering Document: Create new parameter standards document
- CHANGELOG: Add entry for v0.0.14 release
