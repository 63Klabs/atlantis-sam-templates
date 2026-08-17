# template-pipeline-build-only.yml

Simplified AWS CodePipeline with only Source and Build stages (no CloudFormation deployment).

**Version:** v2.0.7  
**Last Updated:** 2026-08-15  
**Template:** [templates/v2/pipeline/template-pipeline-build-only.yml](../../../../templates/v2/pipeline/template-pipeline-build-only.yml)

## Overview

This template creates a simplified CI/CD pipeline for build-and-copy workflows using AWS CodeCommit as the source repository. Unlike the full pipeline templates, this version does NOT include a CloudFormation deployment stage, making it ideal for static website builds, artifact generation, or custom deployment workflows.

### Pipeline Stages

1. **Source**: Monitors CodeCommit repository for changes to specified branch
2. **Build**: Executes buildspec.yml to build and copy artifacts (no CloudFormation deployment)
3. **ApproveToPromote** (Optional): Manual approval gate before promoting the build to the next stage
4. **Promote** (Optional): Hands the built commit to the next stage (same or cross account/region) by writing it to the receiving account's S3 promotions area

### Key Features

- **Simplified Workflow**: Only Source and Build stages - no CloudFormation deployment
- **Automated Triggers**: EventBridge rule automatically triggers pipeline on repository changes
- **Build Caching**: Local caching in CodeBuild for faster subsequent builds
- **Modern Build Environment**: CodeBuild image upgraded to amazonlinux-x86_64-standard:5.0 (Amazon Linux 2023)
- **Flexible Buildspec**: Supports local or S3-hosted buildspec files
- **Comprehensive Notifications**: Email notifications for pipeline start, success, and failure
- **Security**: Least-privilege IAM roles with permissions boundary support
- **Multi-Environment**: Supports DEV, TEST, and PROD deployment environments
- **S3 Integration**: Built-in support for copying build artifacts to S3 buckets
- **Promotion (Send to Next Stage)**: Optional, default-off Approve-to-Promote gate and Promote stage that hand the built commit to a downstream stage (same or cross account/region) via the receiving account's S3 promotions area
- **Modular Architecture**: 13 pipeline resources provided via AWS::Include modules for maintainability

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

### Module Source

Parameters for locating AWS::Include modules in S3.

