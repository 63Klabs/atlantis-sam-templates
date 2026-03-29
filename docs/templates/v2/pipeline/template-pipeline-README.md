# template-pipeline.yml

Full-featured AWS CodePipeline for automated SAM deployments from AWS CodeCommit with optional PostDeploy stage.

**Version:** v2.0.20  
**Last Updated:** 2026-03-26  
**Template:** [templates/v2/pipeline/template-pipeline.yml](../../../../templates/v2/pipeline/template-pipeline.yml)

## Overview

This template creates a complete CI/CD pipeline for AWS SAM applications using AWS CodeCommit as the source repository. The pipeline automates the entire deployment process from code commit to production deployment, with an optional PostDeploy stage for integration testing and configuration export.

### Pipeline Stages

1. **Source**: Monitors CodeCommit repository for changes to specified branch
2. **Build**: Executes buildspec.yml to build, test, and package the application
3. **Deploy**: Creates and executes CloudFormation changeset to deploy infrastructure
4. **PostDeploy** (Optional): Runs post-deployment tasks like integration tests or API documentation export

### Key Features

- **Automated Triggers**: EventBridge rule automatically triggers pipeline on repository changes
- **Build Caching**: Local caching in CodeBuild for faster subsequent builds
- **Flexible Buildspec**: Supports local or S3-hosted buildspec files
- **PostDeploy Stage**: Optional stage for integration tests, validation, and artifact export
- **Comprehensive Notifications**: Email notifications for pipeline start, success, and failure
- **Security**: Least-privilege IAM roles with permissions boundary support
- **Multi-Environment**: Supports DEV, TEST, and PROD deployment environments
- **Lambda Layers**: Automatic access to AWS Lambda Insights and Parameters/Secrets extensions

### Use Cases

- Serverless applications with Lambda, API Gateway, DynamoDB, Step Functions, etc.
- Applications requiring post-deployment validation or integration testing
- Projects needing automated API documentation export (e.g., OpenAPI specs)
- Multi-stage deployments with environment-specific configurations
- Applications using AWS CodeCommit for source control

### Prerequisites

- AWS CodeCommit repository
- S3 bucket for build artifacts
- (Optional) S3 bucket for static hosting
- (Optional) Permissions boundary policy
- (Optional) External managed policies for additional permissions

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

By default, buckets include account and region in the name. Use this parameter to specify your own prefix (like an org code) instead. Note that this length is shared with the recommended 20 characters for Resource Identifiers.

#### RolePath

Path for IAM Roles and Policies.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\\/([a-zA-Z0-9-_]+[\\/])+$\|^\\/$` |
| Constraint Description | May only contain alphanumeric characters, forward slashes, underscores, and dashes. Must begin and end with a slash. |

Separate applications from users or create separate paths per prefix or application. Specific paths may be required by permission boundaries. Examples: `/ws-hello-world-test/` or `/app_role/`

#### PermissionsBoundaryArn

Optional IAM Permissions Boundary policy ARN.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^arn:aws:iam::\\d{12}:policy\\/[\\w+=,.@\\-\\/]*[\\w+=,.@\\-]+$` |
| Constraint Description | Must be empty or a valid IAM Policy ARN in the format: arn:aws:iam::{account_id}:policy/{policy_name} |

Permissions Boundary is a policy attached to a role to further restrict the role's permissions. Your organization may or may not require boundaries.

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

An environment can contain multiple stages. For example, 'test' and 't98' stages would be in 'TEST' environment, while 'beta' and 'prod' stages would deploy to 'PROD'. Use this to determine tests, app logging levels, and template conditionals.

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

Must be in the same AWS account and region as the stack. When you first use SAM deploy, it typically creates one in the format `aws-sam-cli-managed-default-samclisourcebucket-*`.

#### S3StaticHostBucket

