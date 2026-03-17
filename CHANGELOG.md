# Change Log

All notable changes to this project will be documented in this file.

Released versions are available from the public S3 bucket `63klabs`

## v0.0.30 - unreleased

### Changed
- **Network: template-network-route53-cloudfront-s3-apigw.yml (v0.0.17)** [Spec: cloudfront-function-associations](../.kiro/specs/0-0-30-cloudfront-function-associations/)
  - CloudFront Function Associations: Added 8 optional parameters to associate existing CloudFront Functions with static and API cache behaviors for viewer-request, viewer-response, origin-request, and origin-response event types
- **Pipeline: template-pipeline.yml v2.0.18**
  - Added additional permissions to Post Deployment CodeBuild project so that it can read back the stack resources. This does not grant any access to the resources created. For that you will need to supply your own managed policy via `PostDeploySvcRoleIncludeManagedPolicyArns`. However, since accessing API Gateway is common post-deployment, read permissions have been included.

## v0.0.29 - 2026-02-18

### Added
- **Comprehensive Documentation**: Full documentation of the repository structure, templates, and contribution guidelines
- **Template Standards**: template-standard.md - Standardized template structure,naming conventions, and best practices
- **AI Steering Documents**: Initial AI steering documents to guide the development and maintenance of AI-related components

### Changed
- **Network: template-network-route53-cloudfront-s3-apigw.yml v0.0.14** - Added optional CloudFront logging with S3LogBucketName parameter [Spec: 0-0-29-network-cloudfront-logging](../.kiro/specs/0-0-29-network-cloudfront-logging/)
- **Network: template-network-route53-cloudfront-s3-apigw.yml v0.0.15** - Added StaticOriginPath and ApiOriginPath parameters for customizable CloudFront origin paths [Spec: 0-0-29-network-add-origin-path-to-static-and-api](../.kiro/specs/0-0-29-network-add-origin-path-to-static-and-api/)
- **Network: template-network-route53-cloudfront-s3-apigw.yml v0.0.16** - Added support for AWS managed cache policies with environment-based overrides [Spec: 0-0-29-network-add-managed-cache-policies](../.kiro/specs/0-0-29-network-add-managed-cache-policies/)

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
