# template-pipeline-build-only.yml

Simplified AWS CodePipeline with only Source and Build stages (no CloudFormation deployment).

**Version:** v2.0.5  
**Last Updated:** 2026-03-26  
**Template:** [templates/v2/pipeline/template-pipeline-build-only.yml](../../../../templates/v2/pipeline/template-pipeline-build-only.yml)

## Overview

This template creates a simplified CI/CD pipeline for build-and-copy workflows using AWS CodeCommit as the source repository. Unlike the full pipeline templates, this version does NOT include a CloudFormation deployment stage, making it ideal for static website builds, artifact generation, or custom deployment workflows.

### Pipeline Stages

1. **Source**: Monitors CodeCommit repository for changes to specified branch
2. **Build**: Executes buildspec.yml to build and copy artifacts (no CloudFormation deployment)

### Key Features

- **Simplified Workflow**: Only Source and Build stages - no CloudFormation deployment
- **Automated Triggers**: EventBridge rule automatically triggers pipeline on repository changes
- **Build Caching**: Local caching in CodeBuild for faster subsequent builds
- **Flexible Buildspec**: Supports local or S3-hosted buildspec files
- **Comprehensive Notifications**: Email notifications for pipeline start, success, and failure
- **Security**: Least-privilege IAM roles with permissions boundary support
- **Multi-Environment**: Supports DEV, TEST, and PROD deployment environments
- **S3 Integration**: Built-in support for copying build artifacts to S3 buckets

### Use Cases

- **Static Website Builds**: Build React, Vue, Angular, or static HTML sites and copy to S3
- **Artifact Generation**: Generate documentation, reports, or other artifacts
- **Custom Deployments**: Build artifacts that are deployed by external tools or processes
- **Build-Only Workflows**: Scenarios where CloudFormation deployment is not needed
- **Multi-Stage Builds**: First stage of a multi-pipeline deployment strategy

### Prerequisites

- AWS CodeCommit repository
- S3 bucket for build artifacts
- (Optional) S3 bucket for static hosting or build output
- (Optional) Permissions boundary policy
- (Optional) External managed policies for additional permissions

> **Important:** This template does NOT create CloudFormation service roles or deployment stages. If you need CloudFormation deployment, use template-pipeline.yml instead.

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
| Constraint Description | 2 to 8 characters. Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. |

#### ProjectId

Project or Application Identifier.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,24}[a-z0-9]$` |
| Min Length | 2 |
| Max Length | 26 |
| Constraint Description | Minimum of 2 characters (suggested maximum of 20). Lower case alphanumeric and dashes. |

#### StageId

Alias for the branch, used in resource naming.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,6}[a-z0-9]$` |
| Min Length | 2 |
| Max Length | 8 |
| Constraint Description | 2 to 8 characters. Lower case alphanumeric and dashes. |

#### S3BucketNameOrgPrefix

Optional organization prefix for S3 bucket names.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,18}[a-z0-9]$\|^$` |
| Constraint Description | May be empty or 2 to 20 characters (8 or less recommended). |

#### RolePath

Path for IAM Roles and Policies.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\\/([a-zA-Z0-9-_]+[\\/])+$\|^\\/$` |
| Constraint Description | Must begin and end with a slash. |

#### PermissionsBoundaryArn

Optional IAM Permissions Boundary policy ARN.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^arn:aws:iam::\\d{12}:policy\\/[\\w+=,.@\\-\\/]*[\\w+=,.@\\-]+$` |
| Constraint Description | Must be empty or a valid IAM Policy ARN |

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

Use this to determine tests, app logging levels, and conditionals in the buildspec.

#### S3ArtifactsBucket

Existing S3 bucket name for build artifacts.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$` |
| Constraint Description | May only contain alphanumeric characters and dashes. |

Must be in the same AWS account and region as the stack.

#### S3StaticHostBucket

