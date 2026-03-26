# template-pipeline-github.yml

AWS CodePipeline for automated SAM deployments from GitHub repositories using AWS CodeConnections.

**Version:** v2.0.3  
**Last Updated:** 2026-03-26  
**Template:** [templates/v2/pipeline/template-pipeline-github.yml](../../../../templates/v2/pipeline/template-pipeline-github.yml)

## Overview

This template creates a complete CI/CD pipeline for AWS SAM applications using GitHub as the source repository via AWS CodeConnections (formerly CodeStar Connections). The pipeline automates the entire deployment process from GitHub commits to production deployment.

### Pipeline Stages

1. **Source**: Monitors GitHub repository for changes to specified branch via CodeConnections
2. **Build**: Executes buildspec.yml to build, test, and package the application
3. **Deploy**: Creates and executes CloudFormation changeset to deploy infrastructure

### Key Features

- **GitHub Integration**: Direct integration with GitHub repositories via AWS CodeConnections
- **Automated Triggers**: Pipeline automatically triggers on GitHub commits
- **Build Caching**: Local caching in CodeBuild for faster subsequent builds
- **Flexible Buildspec**: Supports local or S3-hosted buildspec files
- **Comprehensive Notifications**: Email notifications for pipeline start, success, and failure
- **Security**: Least-privilege IAM roles with permissions boundary support
- **Multi-Environment**: Supports DEV, TEST, and PROD deployment environments
- **Lambda Layers**: Automatic access to AWS Lambda Insights and Parameters/Secrets extensions

### Use Cases

- Serverless applications hosted on GitHub
- Teams using GitHub for source control and collaboration
- Projects requiring GitHub Actions integration
- Open source projects with public GitHub repositories
- Organizations standardizing on GitHub for version control

### Prerequisites

- GitHub repository with application code
- AWS CodeConnections connection to GitHub (must be created separately)
- S3 bucket for build artifacts
- (Optional) S3 bucket for static hosting
- (Optional) Permissions boundary policy
- (Optional) External managed policies for additional permissions

> **Important:** You must create a GitHub connection in AWS CodeConnections before deploying this template. The connection ARN is required as a parameter.

## Parameters

### Application Resource Naming

Parameters for naming and organizing pipeline resources.

