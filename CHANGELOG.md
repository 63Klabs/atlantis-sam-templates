# Change Log

All notable changes to this project will be documented in this file.

Released versions are freely available for your use from the public S3 bucket `63klabs` and mirrored for deployment in US regions:

- `63klabs` (us-east-2)
- `63klabs-atlas-us-east-1`
- `63klabs-zenith-us-east-2`
- `63klabs-fabric-us-west-1`
- `63klabs-orbit-us-west-2`

When deploying to other regions you may need to [self-host under certain deployment scenerios](https://github.com/63Klabs/atlantis-platform-admin).

The Atlantis Templates Repository is free and open source. Templates and build/deploy scripts for both CodePipeline and GitHub Pipeline are available from the [Atlantis SAM Templates repository on GitHub](https://github.com/63Klabs/atlantis-sam-templates).

## v0.0.39 (unreleased)

### Added
- **Pipeline Modules** [Spec: 0-0-39-pipeline-module-extraction](.kiro/specs/0-0-39-pipeline-module-extraction/) - Created 15 reusable pipeline modules in templates/v2/modules/pipeline/ for shared pipeline infrastructure components
  - Modules: pipeline-notification-topic.yml - SNS topic for pipeline state notifications
  - Modules: pipeline-notification-started-rule.yml - EventBridge rule for STARTED pipeline state
  - Modules: pipeline-notification-succeeded-rule.yml - EventBridge rule for SUCCEEDED pipeline state
  - Modules: pipeline-notification-failed-rule.yml - EventBridge rule for FAILED pipeline state
  - Modules: pipeline-notification-topic-policy.yml - SNS topic policy allowing EventBridge to publish notifications
  - Modules: source-event-service-role.yml - IAM role for CodeCommit source event triggers
  - Modules: source-event-rule.yml - EventBridge rule for CodeCommit repository changes
  - Modules: codebuild-log-group.yml - CloudWatch log group for CodeBuild projects
  - Modules: codebuild-service-role.yml - IAM role for CodeBuild projects with reconciled permissions
  - Modules: codebuild-project.yml - CodeBuild project with standardized container image
  - Modules: cloudformation-svc-role.yml - IAM role for CloudFormation deployments
  - Modules: codedeploy-service-role.yml - IAM role for CodeDeploy operations
  - Modules: postdeploy-service-role.yml - IAM role for post-deployment validation
  - Modules: postdeploy-project.yml - CodeBuild project for post-deployment tasks
  - Modules: postdeploy-log-group.yml - CloudWatch log group for post-deployment builds
- **Cache-Data Modules** [Spec: 0-0-39-cache-data-modularization](.kiro/specs/0-0-39-cache-data-modularization/) - Created four reusable cache-data modules in templates/v2/modules/cache-data/ for shared, prefix-wide Cache-Data infrastructure consumed by prefix-based-infrastructure.yml
  - Modules: cache-dynamodb-table.yml - DynamoDB cache table with TTL (purge_ts) and PAY_PER_REQUEST billing
  - Modules: cache-s3-bucket.yml - Regional S3 cache bucket with AES256 encryption and lifecycle expiration of cache objects
  - Modules: cache-s3-bucket-policy.yml - S3 bucket policy enforcing secure transport and scoped Lambda read/write/delete access
  - Modules: cache-managed-lambda-policy.yml - Managed IAM policy granting Lambda execution roles scoped access to the cache-data S3 bucket and DynamoDB table
- **S3 Access-Logs Modules** - Created two reusable s3-access-logs modules in templates/v2/modules/s3-access-logs/ for a shared, account-wide S3 server access log bucket consumed by account-wide-infrastructure.yml
  - Modules: s3-access-log-bucket.yml - Account-wide regional S3 access log bucket with AES256 encryption, retention, lifecycle expiration, and optional legacy CloudFront ownership controls (Prefix/ProjectId naming tokens dropped)
  - Modules: s3-access-log-bucket-policy.yml - S3 bucket policy enforcing secure transport and granting the S3 (and optional CloudFront) log delivery service write access
  - Steering: Added .kiro/steering/s3-access-logs-module-sync.md to keep the modules in sync with the standalone template-storage-s3-access-logs.yml

### Changed
- **Account: account-wide-infrastructure.yml v0.0.0** - Added opt-in account-wide S3 access log bucket via the EnableS3AccessLogBucket parameter (with LogExpirationInDays and AllowLegacyCloudFrontLogs), consuming the two s3-access-logs modules through AWS::Include with conditional resources and outputs. When enabled, the account-wide artifacts bucket logs to this bucket unless an explicit S3LogBucketName is supplied (which takes precedence)
- **Modules: s3-artifacts-bucket.yml** - Updated server access logging destination precedence to prefer an explicitly supplied S3LogBucketName, falling back to the account-wide access log bucket (AccessLogBucketRegional) when EnableS3AccessLogBucket is true, then to no logging; logs are written under the cf-artifacts/ prefix (backward compatible; default behavior unchanged)
- **Pipeline: template-pipeline.yml v2.0.21** [Spec: 0-0-39-pipeline-module-extraction](.kiro/specs/0-0-39-pipeline-module-extraction/) - Refactored to consume 15 pipeline modules via AWS::Include, replacing inline resource definitions with shared module references
- **Pipeline: template-pipeline-github.yml v2.0.4** [Spec: 0-0-39-pipeline-module-extraction](.kiro/specs/0-0-39-pipeline-module-extraction/) - Refactored to consume 14 pipeline modules via AWS::Include (excludes source-event-rule which is CodeCommit-specific)
- **Pipeline: template-pipeline-build-only.yml v2.0.6** [Spec: 0-0-39-pipeline-module-extraction](.kiro/specs/0-0-39-pipeline-module-extraction/) - Refactored to consume 10 pipeline modules via AWS::Include (excludes CloudFormation/CodeDeploy/PostDeploy modules)
- **CodeBuild Container Image Standardization** - CodeBuild image standardized to aws/codebuild/amazonlinux-x86_64-standard:5.0 (Amazon Linux 2023 with Node 22 / Python 3.13) across all pipeline templates for consistency
  - Pipeline: template-pipeline-github.yml - Upgraded from amazonlinux2-x86_64-standard:5.0 (Amazon Linux 2)
  - Pipeline: template-pipeline-build-only.yml - Upgraded from amazonlinux2-x86_64-standard:5.0 (Amazon Linux 2)
- **CodeBuild IAM Permissions Reconciliation** - Added s3:GetBucketLocation permission to CodeBuildServiceRole for reconciled IAM policies across all pipeline templates
  - Pipeline: template-pipeline.yml - Gained s3:GetBucketLocation read-only permission
  - Pipeline: template-pipeline-github.yml - Gained s3:GetBucketLocation read-only permission
- **Management Roles: S3 Module Bucket Read Access** [Spec: 0-0-39-mgmt-roles-s3module-access](.kiro/specs/0-0-39-mgmt-roles-s3module-access/) - Added S3ModuleBucketReadOnly IAM policy statement to enable CloudFormation AWS::Include transform to access module snippets from S3
  - Modules: pipeline-mgmt-role.yml - Added read-only S3 permissions scoped to module bucket and namespace
  - Modules: storage-mgmt-role.yml - Added read-only S3 permissions scoped to module bucket and namespace
  - Modules: network-cloudfront-mgmt-policy.yml - Added read-only S3 permissions scoped to module bucket and namespace
- **Account: prefix-based-infrastructure.yml v0.0.0** [Spec: 0-0-39-cache-data-modularization](.kiro/specs/0-0-39-cache-data-modularization/) - Added opt-in Cache-Data support via the EnableCacheData parameter, consuming the four cache-data modules through AWS::Include with conditional resources and outputs (export names preserved from template-storage-cache-data.yml)

## v0.0.38 (2026-06-12)

### Fixed
- **IAM TagRole/UntagRole Permissions Boundary Fix** [Spec: 0-0-38-iam-tagrole-permissions-boundary-fix](.kiro/specs/0-0-38-iam-tagrole-permissions-boundary-fix/) addresses [#5](https://github.com/63Klabs/atlantis-sam-templates/issues/5)
  - Modules: pipeline-mgmt-role.yml - Extracted `iam:TagRole` and `iam:UntagRole` into separate unconditional statement to prevent denial when PermissionsBoundaryArn is configured
  - Modules: storage-mgmt-role.yml - Same fix applied
- **AllowTransformOperations for Management Roles** [Spec: 0-0-38-mgmt-role-allow-transform-operations](.kiro/specs/0-0-38-mgmt-role-allow-transform-operations/) addresses [#6](https://github.com/63Klabs/atlantis-sam-templates/issues/6)
  - Modules: pipeline-mgmt-role.yml - Added `AllowTransformOperations` statement granting `cloudformation:CreateChangeSet` on AWS-managed transform ARNs to unblock SAM/LanguageExtensions/Include deployments
  - Modules: storage-mgmt-role.yml - Same fix applied
- **Network CloudFront Management Policy Permissions Gaps** [Spec: 0-0-38-network-cloudfront-mgmt-policy-gaps](.kiro/specs/0-0-38-network-cloudfront-mgmt-policy-gaps/) addresses [#8](https://github.com/63Klabs/atlantis-sam-templates/issues/8)
  - Modules: network-cloudfront-mgmt-policy.yml - Added `CloudFrontOriginRequestPolicyRead` statement for Origin Request Policy validation during CloudFront distribution deployments
  - Modules: network-cloudfront-mgmt-policy.yml - Added `ApiGatewayV2ReadApis` statement for API reference validation during ApiMapping creation
  - Modules: network-cloudfront-mgmt-policy.yml - Fixed `S3BucketReadForLogging` resource pattern to use `${Prefix}-*` instead of `${Prefix}-${AccountId}-${Region}-*`, matching actual bucket names that include ProjectId
- **Storage Management Role S3 Pattern Fix** [Spec: 0-0-38-storage-mgmt-role-s3-pattern-fix](.kiro/specs/0-0-38-storage-mgmt-role-s3-pattern-fix/) addresses [#7](https://github.com/63Klabs/atlantis-sam-templates/issues/7)
  - Modules: storage-mgmt-role.yml - Fixed `ManageBucketsByResourcePrefix` S3 resource pattern from `${Prefix}-${AccountId}-${Region}-*` to simplified `${Prefix}-*` wildcard that matches actual bucket names containing ProjectId
  - Modules: storage-mgmt-role.yml - Added `ManageManagedPoliciesByResourcePrefix` statement granting IAM managed policy CRUD operations scoped to `${RolePath}${Prefix}-*`

## v0.0.37 (2026-06-01)

### Added
- **S3 Artifacts Bucket Modules** [Spec: 0-0-37-s3-artifacts-module-extraction](.kiro/specs/0-0-37-s3-artifacts-module-extraction/) - Added account-wide S3 artifacts bucket modules and integration into the account-wide-infrastructure template, providing a shared artifacts bucket accessible by all pipeline roles in the account regardless of prefix
  - Account: account-wide-infrastructure.yml v0.0.0 - Added EnableS3ArtifactsBucket parameter, S3BucketNameOrgPrefix parameter, S3LogBucketName parameter, conditions, module references via AWS::Include, and conditional outputs
  - Modules: s3-artifacts-bucket.yml - New account-wide S3 bucket module with versioning, encryption, lifecycle rules, and conditional logging
  - Modules: s3-artifacts-bucket-policy.yml - New account-wide bucket policy module granting access to all pipeline service roles

## v0.0.36 (2026-05-27)

### Changed
- **Regional S3 Bucket for Module Resolution** [Spec: 0-0-36-add-mapping-for-regional-template-imports](.kiro/specs/0-0-36-add-mapping-for-regional-template-imports/) - Added regional S3 buckets for AWS::Include module resolution, enabling multi-region deployment without manual bucket specification
  - Account: account-wide-infrastructure.yml v0.0.0 - Added S3ModuleNamespace parameter
  - Account: prefix-based-infrastructure.yml v0.0.0 - Added S3ModuleNamespace parameter
  - Service Role: template-service-role-pipeline.yml v0.0.17 - Added S3ModuleNamespace parameter
  - Service Role: template-service-role-network-cloudfront.yml v0.0.0 - Added S3ModuleNamespace parameter
  - Service Role: template-service-role-network-full.yml v0.0.0 - Added S3ModuleNamespace parameter
  - Service Role: template-service-role-storage.yml v0.0.2 - Added S3ModuleNamespace parameter

## v0.0.35 (2026-05-04)

### Fixed
- **Storage: template-storage-s3-oac-for-cloudfront.yml v0.1.2** - Fixed OriginBucketDomainForCloudFront output to use regional S3 domain format (`<bucket>.s3.<region>.amazonaws.com`) instead of global format, preventing 307 redirects for CloudFront distributions using OAC [Spec: 0-0-35-s3-oac-domain-fix](../.kiro/specs/0-0-35-s3-oac-domain-fix/) addresses [#3](https://github.com/63Klabs/atlantis-sam-templates/issues/3)

## v0.0.34 (2026-05-01)

### Changed
- **Network: template-network-route53-cloudfront-s3-apigw.yml v0.0.18** - Added AllViewerExceptHostHeader origin request policy to API Gateway cache behaviors, replacing custom header forwarding via the cache policy with the modern origin request policy approach [Spec: cloudfront-origin-request-policy](../.kiro/specs/0-0-34-cloudfront-origin-request-policy/)

### Deprecated
- **Network: template-network-route53-cloudfront-s3-apigw.yml v0.0.18** - `HeadersToForwardToApi` parameter deprecated; header forwarding is now handled by the AllViewerExceptHostHeader origin request policy [Spec: cloudfront-origin-request-policy](../.kiro/specs/0-0-34-cloudfront-origin-request-policy/)

## v0.0.33 (2026-04-30)

### Added
- **Modules** - Template snipits, which can also be used as modules to insert into your CloudFormation templates, have been added to the repository! These will find their way into other templates to provide consistency and easy maintainability. Currently, there is no versioning. While a previous version can be retrieved from the AWS CLI, since they are still in the S3 bucket, CloudFormation does not support versions. An optimal solution for versioning will be developed later.
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