Optional existing S3 bucket for build output.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$\|^$` |
| Constraint Description | May only contain alphanumeric characters and dashes. |

Passed as `S3_STATIC_HOST_BUCKET` environment variable to CodeBuild. Commonly used for static website hosting or build output destination.

#### BuildSpec

Path to CodeBuild buildspec file (local or S3).

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | buildspec.yml |
| Allowed Pattern | `^s3:\\/\\/[a-zA-Z0-9][a-zA-Z0-9\\-]{1,61}[a-zA-Z0-9]\\/.*$\|^[([a-zA-Z0-9][a-zA-Z0-9_\\-\\/]*)?(buildspec\\.yml)$\|^$` |
| Constraint Description | Must be a valid S3 URI or a local path ending with 'buildspec.yml'. May be empty. |

### External Resources and Alarm Notifications

Parameters for external resources and notifications.

- [ParameterStoreHierarchy](#parameterstorehierarchy)
- [AlarmNotificationEmail](#alarmnotificationemail)
- [CodeBuildSvcRoleIncludeManagedPolicyArns](#codebuildsvcr oleincludemanagedpolicyarns)

#### ParameterStoreHierarchy

SSM Parameter Store hierarchy for application parameters.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\\/([a-zA-Z0-9_.\\-]*[\\/])*$\|^$` |
| Constraint Description | Must be a single slash or begin and end with a slash. |

#### AlarmNotificationEmail

Email address for pipeline notifications.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[\\w\\-\\.]+@([\\w\\-]+\\.)+[\\w\\-]{2,4}$` |
| Constraint Description | A valid email address |

#### CodeBuildSvcRoleIncludeManagedPolicyArns

Additional managed policies for CodeBuild service role.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^arn:aws:iam::\\d{12}:policy\\/[a-zA-Z0-9_\\-]+(?:\\/[a-zA-Z0-9_\\-]+)*$` |
| Constraint Description | Must be comma delimited valid IAM Policy ARNs |

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
| Constraint Description | Must be a valid CodeCommit repository name. |

#### RepositoryBranch

Branch of CodeCommit to monitor.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | main |
| Allowed Pattern | `^[a-zA-Z0-9][a-zA-Z0-9_\\-\\/]{0,14}[a-zA-Z0-9]$` |
| Constraint Description | Must be a valid CodeCommit branch name |

## Resources

This template creates the following resources:

- [SourceEventServiceRole](#sourceeventservicerole) - AWS::IAM::Role (Conditional: IsNotDevelopment)
- [CodePipelineServiceRole](#codepipelineservicerole) - AWS::IAM::Role (Conditional: IsNotDevelopment)
- [CodeBuildServiceRole](#codebuildservicerole) - AWS::IAM::Role (Conditional: IsNotDevelopment)
- [SourceEvent](#sourceevent) - AWS::Events::Rule (Conditional: IsNotDevelopment)
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

Service role that allows EventBridge to trigger CodePipeline execution when repository changes are detected.

**Key Properties:**
- Allows events.amazonaws.com to assume the role
- Grants codepipeline:StartPipelineExecution permission

### CodePipelineServiceRole

Type: AWS::IAM::Role  
Condition: IsNotDevelopment

Service role for CodePipeline to access resources during pipeline execution.

**Key Permissions:**
- **Source Phase**: Read access to CodeCommit repository
- **Build Phase**: Full access to CodeBuild project and report groups
- **Artifacts**: Read/write access to S3 artifacts bucket

> **Note:** This role does NOT include CloudFormation permissions since this template does not have a Deploy stage.

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

**S3 Access Patterns:**
The role supports four S3 access patterns for copying build output:
1. By path: `*/${Prefix}-${ProjectId}/${StageId}/*`
2. By application tag: `${OrgPrefix}${Prefix}-${ProjectId}-*/${StageId}/*`
3. By deployment tag: `${OrgPrefix}${Prefix}-${ProjectId}-${StageId}-*/*`
4. Specific bucket: S3StaticHostBucket parameter

### SourceEvent

Type: AWS::Events::Rule  
Condition: IsNotDevelopment

EventBridge rule that detects commits to the specified branch in CodeCommit and triggers the pipeline.

**Key Properties:**
- Monitors CodeCommit Repository State Change events
- Filters for referenceCreated and referenceUpdated events
- Scoped to specific repository and branch

### CodeBuildProject

Type: AWS::CodeBuild::Project  
Condition: IsNotDevelopment

CodeBuild project for building and copying artifacts.

**Key Properties:**
- **Compute**: BUILD_GENERAL1_SMALL Linux container
- **Image**: aws/codebuild/amazonlinux2-x86_64-standard:5.0 (Node 20, Python 3.12)
- **Caching**: Local custom cache for faster builds
- **Artifacts**: Packaged as ZIP from CodePipeline
- **Environment Variables**: AWS_REGION, PREFIX, PROJECT_ID, STAGE_ID, DEPLOY_ENVIRONMENT, S3_STATIC_HOST_BUCKET, etc.

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

CloudWatch log group for CodeBuild project logs with 90-day retention policy.

### ProjectPipeline

Type: AWS::CodePipeline::Pipeline  
Condition: IsNotDevelopment

The main CodePipeline that orchestrates the build workflow.

**Pipeline Structure:**
1. **Source Stage**: Retrieves code from CodeCommit repository
2. **Build Stage**: Executes CodeBuild project to build and copy artifacts

**Key Properties:**
- Artifact store: S3ArtifactsBucket
- Service role: CodePipelineServiceRole
- Artifacts: SourceArtifact, BuildArtifact

> **Note:** This pipeline does NOT include a Deploy stage. All deployment logic must be handled in the buildspec.yml file.

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

### CodeCommitRepo

Direct link to the CodeCommit repository in AWS Console.

**Value:** `https://${AWS::Region}.console.aws.amazon.com/codesuite/codecommit/repositories/${Repository}/browse?region=${AWS::Region}`

## Conditions

The template uses several conditions to control resource creation:

- **IsNotDevelopment**: True when DeployEnvironment is not "DEV"
- **UseS3BucketNameOrgPrefix**: True when S3BucketNameOrgPrefix is not empty
- **HasPermissionsBoundaryArn**: True when PermissionsBoundaryArn is not empty
- **HasS3StaticHostBucket**: True when S3StaticHostBucket is not empty
- **HasS3BuildSpecLocation**: True when BuildSpec starts with "s3:"
- **UseDefaultBuildSpecLocation**: True when BuildSpec is empty
- **HasManagedPoliciesForCodeBuildSvcRole**: True when CodeBuildSvcRoleIncludeManagedPolicyArns is not empty

## Examples

### Static Website Build

```yaml
Parameters:
  Prefix: "acme"
  ProjectId: "website"
  StageId: "prod"
  DeployEnvironment: "PROD"
  S3ArtifactsBucket: "aws-sam-cli-managed-default-samclisourcebucket-abc123"
  S3StaticHostBucket: "acme-website-prod"
  BuildSpec: "buildspec.yml"
  AlarmNotificationEmail: "devops@example.com"
  Repository: "website-source"
  RepositoryBranch: "main"
```

**Example buildspec.yml for static website:**
```yaml
version: 0.2

phases:
  install:
    runtime-versions:
      nodejs: 20
  pre_build:
    commands:
      - npm install
  build:
    commands:
      - npm run build
  post_build:
    commands:
      - aws s3 sync ./build s3://$S3_STATIC_HOST_BUCKET --delete
      - aws cloudfront create-invalidation --distribution-id $CLOUDFRONT_DIST_ID --paths "/*"

artifacts:
  files:
    - '**/*'
  base-directory: build
```

### Documentation Generation

```yaml
Parameters:
  Prefix: "acme"
  ProjectId: "api-docs"
  StageId: "prod"
  DeployEnvironment: "PROD"
  S3ArtifactsBucket: "aws-sam-cli-managed-default-samclisourcebucket-abc123"
  S3StaticHostBucket: "acme-api-docs"
  BuildSpec: "buildspec.yml"
  AlarmNotificationEmail: "devops@example.com"
  Repository: "api-documentation"
  RepositoryBranch: "main"
```

### Custom Deployment Workflow

```yaml
Parameters:
  Prefix: "acme"
  ProjectId: "custom-deploy"
  StageId: "prod"
  DeployEnvironment: "PROD"
  S3ArtifactsBucket: "aws-sam-cli-managed-default-samclisourcebucket-abc123"
  BuildSpec: "deploy/buildspec.yml"
  AlarmNotificationEmail: "devops@example.com"
  Repository: "custom-deployment"
  RepositoryBranch: "main"
```

## Troubleshooting

### Build Fails to Copy to S3

**Symptom:** Build succeeds but files are not copied to S3StaticHostBucket.

**Possible Causes:**
- S3StaticHostBucket parameter not set
- CodeBuildServiceRole lacks S3 permissions
- Bucket doesn't exist or is in different region
- buildspec.yml doesn't include S3 copy commands

**Solutions:**
1. Verify S3StaticHostBucket parameter is set correctly
2. Check CodeBuildServiceRole has permissions for the bucket
3. Ensure bucket exists in the same region
4. Add S3 copy commands to buildspec.yml (e.g., `aws s3 sync`)

### Pipeline Not Triggering

**Symptom:** Pipeline doesn't start when code is pushed to repository.

**Solutions:**
1. Check EventBridge rule is enabled
2. Verify Repository and RepositoryBranch parameters match actual repository
3. Manually trigger pipeline to test

### Build Stage Fails

**Symptom:** Build stage fails with errors in CodeBuild logs.

**Solutions:**
1. Review CodeBuild logs in CloudWatch
2. Verify buildspec.yml syntax and commands
3. Check CodeBuildServiceRole has necessary permissions
4. Test build commands locally

### Environment Variables Not Available

**Symptom:** buildspec.yml references environment variables that are undefined.

**Solutions:**
1. Check environment variable names match those provided by the template
2. Verify S3_STATIC_HOST_BUCKET is set if using S3StaticHostBucket parameter
3. Add custom environment variables to CodeBuildProject if needed

## Use With

- CodeCommit repository and S3 bucket
- Static website hosting (S3 + CloudFront)
- Custom deployment tools or scripts
- Documentation generation workflows

## Related Templates

This template is commonly used with:

- **Storage Templates**:
  - [template-storage-s3-artifacts.yml](../storage/template-storage-s3-artifacts-README.md) - S3 bucket for build artifacts
  - [template-storage-s3-devops.yml](../storage/template-storage-s3-devops-README.md) - S3 bucket for static hosting

- **Network Templates** (for static websites):
  - [template-network-route53-cloudfront-s3-apigw.yml](../network/template-network-route53-cloudfront-s3-apigw-README.md) - CloudFront distribution for S3 static hosting

## Security Considerations

1. **Least Privilege**: IAM roles follow least-privilege principles with scoped permissions
2. **Permissions Boundaries**: Support for permissions boundaries to enforce organizational policies
3. **Role Paths**: Use role paths to organize and scope IAM roles
4. **Managed Policies**: Support for external managed policies for additional permissions
5. **Parameter Store**: Secure storage for build-time configuration
6. **S3 Access**: Multiple S3 access patterns for flexible artifact management

## Cost Considerations

**Monthly Costs (approximate):**
- CodePipeline: $1 per active pipeline
- CodeBuild: $0.005 per build minute (BUILD_GENERAL1_SMALL)
- S3: Storage costs for artifacts and build output
- CloudWatch Logs: $0.50 per GB ingested + $0.03 per GB stored
- SNS: $0.50 per million notifications (minimal)

**Cost Optimization Tips:**
- Use DEV environment for local testing
- Set appropriate log retention periods (default: 90 days)
- Clean up old artifacts from S3 periodically
- Use build caching to reduce build times

## Additional Resources

- [AWS CodePipeline User Guide](https://docs.aws.amazon.com/codepipeline/latest/userguide/)
- [AWS CodeBuild User Guide](https://docs.aws.amazon.com/codebuild/latest/userguide/)
- [CodeBuild Buildspec Reference](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html)
- [GitHub Repository](https://github.com/63Klabs/atlantis-sam-templates/)