Optional existing S3 bucket for static content hosting.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$\|^$` |
| Constraint Description | May only contain alphanumeric characters, dashes, and must begin and end with a letter or number. |

Passed as `S3_STATIC_HOST_BUCKET` environment variable to CodeBuild. Can be left blank if CodeBuild will programmatically construct the bucket name or doesn't need this value. Used primarily for hosting static content (JS, CSS, HTML, React, etc.) from S3.

#### BuildSpec

Path to CodeBuild buildspec file (local or S3).

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | application-infrastructure/buildspec.yml |
| Allowed Pattern | `^s3:\\/\\/[a-zA-Z0-9][a-zA-Z0-9\\-]{1,61}[a-zA-Z0-9]\\/.*$\|^([a-zA-Z0-9][a-zA-Z0-9_\\-\\/]*)?(buildspec\\.yml)$\|^$` |
| Constraint Description | Must be a valid S3 URI or a local path ending with 'buildspec.yml'. For example, 'buildspec.yml', 'application-infrastructure/buildspec.yml' or 's3://mybucket/buildspec.yml'. If empty, buildspec.yml at root of repo will be sought. |

Best practice is to have a single buildspec file for all instances of an application. This option exists if you cannot store your buildspec file with your source code OR wish to use a central buildspec for a group of deployments.

### Post Deploy Environment Information

Parameters for optional PostDeploy stage configuration.

> **Important:** The PostDeploy stage is designed for tasks that require the application infrastructure to be deployed first, such as integration tests, configuration validation, or exporting configurations. Pre-deployment tasks should be done in the Build stage.

- [PostDeployStageEnabled](#postdeploystageenabled)
- [PostDeployS3StaticHostBucket](#postdeploys3statichostbucket)
- [PostDeployBuildSpec](#postdeploybuildspec)

#### PostDeployStageEnabled

Controls whether the PostDeploy stage is created.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | false |
| Allowed Values | true, false |
| Constraint Description | Must specify true or false. |

When enabled, creates a final pipeline stage to run integration tests, configuration checks, or export configurations (such as OpenAPI specifications from API Gateway). Setting to 'true' creates PostDeployServiceRole, PostDeployProject, PostDeployLogGroup, and adds the PostDeploy stage to the pipeline.

**Usage Patterns:**
1. **API Documentation Export**: Export OpenAPI specs from deployed API Gateway to S3
2. **Integration Testing**: Run integration tests against deployed endpoints
3. **Configuration Validation**: Validate deployed resources meet requirements
4. **Disabled** (default): No PostDeploy resources created, pipeline has only 3 stages

#### PostDeployS3StaticHostBucket

Optional S3 bucket for PostDeploy stage artifacts.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$\|^$` |
| Constraint Description | May only contain alphanumeric characters, dashes, and must begin and end with a letter or number. |

Passed as `POST_DEPLOY_S3_STATIC_HOST_BUCKET` environment variable to the PostDeploy CodeBuild project. Used primarily to store artifacts that will be picked up by another process such as static API specification documentation or exported configuration files.

#### PostDeployBuildSpec

Path to PostDeploy buildspec file (local or S3).

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | application-infrastructure/buildspec-postdeploy.yml |
| Allowed Pattern | `^s3:\\/\\/[a-zA-Z0-9][a-zA-Z0-9\\-]{1,61}[a-zA-Z0-9]\\/.*$\|^([a-zA-Z0-9][a-zA-Z0-9_\\-\\/]*)?(buildspec-postdeploy\\.yml)$\|^$` |
| Constraint Description | Must be a valid S3 URI or a local path ending with 'buildspec-postdeploy.yml'. For example, 'buildspec-postdeploy.yml', 'application-infrastructure/buildspec-postdeploy.yml' or 's3://mybucket/buildspec-postdeploy.yml'. May not be empty. |

Best practice is to have a single file for all instances of an application. Default is 'application-infrastructure/buildspec-postdeploy.yml', and leaving blank will use the SAM default buildspec-postdeploy.yml in the root of the repository.

### External Resources

Parameters for external resources and notifications.