- [Prefix](#prefix)
- [ProjectId](#projectid)
- [StageId](#stageid)
- [S3BucketNameOrgPrefix](#s3bucketnameorgprefix)
- [RolePath](#rolepath)
- [PermissionsBoundaryArn](#permissionsboundaryarn)

#### Prefix

Prefix prepended to all resources for namespace identification and access control.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | acme |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,6}[a-z0-9]$` |
| Min Length | 2 |
| Max Length | 8 |
| Constraint Description | 2 to 8 characters. Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. Length of Prefix + Project ID should not exceed 28 characters. |

Short, descriptive 2-6 character values work best. Resources are named `<Prefix>-<ProjectId>-<StageId>-<ResourceId>`.

#### ProjectId

Project or Application Identifier.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,24}[a-z0-9]$` |
| Min Length | 2 |
| Max Length | 26 |
| Constraint Description | Minimum of 2 characters (suggested maximum of 20). Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. Length of Prefix + Project ID should not exceed 28 characters. |

If you receive 'S3 bucket name too long' errors, shorten the Project ID or use an S3 Org Prefix.

#### StageId

Alias for the branch, used in resource naming.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,6}[a-z0-9]$` |
| Min Length | 2 |
| Max Length | 8 |
| Constraint Description | 2 to 8 characters. Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. |

Does not need to match RepositoryBranch or DeployEnvironment. Provides shorter names without special characters. For example, branch 'test/feature-98' could use StageId 'tf98'.

#### S3BucketNameOrgPrefix

Optional organization prefix for S3 bucket names to enforce uniqueness.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,18}[a-z0-9]$\|^$` |
| Constraint Description | May be empty or 2 to 20 characters (8 or less recommended). Lower case alphanumeric and dashes. Must start and end with a letter or number. |

By default, buckets include account and region in the name. Use this parameter to specify your own prefix (like an org code) instead.

#### RolePath

Path for IAM Roles and Policies.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\\/([a-zA-Z0-9-_]+[\\/])+$\|^\\/$` |
| Constraint Description | May only contain alphanumeric characters, forward slashes, underscores, and dashes. Must begin and end with a slash. |

Separate applications from users or create separate paths per prefix or application. Examples: `/ws-hello-world-test/` or `/app_role/`

#### PermissionsBoundaryArn

Optional IAM Permissions Boundary policy ARN.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^arn:aws:iam::\\d{12}:policy\\/[\\w+=,.@\\-\\/]*[\\w+=,.@\\-]+$` |
| Constraint Description | Must be empty or a valid IAM Policy ARN in the format: arn:aws:iam::{account_id}:policy/{policy_name} |

Permissions Boundary is a policy attached to a role to further restrict the role's permissions.

### Deployment Environment Information

Parameters for deployment environment configuration.

- [DeployEnvironment](#deployenvironment)
- [S3ArtifactsBucket](#s3artifactsbucket)
- [S3StaticHostBucket](#s3statichostbucket)
- [BuildSpec](#buildspec)

#### DeployEnvironment

Deployment/testing environment designation.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | PROD |
| Allowed Values | DEV, TEST, PROD |
| Constraint Description | Must specify DEV, TEST, or PROD. |

An environment can contain multiple stages. Use this to determine tests, app logging levels, and template conditionals.

**Suggested use:**
- DEV: Local SAM deployment
- TEST: Test/QA deployments
- PROD: Stage, beta, and main/prod deployments

#### S3ArtifactsBucket

Existing S3 bucket name for build artifacts.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$` |
| Constraint Description | May only contain alphanumeric characters, dashes, and must begin and end with a letter or number. |

Must be in the same AWS account and region as the stack.

#### S3StaticHostBucket

Optional existing S3 bucket for static content hosting.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$\|^$` |
| Constraint Description | May only contain alphanumeric characters, dashes, and must begin and end with a letter or number. |

Passed as `S3_STATIC_HOST_BUCKET` environment variable to CodeBuild. Used primarily for hosting static content (JS, CSS, HTML, React, etc.) from S3.

#### BuildSpec

Path to CodeBuild buildspec file (local or S3).

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | application-infrastructure/buildspec.yml |
| Allowed Pattern | `^s3:\\/\\/[a-zA-Z0-9][a-zA-Z0-9\\-]{1,61}[a-zA-Z0-9]\\/.*$\|^([a-zA-Z0-9][a-zA-Z0-9_\\-\\/]*)?(buildspec\\.yml)$\|^$` |
| Constraint Description | Must be a valid S3 URI or a local path ending with 'buildspec.yml'. |

Best practice is to have a single buildspec file for all instances of an application.

### External Resources

Parameters for external resources and notifications.

- [ParameterStoreHierarchy](#parameterstorehierarchy)
- [AlarmNotificationEmail](#alarmnotificationemail)
- [CloudFormationSvcRoleIncludeManagedPolicyArns](#cloudformationsvcr oleincludemanagedpolicyarns)
- [CodeBuildSvcRoleIncludeManagedPolicyArns](#codebuildsvcr oleincludemanagedpolicyarns)

#### ParameterStoreHierarchy

SSM Parameter Store hierarchy for application parameters.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\\/([a-zA-Z0-9_.\\-]*[\\/])*$\|^$` |
| Constraint Description | Must only contain alpha-numeric, dashes, underscores, or slashes. Must be a single slash or begin and end with a slash. |

Parameters specific to the application may be organized within a hierarchy. For example, `/Finance/ops/` would generate `/Finance/ops/<DeployEnvironment>/<Prefix>-<ProjectId>-<StageId>/<parameterName>`.

#### AlarmNotificationEmail

Email address for pipeline notifications.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[\\w\\-\\.]+@([\\w\\-]+\\.)+[\\w\\-]{2,4}$` |
| Constraint Description | A valid email address |

Email address to send notifications to when pipeline events occur. Be sure to check the inbox for SNS subscription confirmation.

#### CloudFormationSvcRoleIncludeManagedPolicyArns

Additional managed policies for CloudFormation service role.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^arn:aws:iam::\\d{12}:policy\\/[a-zA-Z0-9_\\-]+(?:\\/[a-zA-Z0-9_\\-]+)*$` |
| Constraint Description | Must be an empty string or comma delimited valid IAM Policy ARNs |

List of IAM Managed Policy ARNs to add to the CloudFormation Service Role.

#### CodeBuildSvcRoleIncludeManagedPolicyArns

Additional managed policies for CodeBuild service role.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^arn:aws:iam::\\d{12}:policy\\/[a-zA-Z0-9_\\-]+(?:\\/[a-zA-Z0-9_\\-]+)*$` |
| Constraint Description | Must be an empty string or comma delimited valid IAM Policy ARNs |

List of IAM Managed Policy ARNs to add to the CodeBuild Service Role.

### Code Repository

Parameters for GitHub repository configuration.

- [Repository](#repository)
- [RepositoryBranch](#repositorybranch)
- [GitHubConnectionArn](#githubconnectionarn)

#### Repository

GitHub repository in owner/repository format.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[a-zA-Z0-9][a-zA-Z0-9_\\-]{0,62}[a-zA-Z0-9]\\/[a-zA-Z0-9][a-zA-Z0-9_\\-]{0,62}[a-zA-Z0-9]$` |
| Min Length | 2 |
| Constraint Description | Must be a valid owner/repository format for GitHub |

For GitHub repositories, use the format 'username/my-repo' or 'organization/my-repo'.

#### RepositoryBranch

Branch of GitHub repository to monitor.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | main |
| Allowed Pattern | `^[a-zA-Z0-9][a-zA-Z0-9_\\-\\/]{0,14}[a-zA-Z0-9]$` |
| Constraint Description | Must be a valid branch name |

Typically this is the same name as the stage, but may be different if there are multiple deploys operating off the same branch.

#### GitHubConnectionArn

ARN of the GitHub connection in AWS CodeConnections.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^arn:aws:codeconnections:\\S+:\\d{12}:connection\\/\\S+$` |
| Constraint Description | A valid ARN for a GitHub connection |

The ARN of the GitHub connection to use for the repository. You must create a GitHub connection first in AWS CodeConnections. The ARN is in the connection details page.

> **Note:** To create a GitHub connection, go to AWS CodeConnections in the AWS Console, create a new connection, and authorize it with your GitHub account. Copy the connection ARN for use in this parameter.

## Resources

This template creates the following resources:

- [SourceEventServiceRole](#sourceeventservicerole) - AWS::IAM::Role (Conditional: IsNotDevelopment)
- [CodePipelineServiceRole](#codepipelineservicerole) - AWS::IAM::Role (Conditional: IsNotDevelopment)
- [CodeBuildServiceRole](#codebuildservicerole) - AWS::IAM::Role (Conditional: IsNotDevelopment)
- [CodeDeployServiceRole](#codedeployservicerole) - AWS::IAM::Role
- [CloudFormationSvcRole](#cloudformationsvcr ole) - AWS::IAM::Role
- [CodeBuildProject](#codebuildproject) - AWS::CodeBuild::Project (Conditional: IsNotDevelopment)
- [CodeBuildLogGroup](#codebuildloggroup) - AWS::Logs::LogGroup (Conditional: IsNotDevelopment)
- [ProjectPipeline](#projectpipeline) - AWS::CodePipeline::Pipeline (Conditional: IsNotDevelopment)
- [PipelineNotificationTopic](#pipelinenotificationtopic) - AWS::SNS::Topic
- [PipelineStartedRule](#pipelinestartedrule) - AWS::Events::Rule
- [PipelineSucceededRule](#pipelinesucceededrule) - AWS::Events::Rule
- [PipelineFailedRule](#pipelinefailedrule) - AWS::Events::Rule
- [PipelineNotificationTopicPolicy](#pipelinenotificationtopicpolicy) - AWS::SNS::TopicPolicy

### SourceEventServiceRole

Type: AWS::IAM::Role  
Condition: IsNotDevelopment

Service role that allows EventBridge to trigger CodePipeline execution. This role has permission to start the pipeline execution.

**Key Properties:**
- Allows events.amazonaws.com to assume the role
- Grants codepipeline:StartPipelineExecution permission for the specific pipeline

### CodePipelineServiceRole

Type: AWS::IAM::Role  
Condition: IsNotDevelopment

Service role for CodePipeline to access resources during pipeline execution.

**Key Permissions:**
- **Build Phase**: Full access to CodeBuild project and report groups
- **Deploy Phase**: Full access to CloudFormation stack operations
- **Artifacts**: Read/write access to S3 artifacts bucket
- **IAM**: PassRole permission for CloudFormation service role
- **CodeConnections**: UseConnection permission for GitHub connection

> **Important:** This role includes permissions for both CodeConnections and the deprecated CodeStar Connections. The Pipeline Source Stage currently only works with CodeStar Connections provider, though CodeConnections is the recommended approach.

### CodeBuildServiceRole

Type: AWS::IAM::Role  
Condition: IsNotDevelopment

Service role for CodeBuild to access resources during the build phase.

**Key Permissions:**
- **Logs**: Full access to CodeBuild log group
- **Artifacts**: Read/write access to S3 artifacts bucket
- **SSM**: Read/write access to Parameter Store hierarchy
- **S3 Assets**: Copy assets to S3 buckets by path, application tag, or deployment tag
- **Static Host**: Access to S3StaticHostBucket if specified
- **Remote Buildspec**: Access to S3-hosted buildspec file if specified

### CodeDeployServiceRole

Type: AWS::IAM::Role

Service role passed to application infrastructure for Lambda function deployments.

**Key Properties:**
- Allows codedeploy.amazonaws.com to assume the role
- Attached managed policy: AWSCodeDeployRoleForLambda

### CloudFormationSvcRole

Type: AWS::IAM::Role

Service role for CloudFormation to create and manage application infrastructure resources.

**Key Permissions:**
- **IAM**: Full access to worker roles and policies for this deployment
- **CloudFormation**: Full access to application stack and transforms
- **CodeDeploy**: Full CRUD for deployment resources
- **Artifacts**: Read/write access to S3 artifacts bucket
- **API Gateway**: Full CRUD with tag-based scoping
- **EventBridge**: Full CRUD for rules and schedules
- **SQS/SNS**: Full CRUD for queues and topics
- **Step Functions**: Full CRUD for state machines
- **S3**: Full CRUD for deployment-specific buckets
- **Lambda**: Full CRUD for functions, layers, and event source mappings
- **DynamoDB**: Full CRUD for tables
- **CloudWatch**: Limited CRUD for dashboards, alarms, and log groups
- **SSM**: Read-only access to Parameter Store
- **Lambda Layers**: Access to AWS-provided Lambda Insights and Parameters/Secrets extensions

### CodeBuildProject

Type: AWS::CodeBuild::Project  
Condition: IsNotDevelopment

CodeBuild project for building and packaging the SAM application.

**Key Properties:**
- **Compute**: BUILD_GENERAL1_SMALL Linux container
- **Image**: aws/codebuild/amazonlinux2-x86_64-standard:5.0 (Node 20, Python 3.12)
- **Caching**: Local custom cache for faster builds
- **Artifacts**: Packaged as ZIP from CodePipeline
- **Environment Variables**: Comprehensive set including AWS_REGION, PREFIX, PROJECT_ID, STAGE_ID, DEPLOY_ENVIRONMENT, etc.

### CodeBuildLogGroup

Type: AWS::Logs::LogGroup  
Condition: IsNotDevelopment

CloudWatch log group for CodeBuild project logs with 90-day retention policy.

### ProjectPipeline

Type: AWS::CodePipeline::Pipeline  
Condition: IsNotDevelopment

The main CodePipeline that orchestrates the entire CI/CD workflow.

**Pipeline Structure:**
1. **Source Stage**: Retrieves code from GitHub repository via CodeConnections
2. **Build Stage**: Executes CodeBuild project to build and package
3. **Deploy Stage**: 
   - GenerateChangeSet: Creates CloudFormation changeset
   - ExecuteChangeSet: Executes the changeset to deploy infrastructure

**Key Properties:**
- Source provider: CodeStarSourceConnection (deprecated but required for functionality)
- Connection: Uses GitHubConnectionArn parameter
- Artifact store: S3ArtifactsBucket
- Service role: CodePipelineServiceRole

> **Note:** The Source stage uses CodeStarSourceConnection provider (deprecated) instead of CodeConnections because the Pipeline Source Stage currently only works with CodeStar. AWS recommends using CodeConnections for new connections, but the pipeline configuration must use the deprecated provider name.

### PipelineNotificationTopic

Type: AWS::SNS::Topic

SNS topic for pipeline execution notifications with email subscription.

### PipelineStartedRule

Type: AWS::Events::Rule

EventBridge rule that sends notification when pipeline execution starts.

**Notification Format:**
- Subject: `Pipeline <pipeline-name> Started`
- Message body uses labeled fields on separate lines (Status, Pipeline, Execution ID, Time, Console Link) with blank-line separation between the header summary and detail fields

### PipelineSucceededRule

Type: AWS::Events::Rule

EventBridge rule that sends notification when pipeline execution succeeds.

**Notification Format:**
- Subject: `Pipeline <pipeline-name> Succeeded`
- Message body uses labeled fields on separate lines (Status, Pipeline, Execution ID, Time, Console Link) with blank-line separation between the header summary and detail fields

### PipelineFailedRule

Type: AWS::Events::Rule

EventBridge rule that sends notification when pipeline execution fails.

**Notification Format:**
- Subject: `ALERT: Pipeline <pipeline-name> Failed`
- Message body uses labeled fields on separate lines (Status, Pipeline, Execution ID, Time, Console Link) with blank-line separation between the header summary and detail fields
- Includes call-to-action: "Please check the pipeline for errors."

### PipelineNotificationTopicPolicy

Type: AWS::SNS::TopicPolicy

Policy that allows EventBridge to publish messages to the notification topic.

## Outputs

### ProjectPipeline

Condition: IsNotDevelopment

Direct link to the CodePipeline in AWS Console.

**Value:** `https://${AWS::Region}.console.aws.amazon.com/codesuite/codepipeline/pipelines/${Prefix}-${ProjectId}-${StageId}-Pipeline/view?region=${AWS::Region}`

### Repository

Direct link to the GitHub repository.

**Value:** `https://github.com/${Repository}`

## Conditions

The template uses several conditions to control resource creation:

- **IsNotDevelopment**: True when DeployEnvironment is not "DEV"
- **UseS3BucketNameOrgPrefix**: True when S3BucketNameOrgPrefix is not empty
- **HasPermissionsBoundaryArn**: True when PermissionsBoundaryArn is not empty
- **HasS3StaticHostBucket**: True when S3StaticHostBucket is not empty
- **HasS3BuildSpecLocation**: True when BuildSpec starts with "s3:"
- **UseDefaultBuildSpecLocation**: True when BuildSpec is empty
- **HasManagedPoliciesForCloudFormationSvcRole**: True when CloudFormationSvcRoleIncludeManagedPolicyArns is not empty
- **HasManagedPoliciesForCodeBuildSvcRole**: True when CodeBuildSvcRoleIncludeManagedPolicyArns is not empty

## Examples

### Basic GitHub Deployment

```yaml
Parameters:
  Prefix: "acme"
  ProjectId: "myapp"
  StageId: "prod"
  DeployEnvironment: "PROD"
  S3ArtifactsBucket: "aws-sam-cli-managed-default-samclisourcebucket-abc123"
  BuildSpec: "application-infrastructure/buildspec.yml"
  AlarmNotificationEmail: "devops@example.com"
  Repository: "myorg/my-serverless-app"
  RepositoryBranch: "main"
  GitHubConnectionArn: "arn:aws:codeconnections:us-east-1:123456789012:connection/abc123-def456"
```

### With Static Hosting

```yaml
Parameters:
  Prefix: "acme"
  ProjectId: "webapp"
  StageId: "prod"
  DeployEnvironment: "PROD"
  S3ArtifactsBucket: "aws-sam-cli-managed-default-samclisourcebucket-abc123"
  S3StaticHostBucket: "acme-webapp-static-content"
  AlarmNotificationEmail: "devops@example.com"
  Repository: "myorg/webapp"
  RepositoryBranch: "main"
  GitHubConnectionArn: "arn:aws:codeconnections:us-east-1:123456789012:connection/abc123-def456"
```

## Troubleshooting

### GitHub Connection Issues

**Symptom:** Pipeline fails to retrieve source from GitHub.

**Possible Causes:**
- GitHub connection not authorized
- Connection ARN incorrect
- Repository or branch doesn't exist
- Insufficient permissions on GitHub repository

**Solutions:**
1. Verify GitHub connection is in "Available" status in AWS CodeConnections
2. Re-authorize the connection if needed
3. Verify Repository parameter matches GitHub repository (owner/repo format)
4. Check GitHub repository permissions allow AWS access

### Pipeline Not Triggering

**Symptom:** Pipeline doesn't start when code is pushed to GitHub.

**Possible Causes:**
- GitHub webhooks not configured
- Connection not properly authorized
- Branch name doesn't match parameter

**Solutions:**
1. Check GitHub webhooks are configured for the repository
2. Verify connection is authorized and active
3. Manually trigger pipeline to test if issue is with automatic triggering

### Build Stage Fails

**Symptom:** Build stage fails with errors in CodeBuild logs.

**Solutions:**
1. Review CodeBuild logs in CloudWatch
2. Verify buildspec.yml syntax and commands
3. Check CodeBuildServiceRole has necessary permissions
4. Test build locally using SAM CLI

### Deploy Stage Fails

**Symptom:** Deploy stage fails during changeset creation or execution.

**Solutions:**
1. Review CloudFormation changeset for errors
2. Check CloudFormationSvcRole has permissions for all resources
3. Verify parameter overrides match template parameters

## Related Templates

This template is commonly used with:

- **Service Role Templates**: 
  - [template-service-role-pipeline.yml](../service-role/template-service-role-pipeline-README.md)

- **Storage Templates**:
  - [template-storage-s3-artifacts.yml](../storage/template-storage-s3-artifacts-README.md)
  - [template-storage-s3-devops.yml](../storage/template-storage-s3-devops-README.md)

- **Application Infrastructure**: Your SAM template being deployed by the pipeline

## Use With

- Application Infrastructure (API Gateway, Event Bridge, Lambda, Step Functions, S3, DynamoDB, etc)
- OPTIONAL: Route53 and CloudFront for custom domains

## Security Considerations

1. **GitHub Connection Security**: GitHub connections use OAuth for secure authentication
2. **Least Privilege**: All IAM roles follow least-privilege principles
3. **Permissions Boundaries**: Support for permissions boundaries to enforce organizational policies
4. **Resource Tagging**: All resources tagged with atlantis:ApplicationDeploymentId

## Cost Considerations

**Monthly Costs (approximate):**
- CodePipeline: $1 per active pipeline
- CodeBuild: $0.005 per build minute (BUILD_GENERAL1_SMALL)
- S3: Storage costs for artifacts
- CloudWatch Logs: $0.50 per GB ingested + $0.03 per GB stored
- SNS: $0.50 per million notifications (minimal)
- CodeConnections: No additional charge

## Additional Resources

- [AWS CodeConnections Documentation](https://docs.aws.amazon.com/codeconnections/latest/userguide/)
- [AWS CodePipeline User Guide](https://docs.aws.amazon.com/codepipeline/latest/userguide/)
- [AWS CodeBuild User Guide](https://docs.aws.amazon.com/codebuild/latest/userguide/)
- [GitHub Repository](https://github.com/63klabs/atlantis-cfn-template-repo-for-serverless-deployments/)
