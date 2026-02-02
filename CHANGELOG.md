# Change Log

All notable changes to this project will be documented in this file.

Released versions are available from the public S3 bucket `63klabs`

## v0.0.29 - unreleased

### Added
- **CloudFront Logging Support** [Spec: 0-0-29-network-cloudfront-logging](../.kiro/specs/0-0-29-network-cloudfront-logging/)
  - Network: template-network-route53-cloudfront-s3-apigw.yml v0.0.14 - Added optional CloudFront logging with S3LogBucketName parameter
  - Steering Document: template-parameter-standards.md - Standardized parameter naming and definitions across templates
- **Comprehensive Documentation**: Full documentation of the repository structure, templates, and contribution guidelines
- **AI Steering Documents**: Initial AI steering documents to guide the development and maintenance of AI-related components

## v0.0.28 - 2026-01-08

### Added
- **CloudFormation Template Validation**: Automated validation of all CloudFormation templates using cfn-lint
  - Recursive template discovery in templates/v2 directory
  - Integration with pytest for local development testing
  - CI/CD pipeline integration via buildspec.yml
  - Comprehensive error reporting with file paths and violation details
  - Virtual environment isolation for cfn-lint dependencies
  - Property-based testing for validation consistency
  - Graceful error handling and recovery mechanisms

### Changed
- Enhanced README.md with CloudFormation validation documentation and setup instructions
- Updated buildspec.yml to include CFN template validation in build process

### Dependencies
- Added cfn-lint>=0.83.0 for CloudFormation template validation
- Added hypothesis>=6.92.0 for property-based testing
