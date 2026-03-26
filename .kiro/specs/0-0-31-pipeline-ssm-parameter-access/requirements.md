# Requirements Document

## Introduction

The pipeline CloudFormation template (`template-pipeline.yml`) deploys application infrastructure via CloudFormation using the `CloudFormationSvcRole`. When application templates use the `{{resolve:ssm:...}}` dynamic reference syntax to resolve public AWS SSM parameters (e.g., `/aws/service/aws-parameters-and-secrets-lambda-extension/x86/latest`), CloudFormation requires `ssm:GetParameter` permission on those public parameter paths. Currently, the `CloudFormationSvcRole` only has SSM read access scoped to the application's own parameter store hierarchy, causing deployments to fail when resolving public AWS SSM parameters. This feature adds the necessary SSM permissions to the `CloudFormationSvcRole` so that CloudFormation can resolve public AWS SSM parameters during stack deployments.

## Glossary

- **CloudFormationSvcRole**: The IAM role (`CloudFormationSvcRole` resource in `template-pipeline.yml`) assumed by CloudFormation when creating and managing the application infrastructure stack. This role dictates what resources CloudFormation can create and manage.
- **Pipeline_Template**: The CloudFormation template at `templates/v2/pipeline/template-pipeline.yml` that defines the CI/CD pipeline infrastructure including IAM roles, CodeBuild projects, and the CodePipeline itself.
- **Service_Role_Template**: The CloudFormation template at `templates/v2/service-role/template-service-role-pipeline.yml` that defines the prefix-based IAM service role used to deploy the Pipeline_Template itself.
- **Public_SSM_Parameter**: An SSM parameter published by AWS under the `/aws/service/` path hierarchy. These parameters contain AWS-managed values such as Lambda layer ARNs, AMI IDs, and extension versions. They are read-only and available in all AWS accounts.
- **Dynamic_Reference**: A CloudFormation syntax pattern `{{resolve:ssm:<parameter-path>}}` that instructs CloudFormation to retrieve a value from SSM Parameter Store at stack create or update time.
- **ParameterStoreHierarchy**: An existing parameter in the Pipeline_Template that defines the organizational path prefix for application-specific SSM parameters.

## Requirements

### Requirement 1: CloudFormationSvcRole Public SSM Parameter Read Access

**User Story:** As a developer, I want the CloudFormationSvcRole to have permission to read public AWS SSM parameters, so that I can use `{{resolve:ssm:...}}` dynamic references in my application CloudFormation templates to resolve AWS-published parameter values during deployment.

#### Acceptance Criteria

1. THE CloudFormationSvcRole SHALL have `ssm:GetParameter` permission on SSM parameters matching the path pattern `/aws/service/*` in the deployment region and account.
2. THE CloudFormationSvcRole SHALL have `ssm:GetParameters` permission on SSM parameters matching the path pattern `/aws/service/*` in the deployment region and account.
3. WHEN a CloudFormation application template uses a Dynamic_Reference such as `{{resolve:ssm:/aws/service/aws-parameters-and-secrets-lambda-extension/x86/latest}}`, THE CloudFormationSvcRole SHALL allow CloudFormation to resolve the parameter value during stack creation or update.
4. THE CloudFormationSvcRole SHALL retain all existing SSM permissions for the application-specific ParameterStoreHierarchy without modification.
5. THE Pipeline_Template SHALL define the public SSM parameter read permissions as a separate IAM policy statement with a descriptive Sid distinct from the existing `SSMParameterStoreReadThisDeploymentOnly` statement.

### Requirement 2: Service Role Template Public SSM Parameter Read Access

**User Story:** As a developer deploying the pipeline stack, I want the prefix-based CloudFormation service role to have permission to pass through SSM-related IAM permissions, so that the pipeline stack can be created and updated with the new SSM policy statements without deployment failures.

#### Acceptance Criteria

1. THE Service_Role_Template SHALL allow the `PrefixBasedCloudFormationPipelineMgmtServiceRole` to manage IAM policies that include `ssm:GetParameter` and `ssm:GetParameters` actions on public SSM parameter resources.
2. WHEN the Pipeline_Template is deployed or updated with the new public SSM parameter permissions, THE Service_Role_Template SHALL permit CloudFormation to create and update the CloudFormationSvcRole with the expanded SSM policy statements.

### Requirement 3: Least Privilege Scoping for Public SSM Access

**User Story:** As a security-conscious operator, I want the public SSM parameter permissions to be scoped to only AWS-published parameters, so that the principle of least privilege is maintained.

#### Acceptance Criteria

1. THE CloudFormationSvcRole public SSM parameter permissions SHALL be scoped to the resource ARN pattern `arn:aws:ssm:<region>:<account>:parameter/aws/service/*` using the stack's region and account references.
2. THE CloudFormationSvcRole public SSM parameter permissions SHALL be limited to read-only actions (`ssm:GetParameter` and `ssm:GetParameters`) and SHALL NOT include write actions such as `ssm:PutParameter` or `ssm:DeleteParameter`.
3. THE CloudFormationSvcRole public SSM parameter permissions SHALL NOT grant access to SSM parameters outside the `/aws/service/*` path hierarchy.