- [ParameterStoreHierarchy](#parameterstorehierarchy)
- [AlarmNotificationEmail](#alarmnotificationemail)
- [CloudFormationSvcRoleIncludeManagedPolicyArns](#cloudformationsvcr oleincludemanagedpolicyarns)
- [CodeBuildSvcRoleIncludeManagedPolicyArns](#codebuildsvcr oleincludemanagedpolicyarns)
- [PostDeploySvcRoleIncludeManagedPolicyArns](#postdeploysvcr oleincludemanagedpolicyarns)

#### ParameterStoreHierarchy

SSM Parameter Store hierarchy for application parameters.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\\/([a-zA-Z0-9_.\\-]*[\\/])*$\|^$` |
| Constraint Description | Must only contain alpha-numeric, dashes, underscores, or slashes. Must be a single slash or begin and end with a slash. (/Finance/, /Finance/ops/, or /) |

Parameters specific to the application may be organized within a hierarchy based on your organizational or operations structure. For example, `/Finance/ops/` would generate `/Finance/ops/<DeployEnvironment>/<Prefix>-<ProjectId>-<StageId>/<parameterName>`.

#### AlarmNotificationEmail

Email address for pipeline notifications.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[\\w\\-\\.]+@([\\w\\-]+\\.)+[\\w\\-]{2,4}$` |
| Constraint Description | A valid email address |

Email address to send notifications to when pipeline events occur (started, succeeded, failed). Be sure to check the inbox as you will need to confirm the SNS subscription.

#### CloudFormationSvcRoleIncludeManagedPolicyArns

Additional managed policies for CloudFormation service role.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^arn:aws:iam::\\d{12}:policy\\/[a-zA-Z0-9_\\-]+(?:\\/[a-zA-Z0-9_\\-]+)*$` |
| Constraint Description | Must be an empty string or comma delimited valid IAM Policy ARNs in the format: arn:aws:iam::{account_id}:policy/{policy_name} |

List of IAM Managed Policy ARNs to add to the CloudFormation Service Role. Use when external resources provide policies to interact with them.

#### CodeBuildSvcRoleIncludeManagedPolicyArns

Additional managed policies for CodeBuild service role.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^arn:aws:iam::\\d{12}:policy\\/[a-zA-Z0-9_\\-]+(?:\\/[a-zA-Z0-9_\\-]+)*$` |
| Constraint Description | Must be an empty string or comma delimited valid IAM Policy ARNs in the format: arn:aws:iam::{account_id}:policy/{policy_name} |

List of IAM Managed Policy ARNs to add to the CodeBuild Service Role. Use when external resources provide policies to interact with them.

#### PostDeploySvcRoleIncludeManagedPolicyArns

Additional managed policies for PostDeploy service role.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^arn:aws:iam::\\d{12}:policy\\/[a-zA-Z0-9_\\-]+(?:\\/[a-zA-Z0-9_\\-]+)*$` |
| Constraint Description | Must be an empty string or comma delimited valid IAM Policy ARNs in the format: arn:aws:iam::{account_id}:policy/{policy_name} |

List of IAM Managed Policy ARNs to add to the Post Deploy Stage Service Role. Use when external resources provide policies to interact with them.

### Code Repository

Parameters for source code repository configuration.

- [Repository](#repository)
- [RepositoryBranch](#repositorybranch)

#### Repository

Source CodeCommit repository name.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[a-zA-Z0-9][a-zA-Z0-9_\\-]{0,62}[a-zA-Z0-9]$` |
| Min Length | 2 |
| Constraint Description | Must be a valid CodeCommit repository name. Must be at least 2 characters long. |

This is the name of the repository that will be used to trigger the pipeline. It must be a valid CodeCommit repository name.

#### RepositoryBranch

Branch of CodeCommit to monitor.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | main |
| Allowed Pattern | `^[a-zA-Z0-9][a-zA-Z0-9_\\-\\/]{0,14}[a-zA-Z0-9]$` |
| Constraint Description | Must be a valid CodeCommit branch name |

Typically this is the same name as the stage, but may be different if there are multiple deploys operating off the same branch.


## Resources

This template creates the following resources:

- [SourceEventServiceRole](#sourceeventservicerole) - AWS::IAM::Role (Conditional: IsNotDevelopment)
- [CodePipelineServiceRole](#codepipelineservicerole) - AWS::IAM::Role (Conditional: IsNotDevelopment)
- [CodeBuildServiceRole](#codebuildservicerole) - AWS::IAM::Role (Conditional: IsNotDevelopment)
- [PostDeployServiceRole](#postdeployservicerole) - AWS::IAM::Role (Conditional: IsPostDeployEnabledAndNotDev)
- [CodeDeployServiceRole](#codedeployservicerole) - AWS::IAM::Role
- [CloudFormationSvcRole](#cloudformationsvcr ole) - AWS::IAM::Role
- [SourceEvent](#sourceevent) - AWS::Events::Rule (Conditional: IsNotDevelopment)
- [CodeBuildProject](#codebuildproject) - AWS::CodeBuild::Project (Conditional: IsNotDevelopment)
- [CodeBuildLogGroup](#codebuildloggroup) - AWS::Logs::LogGroup (Conditional: IsNotDevelopment)
- [PostDeployProject](#postdeployproject) - AWS::CodeBuild::Project (Conditional: IsPostDeployEnabledAndNotDev)
- [PostDeployLogGroup](#postdeployloggroup) - AWS::Logs::LogGroup (Conditional: IsPostDeployEnabledAndNotDev)
- [ProjectPipeline](#projectpipeline) - AWS::CodePipeline::Pipeline (Conditional: IsNotDevelopment)
- [PipelineNotificationTopic](#pipelinenotificationtopic) - AWS::SNS::Topic
- [PipelineStartedRule](#pipelinestartedrule) - AWS::Events::Rule
- [PipelineSucceededRule](#pipelinesucceededrule) - AWS::Events::Rule
- [PipelineFailedRule](#pipelinefailedrule) - AWS::Events::Rule
- [PipelineNotificationTopicPolicy](#pipelinenotificationtopicpolicy) - AWS::SNS::TopicPolicy

### SourceEventServiceRole

Type: AWS::IAM::Role  
Condition: IsNotDevelopment

Service role that allows EventBridge to trigger CodePipeline execution when repository changes are detected. This role has permission to start the pipeline execution.

**Key Properties:**
- Allows events.amazonaws.com to assume the role
- Grants codepipeline:StartPipelineExecution permission for the specific pipeline
- Scoped to the deployment-specific pipeline ARN

### CodePipelineServiceRole

Type: AWS::IAM::Role  
Condition: IsNotDevelopment

Service role for CodePipeline to access resources during pipeline execution. This role orchestrates the entire pipeline workflow.

**Key Permissions:**
- **Source Phase**: Read access to CodeCommit repository
- **Build Phase**: Full access to CodeBuild project and report groups
- **Deploy Phase**: Full access to CloudFormation stack operations
- **Artifacts**: Read/write access to S3 artifacts bucket
- **IAM**: PassRole permission for CloudFormation service role

### CodeBuildServiceRole

Type: AWS::IAM::Role  
Condition: IsNotDevelopment

Service role for CodeBuild to access resources during the build phase. This role has comprehensive permissions for building and packaging SAM applications.

**Key Permissions:**
- **Logs**: Full access to CodeBuild log group
- **Artifacts**: Read/write access to S3 artifacts bucket
- **SSM**: Read/write access to Parameter Store hierarchy
- **S3 Assets**: Copy assets to S3 buckets by path, application tag, or deployment tag
- **Static Host**: Access to S3StaticHostBucket if specified
- **Remote Buildspec**: Access to S3-hosted buildspec file if specified

**S3 Access Patterns:**
The role supports four S3 access patterns for copying assets:
1. By path: `*/${Prefix}-${ProjectId}/${StageId}/*`
2. By application tag: `${OrgPrefix}${Prefix}-${ProjectId}-*/${StageId}/*`
3. By deployment tag: `${OrgPrefix}${Prefix}-${ProjectId}-${StageId}-*/*`
4. Specific bucket: S3StaticHostBucket parameter

### PostDeployServiceRole

Type: AWS::IAM::Role  
Condition: IsPostDeployEnabledAndNotDev

Service role for PostDeploy CodeBuild project. Only created when PostDeployStageEnabled="true". Provides similar permissions to CodeBuildServiceRole for consistent execution environment.

**Key Permissions:**
- **Logs**: Full access to PostDeploy log group
- **Artifacts**: Read/write access to S3 artifacts bucket
- **SSM**: Read/write access to Parameter Store hierarchy
- **S3 Assets**: Same four access patterns as CodeBuildServiceRole
- **Static Host**: Access to PostDeployS3StaticHostBucket if specified
- **Remote Buildspec**: Access to S3-hosted buildspec-postdeploy file if specified

**Use Cases:**
- Integration tests against deployed application
- Configuration validation and health checks
- Exporting configurations (e.g., OpenAPI specs from API Gateway)
- Post-deployment data migration or setup tasks

### CodeDeployServiceRole

Type: AWS::IAM::Role

Service role passed to application infrastructure for Lambda function deployments. Uses AWS managed policy for Lambda deployments.

**Key Properties:**
- Allows codedeploy.amazonaws.com to assume the role
- Attached managed policy: AWSCodeDeployRoleForLambda
- Used for gradual Lambda deployment strategies (Linear, Canary, AllAtOnce)

### CloudFormationSvcRole

Type: AWS::IAM::Role

Service role for CloudFormation to create and manage application infrastructure resources. This role defines what resources CloudFormation can create in your application stack.

**Key Permissions:**
- **IAM**: Full access to worker roles and policies for this deployment
- **CloudFormation**: Full access to application stack and transforms
- **CodeDeploy**: Full access to deployment resources for this deployment
- **Artifacts**: Read/write access to S3 artifacts bucket
- **API Gateway**: Full CRUD with tag-based scoping
- **EventBridge**: Full CRUD for rules and schedules
- **SQS/SNS**: Full CRUD for queues and topics
- **Step Functions**: Full CRUD for state machines
- **S3**: Full CRUD for deployment-specific buckets
- **Lambda**: Full CRUD for functions, layers, and event source mappings
- **DynamoDB**: Full CRUD for tables
- **CloudWatch**: Limited CRUD for dashboards, alarms, and log groups
- **SSM**: Read-only access to Parameter Store (application-specific and public AWS parameters)
- **Lambda Layers**: Access to AWS-provided Lambda Insights and Parameters/Secrets extensions

**SSM Parameter Access:**
The role includes two separate SSM policy statements:
- `SSMParameterStoreReadThisDeploymentOnly`: Read access to application-specific parameters under the `ParameterStoreHierarchy` path (includes `ssm:GetParameter`, `ssm:GetParameters`, `ssm:GetParametersByPath`, `ssm:ListTagsForResource`)
- `SSMPublicParameterReadOnly`: Read-only access to AWS-published public SSM parameters under `/aws/service/*` (includes `ssm:GetParameter` and `ssm:GetParameters` only). This enables the use of `{{resolve:ssm:/aws/service/...}}` dynamic references in application CloudFormation templates to resolve AWS-managed values such as Lambda layer ARNs, AMI IDs, and extension versions at deploy time.

**Resource Scoping:**
All permissions are scoped to resources tagged or named with `${Prefix}-${ProjectId}-${StageId}` pattern, following least-privilege principles. The public SSM parameter access is scoped to `arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter/aws/service/*`.

### SourceEvent

Type: AWS::Events::Rule  
Condition: IsNotDevelopment

EventBridge rule that detects commits to the specified branch in CodeCommit and triggers the pipeline.

**Key Properties:**
- Monitors CodeCommit Repository State Change events
- Filters for referenceCreated and referenceUpdated events
- Scoped to specific repository and branch
- Targets the ProjectPipeline with SourceEventServiceRole

### CodeBuildProject

Type: AWS::CodeBuild::Project  
Condition: IsNotDevelopment

CodeBuild project for building and packaging the SAM application.

**Key Properties:**
- **Compute**: BUILD_GENERAL1_SMALL Linux container
- **Image**: aws/codebuild/amazonlinux-x86_64-standard:5.0 (Node 22, Python 3.13, Java corretto21)
- **Caching**: Local custom cache for faster builds
- **Artifacts**: Packaged as ZIP from CodePipeline
- **Environment Variables**: Comprehensive set including AWS_REGION, PREFIX, PROJECT_ID, STAGE_ID, DEPLOY_ENVIRONMENT, etc.
- **Buildspec**: Supports local or S3-hosted buildspec files

**Environment Variables Provided:**
- AWS_PARTITION, AWS_REGION, AWS_ACCOUNT
- S3_ARTIFACTS_BUCKET
- PREFIX, PROJECT_ID, STAGE_ID, S3_BUCKET_NAME_ORG_PREFIX
- REPOSITORY, REPOSITORY_BRANCH
- PARAM_STORE_HIERARCHY
- DEPLOY_ENVIRONMENT
- ALARM_NOTIFICATION_EMAIL
- S3_STATIC_HOST_BUCKET
- ROLE_PATH, PERMISSIONS_BOUNDARY_ARN
- NODE_ENV (set to "production")

### CodeBuildLogGroup

Type: AWS::Logs::LogGroup  
Condition: IsNotDevelopment

CloudWatch log group for CodeBuild project logs with retention policy.

**Key Properties:**
- Log group name: `/aws/codebuild/${Prefix}-${ProjectId}-${StageId}-Build`
- Retention: 90 days
- Deletion policy: Delete
- Update/replace policy: Retain

### PostDeployProject

Type: AWS::CodeBuild::Project  
Condition: IsPostDeployEnabledAndNotDev

CodeBuild project for post-deployment tasks. Only created when PostDeployStageEnabled="true".

**Key Properties:**
- **Compute**: Same as CodeBuildProject (BUILD_GENERAL1_SMALL)
- **Image**: Same as CodeBuildProject for consistency
- **Caching**: Local custom cache
- **Artifacts**: Packaged as ZIP from CodePipeline
- **Environment Variables**: Same as CodeBuildProject, plus POST_DEPLOY_S3_STATIC_HOST_BUCKET
- **Buildspec**: Supports local or S3-hosted buildspec-postdeploy files

**Use Cases:**
- Running integration tests against deployed endpoints
- Validating deployed resources meet requirements
- Exporting API documentation from deployed API Gateway
- Post-deployment configuration tasks

### PostDeployLogGroup

Type: AWS::Logs::LogGroup  
Condition: IsPostDeployEnabledAndNotDev

CloudWatch log group for PostDeploy CodeBuild project logs. Only created when PostDeployStageEnabled="true".

**Key Properties:**
- Log group name: `/aws/codebuild/${Prefix}-${ProjectId}-${StageId}-PostDeploy`
- Retention: 90 days (matches Build stage)
- Deletion policy: Delete
- Update/replace policy: Retain

### ProjectPipeline

Type: AWS::CodePipeline::Pipeline  
Condition: IsNotDevelopment

The main CodePipeline that orchestrates the entire CI/CD workflow.

**Pipeline Structure (PostDeploy Disabled):**
1. **Source Stage**: Retrieves code from CodeCommit repository
2. **Build Stage**: Executes CodeBuild project to build and package
3. **Deploy Stage**: 
   - GenerateChangeSet: Creates CloudFormation changeset
   - ExecuteChangeSet: Executes the changeset to deploy infrastructure

**Pipeline Structure (PostDeploy Enabled):**
1. **Source Stage**: Retrieves code from CodeCommit repository
2. **Build Stage**: Executes CodeBuild project to build and package
3. **Deploy Stage**: 
   - GenerateChangeSet: Creates CloudFormation changeset
   - ExecuteChangeSet: Executes the changeset to deploy infrastructure
4. **PostDeploy Stage**: Executes PostDeploy CodeBuild project

**Key Properties:**
- Artifact store: S3ArtifactsBucket
- Service role: CodePipelineServiceRole
- Artifacts: SourceArtifact, BuildArtifact, PostDeployArtifact (if enabled)
- CloudFormation parameters passed: Prefix, ProjectId, StageId, DeployEnvironment, etc.

### PipelineNotificationTopic

Type: AWS::SNS::Topic

SNS topic for pipeline execution notifications.

**Key Properties:**
- Topic name: `${AWS::StackName}-pipeline-notifications`
- Subscription: Email to AlarmNotificationEmail parameter
- Used by EventBridge rules for pipeline state changes

### PipelineStartedRule

Type: AWS::Events::Rule

EventBridge rule that sends notification when pipeline execution starts.

**Key Properties:**
- Monitors CodePipeline Pipeline Execution State Change events
- Filters for STARTED state
- Scoped to specific pipeline
- Sends human-readable formatted message to PipelineNotificationTopic

**Notification Format:**
- Subject: `Pipeline <pipeline-name> Started`
- Message body uses labeled fields on separate lines (Status, Pipeline, Execution ID, Time, Console Link) with blank-line separation between the header summary and detail fields

### PipelineSucceededRule

Type: AWS::Events::Rule

EventBridge rule that sends notification when pipeline execution succeeds.

**Key Properties:**
- Monitors CodePipeline Pipeline Execution State Change events
- Filters for SUCCEEDED state
- Scoped to specific pipeline
- Sends human-readable formatted message to PipelineNotificationTopic

**Notification Format:**
- Subject: `Pipeline <pipeline-name> Succeeded`
- Message body uses labeled fields on separate lines (Status, Pipeline, Execution ID, Time, Console Link) with blank-line separation between the header summary and detail fields

### PipelineFailedRule

Type: AWS::Events::Rule

EventBridge rule that sends notification when pipeline execution fails.

**Key Properties:**
- Monitors CodePipeline Pipeline Execution State Change events
- Filters for FAILED state
- Scoped to specific pipeline
- Sends ALERT message to PipelineNotificationTopic

**Notification Format:**
- Subject: `ALERT: Pipeline <pipeline-name> Failed`
- Message body uses labeled fields on separate lines (Status, Pipeline, Execution ID, Time, Console Link) with blank-line separation between the header summary and detail fields
- Includes call-to-action: "Please check the pipeline for errors."

### PipelineNotificationTopicPolicy

Type: AWS::SNS::TopicPolicy

Policy that allows EventBridge to publish messages to the notification topic.

**Key Properties:**
- Allows events.amazonaws.com to publish to PipelineNotificationTopic
- Required for EventBridge rules to send notifications

## Outputs

### ProjectPipeline

Condition: IsNotDevelopment

Direct link to the CodePipeline in AWS Console.

**Value:** `https://${AWS::Region}.console.aws.amazon.com/codesuite/codepipeline/pipelines/${Prefix}-${ProjectId}-${StageId}-Pipeline/view?region=${AWS::Region}`

**Usage:** Click this link to view pipeline execution status, stage details, and execution history.

### CodeCommitRepo

Direct link to the CodeCommit repository in AWS Console.

**Value:** `https://${AWS::Region}.console.aws.amazon.com/codesuite/codecommit/repositories/${Repository}/browse?region=${AWS::Region}`

**Usage:** Click this link to browse repository files, view commits, and manage branches.

## Conditions

The template uses several conditions to control resource creation:

- **IsNotDevelopment**: True when DeployEnvironment is not "DEV" - controls creation of pipeline resources
- **UseS3BucketNameOrgPrefix**: True when S3BucketNameOrgPrefix is not empty
- **HasPermissionsBoundaryArn**: True when PermissionsBoundaryArn is not empty
- **HasS3StaticHostBucket**: True when S3StaticHostBucket is not empty
- **HasS3BuildSpecLocation**: True when BuildSpec starts with "s3:"
- **UseDefaultBuildSpecLocation**: True when BuildSpec is empty
- **HasManagedPoliciesForCloudFormationSvcRole**: True when CloudFormationSvcRoleIncludeManagedPolicyArns is not empty
- **IsPostDeployEnabled**: True when PostDeployStageEnabled is "true"
- **HasPostDeployS3StaticHostBucket**: True when PostDeployS3StaticHostBucket is not empty
- **HasPostDeployBuildSpecS3Location**: True when PostDeployBuildSpec starts with "s3:" and PostDeploy is enabled
- **UseDefaultPostDeployBuildSpecLocation**: True when PostDeployBuildSpec is empty
- **HasManagedPoliciesForPostDeploySvcRole**: True when PostDeploySvcRoleIncludeManagedPolicyArns is not empty
- **HasManagedPoliciesForCodeBuildSvcRole**: True when CodeBuildSvcRoleIncludeManagedPolicyArns is not empty
- **IsPostDeployEnabledAndNotDev**: True when both IsNotDevelopment and IsPostDeployEnabled are true

## Mappings

### LambdaInsightsAccountId

Maps AWS regions to account IDs for Lambda Insights extension layers.

**Purpose:** Allows CloudFormation service role to access AWS-provided Lambda Insights layers for application monitoring.

**Reference:** [Lambda Insights Extension Versions](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Lambda-Insights-extension-versions.html)

### LambdaParamSecretsAccountId

Maps AWS regions to account IDs for AWS Parameters and Secrets Lambda Extension layers.

**Purpose:** Allows CloudFormation service role to access AWS-provided Parameters and Secrets extension for efficient parameter retrieval.

**Reference:** [Parameters and Secrets Lambda Extension](https://docs.aws.amazon.com/systems-manager/latest/userguide/ps-integration-lambda-extensions.html)

## Examples

### Basic Deployment

```yaml
Parameters:
  Prefix: "acme"
  ProjectId: "myapp"
  StageId: "prod"
  S3BucketNameOrgPrefix: ""
  RolePath: "/"
  PermissionsBoundaryArn: ""
  DeployEnvironment: "PROD"
  S3ArtifactsBucket: "aws-sam-cli-managed-default-samclisourcebucket-abc123"
  S3StaticHostBucket: ""
  BuildSpec: "application-infrastructure/buildspec.yml"
  PostDeployStageEnabled: "false"
  ParameterStoreHierarchy: "/"
  AlarmNotificationEmail: "devops@example.com"
  CloudFormationSvcRoleIncludeManagedPolicyArns: ""
  CodeBuildSvcRoleIncludeManagedPolicyArns: ""
  PostDeploySvcRoleIncludeManagedPolicyArns: ""
  Repository: "my-serverless-app"
  RepositoryBranch: "main"
```

### With PostDeploy Stage for API Documentation Export

```yaml
Parameters:
  Prefix: "acme"
  ProjectId: "api-service"
  StageId: "prod"
  DeployEnvironment: "PROD"
  S3ArtifactsBucket: "aws-sam-cli-managed-default-samclisourcebucket-abc123"
  PostDeployStageEnabled: "true"
  PostDeployS3StaticHostBucket: "acme-api-docs-bucket"
  PostDeployBuildSpec: "application-infrastructure/buildspec-postdeploy.yml"
  AlarmNotificationEmail: "devops@example.com"
  Repository: "api-service"
  RepositoryBranch: "main"
```

### With External Managed Policies

```yaml
Parameters:
  Prefix: "acme"
  ProjectId: "data-processor"
  StageId: "prod"
  DeployEnvironment: "PROD"
  S3ArtifactsBucket: "aws-sam-cli-managed-default-samclisourcebucket-abc123"
  CloudFormationSvcRoleIncludeManagedPolicyArns: "arn:aws:iam::123456789012:policy/ExternalResourceAccess"
  CodeBuildSvcRoleIncludeManagedPolicyArns: "arn:aws:iam::123456789012:policy/BuildTimeAccess"
  AlarmNotificationEmail: "devops@example.com"
  Repository: "data-processor"
  RepositoryBranch: "main"
```

## Troubleshooting

### Pipeline Not Triggering

**Symptom:** Pipeline doesn't start when code is pushed to repository.

**Possible Causes:**
- EventBridge rule is disabled
- Repository or branch name doesn't match parameters
- SourceEventServiceRole lacks permissions

**Solutions:**
1. Check EventBridge rule is enabled in AWS Console
2. Verify Repository and RepositoryBranch parameters match actual repository
3. Manually trigger pipeline to test if issue is with EventBridge rule

### Build Stage Fails

**Symptom:** Build stage fails with errors in CodeBuild logs.

**Possible Causes:**
- buildspec.yml syntax errors
- Missing dependencies or incorrect runtime versions
- Insufficient IAM permissions
- Environment variables not set correctly

**Solutions:**
1. Review CodeBuild logs in CloudWatch
2. Verify buildspec.yml syntax and commands
3. Check CodeBuildServiceRole has necessary permissions
4. Validate environment variables are set correctly
5. Test build locally using SAM CLI

### Deploy Stage Fails

**Symptom:** Deploy stage fails during changeset creation or execution.

**Possible Causes:**
- CloudFormation template errors
- Insufficient IAM permissions in CloudFormationSvcRole
- Parameter overrides don't match template parameters
- Resource naming conflicts

**Solutions:**
1. Review CloudFormation changeset for errors
2. Check CloudFormationSvcRole has permissions for all resources
3. Verify parameter overrides match template parameters
4. Check for resource naming conflicts with existing resources

### PostDeploy Stage Fails

**Symptom:** PostDeploy stage fails with errors in CodeBuild logs.

**Possible Causes:**
- buildspec-postdeploy.yml syntax errors
- Deployed resources not accessible
- Insufficient IAM permissions
- Integration tests failing

**Solutions:**
1. Review PostDeploy CodeBuild logs in CloudWatch
2. Verify deployed resources are accessible and healthy
3. Check PostDeployServiceRole has necessary permissions
4. Test integration tests locally if possible
5. Verify POST_DEPLOY_S3_STATIC_HOST_BUCKET is correct

### Notifications Not Received

**Symptom:** Email notifications not received for pipeline events.

**Possible Causes:**
- SNS subscription not confirmed
- Email address incorrect
- EventBridge rules not configured correctly

**Solutions:**
1. Check email inbox (including spam) for SNS subscription confirmation
2. Verify AlarmNotificationEmail parameter is correct
3. Check EventBridge rules are enabled and configured correctly
4. Test SNS topic by publishing a test message

## Related Templates

This template is commonly used with:

- **Service Role Templates**: 
  - [template-service-role-pipeline.yml](../service-role/template-service-role-pipeline-README.md) - Pre-created CloudFormation service role

- **Storage Templates**:
  - [template-storage-s3-artifacts.yml](../storage/template-storage-s3-artifacts-README.md) - S3 bucket for build artifacts
  - [template-storage-s3-devops.yml](../storage/template-storage-s3-devops-README.md) - S3 bucket for DevOps artifacts

- **Application Infrastructure**: Your SAM template being deployed by the pipeline

## Security Considerations

1. **Least Privilege**: All IAM roles follow least-privilege principles with scoped permissions
2. **Permissions Boundaries**: Support for permissions boundaries to enforce organizational policies
3. **Role Paths**: Use role paths to organize and scope IAM roles
4. **Managed Policies**: Support for external managed policies for additional permissions
5. **Parameter Store**: Secure storage for application configuration
6. **Artifact Encryption**: Consider enabling S3 bucket encryption for artifacts
7. **Resource Tagging**: All resources tagged with atlantis:ApplicationDeploymentId for tracking

## Cost Considerations

**Monthly Costs (approximate):**
- CodePipeline: $1 per active pipeline
- CodeBuild: $0.005 per build minute (BUILD_GENERAL1_SMALL)
- S3: Storage costs for artifacts (varies by usage)
- CloudWatch Logs: $0.50 per GB ingested + $0.03 per GB stored
- SNS: $0.50 per million notifications (minimal)

**Cost Optimization Tips:**
- Use DEV environment for local testing to avoid pipeline executions
- Set appropriate log retention periods (default: 90 days)
- Clean up old artifacts from S3 periodically
- Use build caching to reduce build times
- Monitor CodeBuild usage and optimize build processes

## Additional Resources

- [AWS CodePipeline User Guide](https://docs.aws.amazon.com/codepipeline/latest/userguide/)
- [AWS CodeBuild User Guide](https://docs.aws.amazon.com/codebuild/latest/userguide/)
- [AWS SAM Developer Guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/)
- [CloudFormation User Guide](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/)
- [GitHub Repository](https://github.com/63Klabs/atlantis-sam-templates/)
