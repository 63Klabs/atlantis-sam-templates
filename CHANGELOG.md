# Change Log

All notable changes to this project will be documented in this file.

Released versions are available from the public S3 bucket `63klabs`

## v0.0.33 (2026-04-30)

### Added
- **Modules** - Template snipits, which can also be used as modules to insert into your CloudFormation templates, have been added to the repository! These will find their way into other templates to provide consistency and easy maintainability. Currently, there is no versioning. While a previous version can be retreived from the AWS CLI, since they are still in the S3 bucket, CloudFormation does not support versions. An optimal solution for versioning will be developed later.
- **`account` category** - In addition to `network`, `pipeline`, and `storage` there is now an `account` template directory for admins managing account-wide resources.

### Updated
- **Pipelines: template-pipeline.yml, template-pipeline-github.yml** - Added `SsmParameterCRUDThisDeploymentOnly` IAM policy statement to CloudFormationSvcRole. This allows the application template to manage SSM Parameters under the `${ParameterStoreHierarchy}app-stack/` path. For example: `/sam-app/PROD/acme-myapp-prod/app-stack/*` Note the use of the additional path segment `app-stack` restricting the application infrastructure stack more than CodeBuild and PostDeploy permissions would. This should be used for resolving circular dependencies and storing configurations only, not for secrets. It is best practice to not store secrets as Environment variables or pass as parameters, but rather access SSM Parameter store at runtime.

### Deprecated
- **`service-role` category** - Deploying service-roles for each prefix was a temporary solution, never meant for developers. This process has been assumed into the `templates/v2/account/prefix-based-infrastructure.yml` template that admins can deploy at account creation time. This template also includes new `network` roles.

## v0.0.31 (2026-04-03)

### Updated
- **Pipeline: template-pipeline*.yml** - Added `SSMPublicParameterReadOnly` IAM policy statement to CloudFormationSvcRole, CodeBuildSvcRole, and PostDeploySvcRole on all 3 existing pipeline templates granting `ssm:GetParameter` and `ssm:GetParameters` on `/aws/service/*` public AWS SSM parameters, enabling `{{resolve:ssm:/aws/service/...}}` dynamic references in application templates [Spec: pipeline-ssm-parameter-access](../.kiro/specs/0-0-31-pipeline-ssm-parameter-access/)

### Changed
- **Pipeline Notification Formatting** [Spec: pipeline-notification-formatting](../.kiro/specs/0-0-31-pipeline-notification-formatting/)
  - Pipeline: template-pipeline.yml v2.0.20 - Switched notification messages from raw JSON-like format to human-readable plain text with labeled fields, blank-line separation, ALERT: prefix for failures, and call-to-action for failure notifications
  - Pipeline: template-pipeline-github.yml v2.0.3 - Switched notification messages from raw JSON-like format to human-readable plain text with labeled fields, blank-line separation, ALERT: prefix for failures, and call-to-action for failure notifications
  - Pipeline: template-pipeline-build-only.yml v2.0.5 - Switched notification messages from raw JSON-like format to human-readable plain text with labeled fields, blank-line separation, ALERT: prefix for failures, and call-to-action for failure notifications
- **S3 Regional Buckets** - Added support for S3 regional buckets.

## v0.0.30 (2026-03-17)

### Changed
- **Network: template-network-route53-cloudfront-s3-apigw.yml (v0.0.17)** [Spec: cloudfront-function-associations](../.kiro/specs/0-0-30-cloudfront-function-associations/)
  - CloudFront Function Associations: Added 8 optional parameters to associate existing CloudFront Functions with static and API cache behaviors for viewer-request, viewer-response, origin-request, and origin-response event types
- **Pipeline: template-pipeline.yml v2.0.18**
  - Added additional permissions to Post Deployment CodeBuild project so that it can read back the stack resources. This does not grant any access to the resources created. For that you will need to supply your own managed policy via `PostDeploySvcRoleIncludeManagedPolicyArns`. However, since accessing API Gateway is common post-deployment, read permissions have been included.
- **Storage: template-storage-s3-access-logs.yml v0.0.2**
  - Added optional CloudFront legacy logging support with AllowLegacyCloudFrontLogs parameter [Spec: cloudfront-logging-acl-fix](../.kiro/specs/0-0-30-cloudfront-logging-acl-fix/)

## v0.0.29 (2026-02-18)

### Added
- **Comprehensive Documentation**: Full documentation of the repository structure, templates, and contribution guidelines
- **Template Standards**: template-standard.md - Standardized template structure,naming conventions, and best practices
- **AI Steering Documents**: Initial AI steering documents to guide the development and maintenance of AI-related components

### Changed
- **Network: template-network-route53-cloudfront-s3-apigw.yml v0.0.14** - Added optional CloudFront logging with S3LogBucketName parameter [Spec: 0-0-29-network-cloudfront-logging](../.kiro/specs/0-0-29-network-cloudfront-logging/)
- **Network: template-network-route53-cloudfront-s3-apigw.yml v0.0.15** - Added StaticOriginPath and ApiOriginPath parameters for customizable CloudFront origin paths [Spec: 0-0-29-network-add-origin-path-to-static-and-api](../.kiro/specs/0-0-29-network-add-origin-path-to-static-and-api/)
- **Network: template-network-route53-cloudfront-s3-apigw.yml v0.0.16** - Added support for AWS managed cache policies with environment-based overrides [Spec: 0-0-29-network-add-managed-cache-policies](../.kiro/specs/0-0-29-network-add-managed-cache-policies/)

## v0.0.28 (2026-01-08)

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