- [S3ModuleLocation](#s3modulelocation)
- [S3ModuleNamespace](#s3modulenamespace)

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

#### S3ModuleLocation

S3 bucket name where AWS::Include modules are stored.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None (required) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$` |
| Constraint Description | Must be a valid S3 bucket name. May only contain lowercase alphanumeric characters and dashes. |

This template uses AWS::Include to reference modular CloudFormation resources stored in S3. The S3ModuleLocation specifies the bucket name where these modules are located. The deploying role must have `s3:GetObject` permission on this bucket.

#### S3ModuleNamespace

Namespace prefix for module paths in S3.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | atlantis |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$` |
| Constraint Description | Must be a valid S3 path prefix. May only contain lowercase alphanumeric characters and dashes. |

Modules are resolved from `s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/pipeline/<module-name>.yml`. The default namespace is "atlantis".

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

### Promotion (Send to Next Stage)

Additive, default-off parameters that hand a validated build off to the next stage (same or cross account/region) via the receiving account's S3 promotions area.

> **Important:** With all of these parameters at their defaults, the pipeline is structurally unchanged — no `Promote` or `ApproveToPromote` stage is created, and no promotion resources (`PromoteServiceRole`, `PromoteProject`, `PromoteLogGroup`) are created. Promotion is only enabled when `PromoteTargetStageId` is set to a non-empty value.

- [PromoteTargetStageId](#promotetargetstageid)
- [PromoteApprovalRequired](#promoteapprovalrequired)
- [PromoteTargetAccountId](#promotetargetaccountid)
- [PromoteTargetRegion](#promotetargetregion)
- [PromoteTargetBucket](#promotetargetbucket)

#### PromoteTargetStageId

The receiving stage's StageId (the target of promotion).

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^[a-z][a-z0-9-]{0,6}[a-z0-9]$` |
| Constraint Description | May be empty (promotion disabled) or 2 to 8 characters. Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. |

A non-empty value **enables** the Promote stage (and the Approve-to-Promote gate unless `PromoteApprovalRequired` is `false`); empty (default) disables promotion entirely. Must equal the receiving pipeline's `StageId`. Promotions are written to `promotions/<Prefix>-<ProjectId>/<PromoteTargetStageId>/source.zip` in the target bucket. Because this template has no Deploy stage, the Promote stage still reuses the pipeline's `SourceArtifact` — it does not require a CloudFormation deployment first.

#### PromoteApprovalRequired

Controls whether the manual Approve-to-Promote gate is inserted before the Promote stage.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | true |
| Allowed Values | true, false |
| Constraint Description | Must specify true or false. |

> **Warning:** Setting this to `false` removes the human gate and promotes automatically. If the receiving pipeline also has `ReleaseApprovalRequired=false`, the artifact will build and deploy into the target environment with no human review at any point, **including into PROD stages**. Only takes effect when `PromoteTargetStageId` is non-empty.

#### PromoteTargetAccountId

The AWS account ID of the promotion target.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^\\d{12}$` |
| Constraint Description | Must be empty or a 12-digit AWS account ID. |

Leave empty (default) for same-account promotion (the target account is the current account). When non-empty, promotion writes cross-account into the target account's artifacts bucket, and that account must allow this account in its `PromotionSourceAccountIds`.

#### PromoteTargetRegion

The AWS region of the promotion target.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^[a-z]{2}-[a-z]+-\\d$` |
| Constraint Description | Must be empty or a valid AWS region name (e.g., us-east-1). |

Leave empty (default) to use the current region. When non-empty, promotion targets the specified region (cross-region promotion); the only cross-region operation is the S3 write into the receiving-region bucket.

#### PromoteTargetBucket

Explicit name of the target account-wide artifacts bucket to write promotions into.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$` |
| Constraint Description | Must be empty or a valid S3 bucket name between 3 and 63 characters. Lower case alphanumeric and dashes. Must start and end with a letter or number. |

Leave empty (default) to derive it as `<S3BucketNameOrgPrefix->cf-artifacts-<targetAccount>-<targetRegion>-an` from the resolved target account/region and this template's `S3BucketNameOrgPrefix`. Set only when the derived name does not match the target bucket.

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
- [PromoteServiceRole](#promoteservicerole) - AWS::IAM::Role (Conditional: IsPromoteEnabledAndNotDev)
- [PromoteProject](#promoteproject) - AWS::CodeBuild::Project (Conditional: IsPromoteEnabledAndNotDev)
- [PromoteLogGroup](#promoteloggroup) - AWS::Logs::LogGroup (Conditional: IsPromoteEnabledAndNotDev)
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
- **Image**: aws/codebuild/amazonlinux-x86_64-standard:5.0 (Amazon Linux 2023 with Node 22, Python 3.13, Java corretto21)
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

### PromoteServiceRole

Type: AWS::IAM::Role  
Condition: IsPromoteEnabledAndNotDev

Sourced from the `promote-service-role.yml` module via `AWS::Include`. This is the **sole** cross-account writer for promotion — the `CodeBuildServiceRole` is never granted cross-account promotion write permissions. Only created when `PromoteTargetStageId` is non-empty (promotion enabled) and `DeployEnvironment` is not `DEV`.

**Key Permissions:**
- **Logs**: Full access to its own CloudWatch log group (`PromoteLogGroup`)
- **Read local SourceArtifact**: Read access to the local `S3ArtifactsBucket` (to read the pipeline's SourceArtifact)
- **Write promotion to target**: `s3:PutObject`, `s3:GetObject`, `s3:GetObjectVersion` scoped to `arn:aws:s3:::<resolved PromoteTargetBucket>/promotions/*` only (plus `s3:PutObjectAcl` when the target bucket ownership is not enforced)

**Least privilege:** write access is confined to the `promotions/*` prefix in the resolved target bucket; the role cannot access any other key or bucket.

### PromoteProject

Type: AWS::CodeBuild::Project  
Condition: IsPromoteEnabledAndNotDev

Sourced from the `promote-project.yml` module via `AWS::Include`. A dedicated CodeBuild project (named `${Prefix}-${ProjectId}-${StageId}-Promote`) that re-uploads the pipeline's existing SourceArtifact as `source.zip` to the target bucket and writes the audit manifest (`promote.json`). Uses the same compute/image as the Build stage, but with a framework-owned inline buildspec (no app-repo buildspec override is supported for promotion). This build-only template has no CloudFormation/PostDeploy modules, so the Promote stage reuses the pipeline's `SourceArtifact` directly and does not require a deployment first.

**Key Properties:**
- **Service role**: `PromoteServiceRole`
- **Inline buildspec**: resolves the commit SHA (`CODEBUILD_RESOLVED_SOURCE_VERSION`), zips the SourceArtifact contents, writes `promote.json` first, then `source.zip` last (so the EventBridge trigger on the receiving side only fires once the manifest already exists)
- **Environment Variables**: `PREFIX`, `PROJECT_ID`, `STAGE_ID`, `PROMOTE_TARGET_STAGE_ID`, `PROMOTE_TARGET_BUCKET`, `PROMOTE_TARGET_REGION`, `PROMOTE_TARGET_ACCOUNT_ID`, `SOURCE_ACCOUNT_ID`, `AWS_REGION`, `PROMOTION_KEY_PREFIX`

### PromoteLogGroup

Type: AWS::Logs::LogGroup  
Condition: IsPromoteEnabledAndNotDev

Sourced from the `promote-log-group.yml` module via `AWS::Include`. Dedicated CloudWatch log group for the Promote CodeBuild project logs.

**Key Properties:**
- Log group name: `/aws/codebuild/${Prefix}-${ProjectId}-${StageId}-Promote`
- Retention: 90 days (matches Build stage)

### ProjectPipeline

Type: AWS::CodePipeline::Pipeline  
Condition: IsNotDevelopment

The main CodePipeline that orchestrates the build workflow.

**Pipeline Structure:**
1. **Source Stage**: Retrieves code from CodeCommit repository
2. **Build Stage**: Executes CodeBuild project to build and copy artifacts

**Pipeline Structure (Promotion Enabled):**

When `PromoteTargetStageId` is non-empty, the pipeline gains one or two additional stages appended after Build:
3. **ApproveToPromote Stage** (only when `PromoteApprovalRequired="true"`, the default): A manual approval action named `ApproveToPromote` that publishes to `PipelineNotificationTopic` and must be approved before the Promote stage runs.
4. **Promote Stage**: Runs the `PromoteProject` CodeBuild project (action named `Promote`), which reuses the Source stage's `SourceArtifact` (no re-clone) to write `source.zip` and `promote.json` to the receiving account's S3 promotions area.

With all promotion parameters left at their defaults (`PromoteTargetStageId=""`), neither stage is added and the pipeline is structurally identical to the pre-promotion pipeline.

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
- **IsPromoteEnabled**: True when PromoteTargetStageId is not empty
- **IsPromoteApprovalRequired**: True when PromoteApprovalRequired is "true"
- **IsPromoteEnabledAndApprovalRequired**: True when both IsPromoteEnabled and IsPromoteApprovalRequired are true — controls creation of the ApproveToPromote stage
- **IsPromoteEnabledAndNotDev**: True when both IsNotDevelopment and IsPromoteEnabled are true — controls creation of PromoteServiceRole, PromoteProject, and PromoteLogGroup
- **HasPromoteTargetAccount**: True when PromoteTargetAccountId is not empty
- **HasPromoteTargetRegion**: True when PromoteTargetRegion is not empty
- **HasPromoteTargetBucket**: True when PromoteTargetBucket is not empty

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

### With Promotion to a Downstream Stage

```yaml
Parameters:
  Prefix: "acme"
  ProjectId: "website"
  StageId: "test"
  DeployEnvironment: "TEST"
  S3ArtifactsBucket: "aws-sam-cli-managed-default-samclisourcebucket-abc123"
  BuildSpec: "buildspec.yml"
  AlarmNotificationEmail: "devops@example.com"
  Repository: "website-source"
  RepositoryBranch: "test"
  PromoteTargetStageId: "beta"
  PromoteApprovalRequired: "true"
  PromoteTargetAccountId: "222233334444"
  PromoteTargetRegion: ""
  PromoteTargetBucket: ""
```

This promotes a validated `test`-stage build to the `beta` stage in account `222233334444` (same region), pausing for manual `ApproveToPromote` approval before the Promote stage writes the archive. Deploy [template-pipeline-promoted-artifact.yml](template-pipeline-promoted-artifact-README.md) as the `beta` pipeline in the target account to receive it.

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

### Promote Stage Fails or Receiving Pipeline Doesn't Trigger

**Symptom:** The Promote stage succeeds but the receiving pipeline never starts, or the Promote stage fails with an S3 access error.

**Possible Causes:**
- `PromoteTargetStageId` does not match the receiving pipeline's `StageId`
- Cross-account promotion but the receiving account's `PromotionSourceAccountIds` does not include this account
- The receiving account's account-wide artifacts bucket does not have EventBridge notifications enabled (`EnablePromotionTrigger`)
- `PromoteTargetBucket` (or the derived bucket name) does not match the actual target bucket

**Solutions:**
1. Verify `PromoteTargetStageId` equals the receiving pipeline's `StageId` exactly
2. For cross-account promotion, confirm the target account's `account-wide-infrastructure.yml` stack includes this account in `PromotionSourceAccountIds`
3. Confirm the target account-wide bucket was deployed with `EnablePromotionTrigger="true"`
4. Check the Promote CodeBuild logs (`/aws/codebuild/${Prefix}-${ProjectId}-${StageId}-Promote`) for the exact S3 error
5. If using an explicit `PromoteTargetBucket`, verify it matches the receiving account's actual bucket name

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

- **Promotion**:
  - [template-pipeline-promoted-artifact.yml](template-pipeline-promoted-artifact-README.md) - Receiving pipeline for the Promote stage's output; deploy this in the target account/stage when using the Promotion parameter group
  - [account-wide-infrastructure.yml](../account/account-wide-infrastructure-README.md) - Provides the account-wide artifacts bucket, cross-account promotion bucket policy, and EventBridge opt-in that the receiving pipeline depends on

## Security Considerations

1. **Least Privilege**: IAM roles follow least-privilege principles with scoped permissions
2. **Permissions Boundaries**: Support for permissions boundaries to enforce organizational policies
3. **Role Paths**: Use role paths to organize and scope IAM roles
4. **Managed Policies**: Support for external managed policies for additional permissions
5. **Parameter Store**: Secure storage for build-time configuration
6. **S3 Access**: Multiple S3 access patterns for flexible artifact management
7. **Promotion Approval Gates**: `PromoteApprovalRequired` defaults to `true`. Setting it to `false` removes the human Approve-to-Promote gate; combined with `ReleaseApprovalRequired=false` on the receiving pipeline, this yields a fully ungated path into the target environment, including PROD stages. Disabling both is auditable via the admin-ops approval-audit CLI (see `docs/admin-ops/`).
8. **Cross-Account Write Scope**: Promotion cross-account writes are performed solely by `PromoteServiceRole`, scoped to the `promotions/*` prefix of the resolved target bucket — no other role can write cross-account.

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
