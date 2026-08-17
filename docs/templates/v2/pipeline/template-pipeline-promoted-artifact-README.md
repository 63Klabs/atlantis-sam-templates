# template-pipeline-promoted-artifact.yml

AWS CodePipeline triggered by a promoted source artifact arriving in S3 - the "receiving" side of cross-account (or same-account) stage-to-stage promotion.

**Version:** v0.0.0  
**Last Updated:** 2026-08-15  
**Template:** [templates/v2/pipeline/template-pipeline-promoted-artifact.yml](../../../../templates/v2/pipeline/template-pipeline-promoted-artifact.yml)

> **Development mode:** This template is at v0.0.0 (PATCH = 0), meaning it has not yet been deployed to any environment. Breaking changes may occur without a new versioned file until it reaches v0.0.1.

## Overview

This template creates a CodePipeline that is triggered when a promoted source archive (`source.zip`) arrives in the account-wide S3 artifacts bucket under the `promotions/` prefix. An EventBridge rule watching the stable trigger key starts the pipeline, whose S3 Source action emits the archive as its `SourceArtifact`. The pipeline then rebuilds and deploys from source in the target account context, behaving identically to a normal build once past the Source stage.

This is the **receiving** side of promotion: an origin pipeline (`template-pipeline.yml`, `template-pipeline-github.yml`, or `template-pipeline-build-only.yml`) writes the promoted archive here via its own Promote stage. This template can also chain promotion onward (for example `beta -> prod`) via its own optional Promote stage, using the same rules as the origin templates.

Two independent, default-on approval gates are provided:
- **`ReleaseApprovalRequired`** (`ApproveRelease`) gates incoming builds/deploys, giving the stage owner control over what is released into this environment.
- **`PromoteApprovalRequired`** (`ApproveToPromote`) gates outbound chained promotion to the next stage.

> **Security note:** Both approval gates default to `true`. Setting `ReleaseApprovalRequired=false` auto-releases every incoming promotion with no human review at this stage. If the upstream (sending) pipeline also has `PromoteApprovalRequired=false`, the result is a fully ungated path into this environment, including into PROD stages. See the [Approval-audit CLI](../../../admin-ops/README.md) to detect deployed pipelines with these gates disabled.

### Pipeline Stages

1. **Source (S3)**: Reads `promotions/<Prefix>-<ProjectId>/<StageId>/source.zip` from `S3ArtifactsBucket` and emits it as the `SourceArtifact`. `PollForSourceChanges` is `false` - the pipeline is started by EventBridge, not S3 polling.
2. **ApproveRelease** (optional, default enabled): Manual approval gate between Source and Build, controlled by `ReleaseApprovalRequired`.
3. **Build**: Executes `buildspec.yml` to build, test, and package the application - identical to the Build stage in the origin templates.
4. **Deploy** (optional, default enabled): Creates and executes a CloudFormation changeset to deploy application infrastructure, controlled by `DeployStageEnabled`.
5. **PostDeploy** (optional, default disabled): Runs post-deployment tasks such as integration tests or configuration export, controlled by `PostDeployStageEnabled`.
6. **ApproveToPromote** (optional, default disabled unless a promotion target is set): Manual approval gate before chained promotion, controlled by `PromoteApprovalRequired`.
7. **Promote** (optional, default disabled): Re-uploads the `SourceArtifact` as a promoted archive to the next stage, controlled by `PromoteTargetStageId`.

### Key Features

- **S3-Triggered Source**: No CodeCommit or GitHub source provider - the pipeline is triggered by the arrival of a promoted archive in the account-wide artifacts bucket.
- **Cross-Account and Same-Account Promotion**: Works whether the sending pipeline is in the same account or a different account (the receiving account owns this pipeline, its bucket, and its worker roles).
- **Chained Promotion**: This template can itself promote onward to a further downstream stage, using the same `PromoteTarget*` parameters and `Promote`/`ApproveToPromote` stages as the origin templates.
- **Two Independent Approval Gates**: `ApproveRelease` (incoming) and `ApproveToPromote` (outbound) are controlled by separate parameters so each stage owner can decide their own gating policy.
- **Optional Deploy Stage**: `DeployStageEnabled` allows this template to be used for build-only-style receiving workloads.
- **Comprehensive Notifications**: Email notifications for pipeline start, success, failure, and both approval actions via the existing `PipelineNotificationTopic`.
- **Security**: Least-privilege IAM roles with permissions boundary support. No source-provider permissions are granted (no CodeCommit, no CodeConnections) since the source is an S3 object.
- **Modular Architecture**: Supporting resources (CodeBuild role/project/log group, CloudFormation service role, CodeDeploy service role, PostDeploy set, Promote set, promotion-source-event set, notification set) are provided via `AWS::Include` modules for maintainability.

### Use Cases

- Receiving a promoted build in a downstream account or stage (for example `test -> beta` or `beta -> prod`) without re-cloning the repository.
- Multi-account CI/CD topologies where DEV/TEST live in one account and PROD (or beta/prod) live in another.
- Chained promotion pipelines (`beta -> prod`) where the same template both receives from an upstream stage and promotes to a downstream stage.
- Build-only-style receiving workloads (`DeployStageEnabled=false`) where the promoted artifact only needs to be rebuilt and copied, not deployed via CloudFormation.

### Prerequisites

- The receiving account's account-wide artifacts bucket must already exist (deployed via `account-wide-infrastructure.yml`) and be versioned.
- If receiving cross-account, the sending account's `PromoteServiceRole` must be included in the receiving bucket's `PromotionSourceAccountIds` parameter (on `account-wide-infrastructure.yml`), and `EnablePromotionTrigger` must be set to `true` on that same stack so the S3 `Object Created` event reaches this pipeline.
- An origin pipeline (`template-pipeline.yml`, `template-pipeline-github.yml`, or `template-pipeline-build-only.yml`) configured with `PromoteTargetStageId` equal to this template's `StageId`, and (for cross-account/cross-region) matching `PromoteTargetAccountId`/`PromoteTargetRegion`.
- S3 bucket for build artifacts (also used as the S3 Source location).
- (Optional) S3 bucket for static hosting.
- (Optional) Permissions boundary policy.
- (Optional) External managed policies for additional permissions.

> **Important:** `Prefix` and `ProjectId` must be identical between the sending and receiving accounts for a given project, and the sender's `PromoteTargetStageId` must equal this template's `StageId`. Both sides derive the same S3 key (`promotions/<Prefix>-<ProjectId>/<StageId>/source.zip`) without any additional parameterization.

## Parameters

### Application Resource Naming

Parameters for naming and organizing pipeline resources.

- [Prefix](#prefix)
- [ProjectId](#projectid)
- [StageId](#stageid)
- [S3BucketNameOrgPrefix](#s3bucketnameorgprefix)
- [RolePath](#rolepath)
- [PermissionsBoundaryArn](#permissionsboundaryarn)

### Deployment Environment Information

Parameters for deployment environment configuration.

- [DeployEnvironment](#deployenvironment)
- [S3ArtifactsBucket](#s3artifactsbucket)
- [S3StaticHostBucket](#s3statichostbucket)
- [BuildSpec](#buildspec)
- [Repository](#repository)
- [RepositoryBranch](#repositorybranch)

### Release Approval and Deploy Control

Parameters controlling this receiving pipeline's own approval gate and whether the Deploy stage is included.

- [ReleaseApprovalRequired](#releaseapprovalrequired)
- [DeployStageEnabled](#deploystageenabled)

### Post Deploy Environment Information

Parameters for optional PostDeploy stage configuration.

> **Important:** The PostDeploy stage is designed for tasks that require the application infrastructure to be deployed first, such as integration tests, configuration validation, or exporting configurations. Pre-deployment tasks should be done in the Build stage.

- [PostDeployStageEnabled](#postdeploystageenabled)
- [PostDeployS3StaticHostBucket](#postdeploys3statichostbucket)
- [PostDeployBuildSpec](#postdeploybuildspec)

### Promotion (Send to Next Stage)

Optional, default-off (except approval, which defaults on) parameters that enable this pipeline to chain promotion onward to a further downstream stage (for example `beta -> prod`). Leaving `PromoteTargetStageId` empty disables the Promote stage entirely.

- [PromoteTargetStageId](#promotetargetstageid)
- [PromoteApprovalRequired](#promoteapprovalrequired)
- [PromoteTargetAccountId](#promotetargetaccountid)
- [PromoteTargetRegion](#promotetargetregion)
- [PromoteTargetBucket](#promotetargetbucket)

### External Resources

Parameters for external resources and notifications.

- [ParameterStoreHierarchy](#parameterstorehierarchy)
- [AlarmNotificationEmail](#alarmnotificationemail)
- [CloudFormationSvcRoleIncludeManagedPolicyArns](#cloudformationsvcroleincludemanagedpolicyarns)
- [CodeBuildSvcRoleIncludeManagedPolicyArns](#codebuildsvcroleincludemanagedpolicyarns)
- [PostDeploySvcRoleIncludeManagedPolicyArns](#postdeploysvcroleincludemanagedpolicyarns)

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

If you receive 'S3 bucket name too long' errors, shorten the Project ID or use an S3 Org Prefix. `Prefix` and `ProjectId` must be identical between the sending and receiving accounts for promotion to route correctly.

#### StageId

Alias for the branch, and the promotion target this pipeline watches.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,6}[a-z0-9]$` |
| Min Length | 2 |
| Max Length | 8 |
| Constraint Description | 2 to 8 characters. Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. |

Does not need to match `RepositoryBranch` or `DeployEnvironment`. For a promoted-artifact (receiving) pipeline, this `StageId` is the promotion target - the pipeline watches `promotions/<Prefix>-<ProjectId>/<StageId>/source.zip`. This value must equal the sending pipeline's `PromoteTargetStageId`.

#### S3BucketNameOrgPrefix

Optional organization prefix for S3 bucket names to enforce uniqueness.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,18}[a-z0-9]$\|^$` |
| Constraint Description | May be empty or 2 to 20 characters (8 or less recommended). Lower case alphanumeric and dashes. Must start and end with a letter or number. |

By default, buckets include account and region in the name. Use this parameter to specify your own prefix (like an org code) instead. This value is also used when this template resolves a chained `PromoteTargetBucket` name (see [PromoteTargetBucket](#promotetargetbucket)).

#### RolePath

Path for IAM Roles and Policies.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\/([a-zA-Z0-9-_]+[\/])+$\|^\/$` |
| Constraint Description | May only contain alphanumeric characters, forward slashes, underscores, and dashes. Must begin and end with a slash. |

Separate applications from users, or create separate paths per prefix or application. Specific paths may be required by permission boundaries. Examples: `/ws-hello-world-test/` or `/app_role/`

#### PermissionsBoundaryArn

Optional IAM Permissions Boundary policy ARN.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^arn:aws:iam::\d{12}:policy\/[\w+=,.@\-\/]*[\w+=,.@\-]+$` |
| Constraint Description | Must be empty or a valid IAM Policy ARN in the format: arn:aws:iam::{account_id}:policy/{policy_name} |

Permissions Boundary is a policy attached to a role to further restrict the role's permissions. Your organization may or may not require boundaries.

#### DeployEnvironment

Deployment/testing environment designation.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | PROD |
| Allowed Values | DEV, TEST, PROD |
| Constraint Description | Must specify DEV, TEST, or PROD. |

An environment can contain multiple stages. Use this to determine tests, app logging levels, and template conditionals. When `DEV`, the pipeline, its supporting IAM roles, and CodeBuild/Log resources are not created (see the `IsNotDevelopment` condition).

**Suggested use:**
- DEV: local SAM deployment (no pipeline created)
- TEST: test/QA receiving stages
- PROD: beta, prod, and other production-bound receiving stages

#### S3ArtifactsBucket

Existing S3 bucket name used for both the S3 Source (promoted artifact) location and the CodePipeline `ArtifactStore`.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$` |
| Constraint Description | May only contain alphanumeric characters, dashes, and must begin and end with a letter or number. |

This is the account-wide artifacts bucket for this account/region; the pipeline reads `promotions/<Prefix>-<ProjectId>/<StageId>/source.zip` from it and stores pipeline artifacts in it. Must be in the same AWS account and region as the stack. Unlike the origin templates, this template has no `GitHubConnectionArn` and does not use a repository as its source - the S3 bucket is the sole source. (`Repository` and `RepositoryBranch` still exist as informational, default-valued parameters - defaulting to `PROMOTED`/`promoted` - that only populate CodeBuild environment variables; see [Repository](#repository) and [RepositoryBranch](#repositorybranch).)

#### S3StaticHostBucket

Optional existing S3 bucket for static content hosting.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$\|^$` |
| Constraint Description | May only contain alphanumeric characters, dashes, and must begin and end with a letter or number. |

Passed as `S3_STATIC_HOST_BUCKET` environment variable to the Build stage CodeBuild project. Used primarily for hosting static content (JS, CSS, HTML, React, etc.) from S3.

#### BuildSpec

Path to the Build stage's CodeBuild buildspec file (local or S3).

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | application-infrastructure/buildspec.yml |
| Allowed Pattern | `^s3:\/\/[a-zA-Z0-9][a-zA-Z0-9\-]{1,61}[a-zA-Z0-9]\/.*$\|^([a-zA-Z0-9][a-zA-Z0-9_\-\/]*)?(buildspec\.yml)$\|^$` |
| Constraint Description | Must be a valid S3 URI or a local path ending with 'buildspec.yml'. For example, 'buildspec.yml', 'application-infrastructure/buildspec.yml' or 's3://mybucket/buildspec.yml'. If empty, buildspec.yml at root of repo will be sought. |

Best practice is to have a single buildspec file for all instances of an application, matching the buildspec used by the origin pipeline for this project (the promoted archive contains the same repository tree).

#### Repository

Informational repository identifier passed to the Build and PostDeploy CodeBuild projects as the `REPOSITORY` environment variable.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | PROMOTED |
| Allowed Pattern | `^$\|^[a-zA-Z0-9][a-zA-Z0-9_\-\/]{0,62}[a-zA-Z0-9]$` |
| Constraint Description | May be empty, or a valid repository name/identifier (alphanumeric, dashes, underscores, slashes). |

This receiving pipeline's real source is the promoted S3 archive, not a repository, so this value defaults to `PROMOTED`. The parameter exists so the shared Build/PostDeploy CodeBuild modules (which set the `REPOSITORY` environment variable via `Ref: Repository`) resolve without requiring you to supply anything. You may optionally override it with the origin repository (name or `owner/repository`) for traceability in build logs and application buildspecs.

#### RepositoryBranch

Informational branch identifier passed to the Build and PostDeploy CodeBuild projects as the `REPOSITORY_BRANCH` environment variable.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | promoted |
| Allowed Pattern | `^[a-zA-Z0-9][a-zA-Z0-9_\-\/]{0,14}[a-zA-Z0-9]$` |
| Constraint Description | Must be a valid branch name. |

Defaults to `promoted` for this receiving pipeline. Like `Repository`, it exists so the shared Build/PostDeploy CodeBuild modules resolve without requiring input, and it may optionally be overridden with the origin branch for traceability.

#### ReleaseApprovalRequired

Controls the `ApproveRelease` manual approval gate for this receiving pipeline.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | true |
| Allowed Values | true, false |
| Constraint Description | Must specify true or false. |

When `true` (default), an incoming promoted artifact pauses after the Source stage and before Build until a human approves it, giving the stage owner control over what is released into this environment.

> **Warning:** Setting this to `false` auto-releases EVERY incoming promotion - the artifact will build and deploy in this environment with no human review at this stage. If the upstream (sending) pipeline also has `PromoteApprovalRequired=false`, this yields a FULLY UNGATED path into this environment with no human review at any point, including into PROD stages. The `ApproveRelease` action name is fixed so this gate is auditable.

#### DeployStageEnabled

Controls whether the Deploy (CloudFormation) stage is included in the pipeline.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | true |
| Allowed Values | true, false |
| Constraint Description | Must specify true or false. |

When `true` (default), the pipeline deploys the built application infrastructure via CloudFormation. Set to `false` for build-only-style receiving workloads where the promoted artifact is built (and optionally copied to S3 in the Build stage) but not deployed via CloudFormation.

#### PostDeployStageEnabled

Controls whether the PostDeploy stage is created and included in the pipeline.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | false |
| Allowed Values | true, false |
| Constraint Description | Must specify true or false. |

When enabled, creates a final stage to run integration tests, configuration checks, or export configurations (such as exporting OpenAPI specifications from API Gateway to an external bucket for static documentation generation). This should only be used for tasks that require a deployment first; pre-deploy tasks should be done in the Build stage. Setting to `true` creates `PostDeployServiceRole`, `PostDeployProject`, `PostDeployLogGroup`, and adds the PostDeploy stage to the pipeline.

#### PostDeployS3StaticHostBucket

Optional existing S3 bucket for PostDeploy stage output.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$\|^$` |
| Constraint Description | May only contain alphanumeric characters, dashes, and must begin and end with a letter or number. |

Passed as `POST_DEPLOY_S3_STATIC_HOST_BUCKET` environment variable to the PostDeploy CodeBuild project. Used primarily to store artifacts that will be picked up by another process such as static API specification documentation or exported configuration files.

#### PostDeployBuildSpec

Path to the PostDeploy stage's buildspec file (local or S3).

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | application-infrastructure/buildspec-postdeploy.yml |
| Allowed Pattern | `^s3:\/\/[a-zA-Z0-9][a-zA-Z0-9\-]{1,61}[a-zA-Z0-9]\/.*$\|^([a-zA-Z0-9][a-zA-Z0-9_\-\/]*)?(buildspec-postdeploy\.yml)$\|^$` |
| Constraint Description | Must be a valid S3 URI or a local path ending with 'buildspec-postdeploy.yml'. For example, 'buildspec-postdeploy.yml', 'application-infrastructure/buildspec-postdeploy.yml' or 's3://mybucket/buildspec-postdeploy.yml'. May not be empty. |

Best practice is to have a single file for all instances of an application. Leaving blank uses the SAM default `buildspec-postdeploy.yml` in the root of the repository.

#### PromoteTargetStageId

The receiving `StageId` to chain promotion to next.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^[a-z][a-z0-9-]{0,6}[a-z0-9]$` |
| Constraint Description | May be empty, or 2 to 8 characters: lower case alphanumeric and dashes, starting with a letter and ending with a letter or number. |

A non-empty value **enables** the Promote stage (and the `ApproveToPromote` gate unless disabled below). Leave empty to disable chained promotion. Must equal the downstream (receiving) pipeline's `StageId`.

#### PromoteApprovalRequired

Controls the `ApproveToPromote` manual approval gate before the outbound Promote stage.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | true |
| Allowed Values | true, false |
| Constraint Description | Must specify true or false. |

When `true` (default), a human must approve before this pipeline promotes the build to the next stage.

> **Warning:** Setting this to `false` removes the human gate and promotes AUTOMATICALLY. If the receiving (downstream) pipeline also has `ReleaseApprovalRequired=false`, the artifact will build and deploy in the target environment with NO human review at any point, INCLUDING INTO PROD STAGES. The `ApproveToPromote` action name is fixed so this gate is auditable.

#### PromoteTargetAccountId

The AWS account ID of the (chained) promotion target.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^\d{12}$` |
| Constraint Description | Must be empty or a 12-digit AWS account ID. |

Leave empty for same-account promotion (target account = current account). When set, the Promote stage writes the source archive cross-account into the target account's artifacts bucket.

#### PromoteTargetRegion

The AWS region of the (chained) promotion target.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^[a-z]{2}-[a-z]+-\d$` |
| Constraint Description | Must be empty or a valid AWS region (e.g. us-east-1). |

Leave empty to use the current region. When set, the Promote stage writes the source archive into the target region's artifacts bucket (cross-region promotion).

#### PromoteTargetBucket

The target artifacts bucket name to write chained promotions into.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$` |
| Constraint Description | May be empty or a valid S3 bucket name between 3 and 63 characters: lower case alphanumeric and dashes, starting and ending with a letter or number. |

Leave empty to derive the name automatically as `<S3BucketNameOrgPrefix->cf-artifacts-<TargetAccountId>-<TargetRegion>-an` using the resolved target account/region. Set explicitly only when the target bucket name does not follow the standard account-wide artifacts bucket convention.

#### ParameterStoreHierarchy

SSM Parameter Store hierarchy for application parameters.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\/([a-zA-Z0-9_.\-]*[\/])*$\|^$` |
| Constraint Description | Must only contain alpha-numeric, dashes, underscores, or slashes. Must be a single slash or begin and end with a slash. (/Finance/, /Finance/ops/, or /) |

Parameters specific to the application may be organized within a hierarchy based on your organizational or operations structure. For example, `/Finance/ops/` would generate `/Finance/ops/<DeployEnvironment>/<Prefix>-<ProjectId>-<StageId>/<parameterName>`.

#### AlarmNotificationEmail

Email address for pipeline notifications.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Allowed Pattern | `^[\w\-\.]+@([\w\-]+\.)+[\w\-]{2,4}$` |
| Constraint Description | A valid email address |

Email address to send notifications to when alarms are triggered or pipeline events (started, succeeded, failed) occur, as well as `ApproveRelease`/`ApproveToPromote` approval requests. Be sure to check the inbox to confirm the SNS subscription.

#### CloudFormationSvcRoleIncludeManagedPolicyArns

Additional managed policies for the CloudFormation service role.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^arn:aws:iam::\d{12}:policy\/[a-zA-Z0-9_\-]+(?:\/[a-zA-Z0-9_\-]+)*$` |
| Constraint Description | Must be an empty string or comma delimited valid IAM Policy ARNs in the format: arn:aws:iam::{account_id}:policy/{policy_name} |

List of IAM Managed Policy ARNs to add to the CloudFormation Service Role. Use when external resources provide policies to interact with them.

#### CodeBuildSvcRoleIncludeManagedPolicyArns

Additional managed policies for the CodeBuild service role.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^arn:aws:iam::\d{12}:policy\/[a-zA-Z0-9_\-]+(?:\/[a-zA-Z0-9_\-]+)*$` |
| Constraint Description | Must be an empty string or comma delimited valid IAM Policy ARNs in the format: arn:aws:iam::{account_id}:policy/{policy_name} |

List of IAM Managed Policy ARNs to add to the CodeBuild Service Role. Use when external resources provide policies to interact with them.

#### PostDeploySvcRoleIncludeManagedPolicyArns

Additional managed policies for the PostDeploy service role.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^arn:aws:iam::\d{12}:policy\/[a-zA-Z0-9_\-]+(?:\/[a-zA-Z0-9_\-]+)*$` |
| Constraint Description | Must be an empty string or comma delimited valid IAM Policy ARNs in the format: arn:aws:iam::{account_id}:policy/{policy_name} |

List of IAM Managed Policy ARNs to add to the Post Deploy Stage Service Role. Use when external resources provide policies to interact with them.

#### S3ModuleLocation

S3 bucket name where AWS::Include modules are stored.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None (required) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$` |
| Min Length | 3 |
| Max Length | 63 |
| Constraint Description | Must be a valid S3 bucket name between 3 and 63 characters containing only lowercase letters, numbers, and hyphens. |

This template uses `AWS::Include` to reference modular CloudFormation resources stored in S3. `S3ModuleLocation` specifies the bucket name where these modules are located. The deploying role must have `s3:GetObject` permission on this bucket. Regional buckets provided by 63klabs: `63klabs-atlas-us-east-1`, `63klabs-zenith-us-east-2`, `63klabs-fabric-us-west-1`, `63klabs-orbit-us-west-2`. Admins must supply their own bucket if deploying outside `us-*`.

#### S3ModuleNamespace

Namespace prefix for module paths in S3.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | atlantis |
| Allowed Pattern | `^[a-z0-9][a-z0-9\-]*(\/[a-z0-9][a-z0-9\-]*)*$` |
| Min Length | 1 |
| Max Length | 128 |
| Constraint Description | Must be 1 to 128 characters containing only lowercase alphanumeric characters, hyphens, and forward slashes. Must not start or end with a slash. Each segment between slashes must start with a lowercase alphanumeric character. |

Modules are resolved from `s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/pipeline/<module-name>.yml`. The default namespace is "atlantis".

## Resources

This template creates the following resources:

- [CodePipelineServiceRole](#codepipelineservicerole) - AWS::IAM::Role (Conditional: IsNotDevelopment)
- [CodeBuildServiceRole](#codebuildservicerole) - AWS::IAM::Role
- [PostDeployServiceRole](#postdeployservicerole) - AWS::IAM::Role (Conditional: IsPostDeployEnabledAndNotDev)
- [CodeDeployServiceRole](#codedeployservicerole) - AWS::IAM::Role
- [CloudFormationSvcRole](#cloudformationsvcrole) - AWS::IAM::Role
- [PromoteServiceRole](#promoteservicerole) - AWS::IAM::Role (Conditional: IsPromoteEnabledAndNotDev)
- [PromotionSourceEventServiceRole](#promotionsourceeventservicerole) - AWS::IAM::Role (Conditional: IsNotDevelopment)
- [PromotionSourceEvent](#promotionsourceevent) - AWS::Events::Rule (Conditional: IsNotDevelopment)
- [CodeBuildProject](#codebuildproject) - AWS::CodeBuild::Project
- [CodeBuildLogGroup](#codebuildloggroup) - AWS::Logs::LogGroup
- [PostDeployProject](#postdeployproject) - AWS::CodeBuild::Project (Conditional: IsPostDeployEnabledAndNotDev)
- [PostDeployLogGroup](#postdeployloggroup) - AWS::Logs::LogGroup (Conditional: IsPostDeployEnabledAndNotDev)
- [PromoteProject](#promoteproject) - AWS::CodeBuild::Project (Conditional: IsPromoteEnabledAndNotDev)
- [PromoteLogGroup](#promoteloggroup) - AWS::Logs::LogGroup (Conditional: IsPromoteEnabledAndNotDev)
- [ProjectPipeline](#projectpipeline) - AWS::CodePipeline::Pipeline (Conditional: IsNotDevelopment)
- [PipelineNotificationTopic](#pipelinenotificationtopic) - AWS::SNS::Topic
- [PipelineStartedRule](#pipelinestartedrule) - AWS::Events::Rule
- [PipelineSucceededRule](#pipelinesucceededrule) - AWS::Events::Rule
- [PipelineFailedRule](#pipelinefailedrule) - AWS::Events::Rule
- [PipelineNotificationTopicPolicy](#pipelinenotificationtopicpolicy) - AWS::SNS::TopicPolicy

### CodePipelineServiceRole

Type: AWS::IAM::Role  
Condition: IsNotDevelopment

Service role for CodePipeline to access resources during pipeline execution. Defined inline (not a module) because its policy differs from the origin templates: there are **no** source-provider permissions (no CodeCommit, no CodeConnections). The S3 Source action reads the promoted archive from `S3ArtifactsBucket`, which is already covered by the artifacts-management statement.

**Key Permissions:**
- **BuildPhase**: Full access to the Build, PostDeploy, and Promote CodeBuild projects
- **CodeBuildReportGroup**: Access to report groups tagged with this deployment
- **DeployPhaseCloudFormation**: Full access to the application CloudFormation stack/stackset
- **ManageArtifactsInS3**: Read/write access to `S3ArtifactsBucket` (covers both the S3 Source read and the pipeline `ArtifactStore`)
- **PassRole**: `iam:PassRole` for `CloudFormationSvcRole`

### CodeBuildServiceRole

Type: AWS::IAM::Role  
Module: `templates/v2/modules/pipeline/codebuild-service-role.yml`

Service role for the Build stage CodeBuild project. Same module used by the origin templates, providing logs, artifacts, Parameter Store, and static-host bucket access.

### PostDeployServiceRole

Type: AWS::IAM::Role  
Condition: IsPostDeployEnabledAndNotDev  
Module: `templates/v2/modules/pipeline/postdeploy-service-role.yml`

Service role for the PostDeploy CodeBuild project. Only created when `PostDeployStageEnabled="true"`. Mirrors `CodeBuildServiceRole` permissions so Build and PostDeploy stages have consistent capabilities.

### CodeDeployServiceRole

Type: AWS::IAM::Role  
Module: `templates/v2/modules/pipeline/codedeploy-service-role.yml`

Service role passed to application infrastructure for Lambda function deployments (gradual deployment strategies).

### CloudFormationSvcRole

Type: AWS::IAM::Role  
Module: `templates/v2/modules/pipeline/cloudformation-svc-role.yml`

Service role for CloudFormation to create and manage the application infrastructure stack. Same module used by the origin templates.

### PromoteServiceRole

Type: AWS::IAM::Role  
Condition: IsPromoteEnabledAndNotDev  
Module: `templates/v2/modules/pipeline/promote-service-role.yml`

Sole cross-account writer for chained promotion. Only created when `PromoteTargetStageId` is non-empty and the environment is not `DEV`. Read access is scoped to the local `S3ArtifactsBucket` (to read the `SourceArtifact`); write access is scoped to `promotions/*` on the resolved `PromoteTargetBucket`. Neither `CodeBuildServiceRole` nor `PostDeployServiceRole` is granted this cross-account write permission.

### PromotionSourceEventServiceRole

Type: AWS::IAM::Role  
Condition: IsNotDevelopment  
Module: `templates/v2/modules/pipeline/promotion-source-event-service-role.yml`

IAM role assumed by EventBridge to call `codepipeline:StartPipelineExecution` on this pipeline when a promoted `source.zip` arrives in the artifacts bucket.

### PromotionSourceEvent

Type: AWS::Events::Rule  
Condition: IsNotDevelopment  
Module: `templates/v2/modules/pipeline/promotion-source-event-rule.yml`

EventBridge rule that detects the arrival of the promoted `source.zip` at `promotions/${Prefix}-${ProjectId}/${StageId}/source.zip` in the account-wide artifacts bucket and starts this pipeline. Requires EventBridge notifications enabled on the artifacts bucket (`account-wide-infrastructure.yml`, `EnablePromotionTrigger=true`).

### CodeBuildProject

Type: AWS::CodeBuild::Project  
Module: `templates/v2/modules/pipeline/codebuild-project.yml`

CodeBuild project for the Build stage. Same image/compute/environment-variable set as the origin templates.

### CodeBuildLogGroup

Type: AWS::Logs::LogGroup  
Module: `templates/v2/modules/pipeline/codebuild-log-group.yml`

CloudWatch log group for the Build CodeBuild project, with a 90-day retention policy.

### PostDeployProject

Type: AWS::CodeBuild::Project  
Condition: IsPostDeployEnabledAndNotDev  
Module: `templates/v2/modules/pipeline/postdeploy-project.yml`

CodeBuild project for the optional PostDeploy stage. Uses the same compute environment, container image, and core environment variables as the Build stage.

### PostDeployLogGroup

Type: AWS::Logs::LogGroup  
Condition: IsPostDeployEnabledAndNotDev  
Module: `templates/v2/modules/pipeline/postdeploy-log-group.yml`

CloudWatch log group for the PostDeploy CodeBuild project, with retention matching `CodeBuildLogGroup`.

### PromoteProject

Type: AWS::CodeBuild::Project  
Condition: IsPromoteEnabledAndNotDev  
Module: `templates/v2/modules/pipeline/promote-project.yml`

Framework-owned CodeBuild project for the optional chained Promote stage. Uses an inline (non-overridable) buildspec that re-uploads the `SourceArtifact` as `source.zip` plus an audit manifest (`promote.json`) into the next stage's `promotions/` area.

### PromoteLogGroup

Type: AWS::Logs::LogGroup  
Condition: IsPromoteEnabledAndNotDev  
Module: `templates/v2/modules/pipeline/promote-log-group.yml`

CloudWatch log group for the Promote CodeBuild project.

### ProjectPipeline

Type: AWS::CodePipeline::Pipeline  
Condition: IsNotDevelopment

The main CodePipeline that orchestrates the receiving/promoted-artifact workflow.

**Stage order** (optional stages in brackets are conditionally included):

```
Source(S3) -> [ApproveRelease] -> Build -> [Deploy] -> [PostDeploy] -> [ApproveToPromote] -> [Promote]
```

- **Source**: `S3` provider action named `PromotedArtifact`. Reads `promotions/${Prefix}-${ProjectId}/${StageId}/source.zip` from `S3ArtifactsBucket`, with `PollForSourceChanges: "false"`.
- **[ApproveRelease]**: Manual approval action named `ApproveRelease`, included when `IsReleaseApprovalRequired`. Publishes to `PipelineNotificationTopic`.
- **Build**: CodeBuild action running the `${Prefix}-${ProjectId}-${StageId}-Build` project.
- **[Deploy]**: `GenerateChangeSet` + `ExecuteChangeSet` CloudFormation actions against the `${Prefix}-${ProjectId}-${StageId}-application` stack, included when `IsDeployStageEnabled`.
- **[PostDeploy]**: CodeBuild action running the `${Prefix}-${ProjectId}-${StageId}-PostDeploy` project, included when `IsPostDeployEnabled`.
- **[ApproveToPromote]**: Manual approval action named `ApproveToPromote`, included when `IsPromoteEnabledAndApprovalRequired`.
- **[Promote]**: CodeBuild action running the `${Prefix}-${ProjectId}-${StageId}-Promote` project, included when `IsPromoteEnabled`.

**Key Properties:**
- Artifact store: `S3ArtifactsBucket` (the same bucket used for the S3 Source)
- Service role: `CodePipelineServiceRole`

> **Note:** The approval action names (`ApproveRelease`, `ApproveToPromote`) are fixed strings so their presence/absence can be detected programmatically by the approval-audit CLI.

### PipelineNotificationTopic

Type: AWS::SNS::Topic  
Module: `templates/v2/modules/pipeline/pipeline-notification-topic.yml`

SNS topic for pipeline execution notifications with an email subscription to `AlarmNotificationEmail`. Also used as the `NotificationArn` for the `ApproveRelease` and `ApproveToPromote` manual approval actions.

### PipelineStartedRule

Type: AWS::Events::Rule  
Module: `templates/v2/modules/pipeline/pipeline-notification-started-rule.yml`

EventBridge rule that sends a notification when pipeline execution starts.

### PipelineSucceededRule

Type: AWS::Events::Rule  
Module: `templates/v2/modules/pipeline/pipeline-notification-succeeded-rule.yml`

EventBridge rule that sends a notification when pipeline execution succeeds.

### PipelineFailedRule

Type: AWS::Events::Rule  
Module: `templates/v2/modules/pipeline/pipeline-notification-failed-rule.yml`

EventBridge rule that sends a notification when pipeline execution fails.

### PipelineNotificationTopicPolicy

Type: AWS::SNS::TopicPolicy  
Module: `templates/v2/modules/pipeline/pipeline-notification-topic-policy.yml`

Policy that allows EventBridge to publish messages to `PipelineNotificationTopic`.

## Outputs

### ProjectPipeline

Condition: IsNotDevelopment

CodePipeline console link for the receiving (promoted-artifact) pipeline.

**Value:** `https://${AWS::Region}.console.aws.amazon.com/codesuite/codepipeline/pipelines/${Prefix}-${ProjectId}-${StageId}-Pipeline/view?region=${AWS::Region}`

### PipelineName

Name of the receiving CodePipeline (empty/unused in DEV, where the pipeline is not created).

**Value:** `${Prefix}-${ProjectId}-${StageId}-Pipeline`

### WatchedPromotionKey

The S3 object key (in `S3ArtifactsBucket`) that triggers this pipeline. An origin pipeline's Promote stage writes the promoted `source.zip` here, which the `PromotionSourceEvent` rule watches to start this pipeline.

**Value:** `promotions/${Prefix}-${ProjectId}/${StageId}/source.zip`

**Usage:** Use this value to confirm the sending pipeline's `PromoteTargetStageId` (and derived `PromoteTargetBucket`) match what this pipeline is actually watching.

### ReleaseApprovalGate

Whether the incoming `ApproveRelease` manual gate is active.

**Value:** `Enabled (ApproveRelease)` when `ReleaseApprovalRequired=true`, otherwise `Disabled (auto-release)`.

**Usage:** `Enabled` means an incoming promoted artifact pauses after Source until a human approves; `Disabled` means every incoming promotion auto-releases (builds/deploys) with no human review at this stage.

### PromotionTarget

Condition: IsPromoteEnabled

The downstream `StageId` this pipeline chains promotion to (the Promote stage target). Only present when chained promotion is enabled (`PromoteTargetStageId` non-empty).

**Value:** `${PromoteTargetStageId}`

### PromoteApprovalGate

Condition: IsPromoteEnabled

Whether the outbound `ApproveToPromote` manual gate is active for chained promotion. Only present when chained promotion is enabled.

**Value:** `Enabled (ApproveToPromote)` when `PromoteApprovalRequired=true`, otherwise `Disabled (auto-promote)`.

**Usage:** `Enabled` means a human must approve before promoting to the target stage; `Disabled` means promotion happens automatically.

## Conditions

The template uses several conditions to control resource creation:

- **IsNotDevelopment**: True when `DeployEnvironment` is not "DEV"
- **UseS3BucketNameOrgPrefix**: True when `S3BucketNameOrgPrefix` is not empty
- **HasPermissionsBoundaryArn**: True when `PermissionsBoundaryArn` is not empty
- **HasS3StaticHostBucket**: True when `S3StaticHostBucket` is not empty
- **HasS3BuildSpecLocation**: True when `BuildSpec` starts with "s3:"
- **UseDefaultBuildSpecLocation**: True when `BuildSpec` is empty
- **HasManagedPoliciesForCodeBuildSvcRole**: True when `CodeBuildSvcRoleIncludeManagedPolicyArns` is not empty
- **HasManagedPoliciesForCloudFormationSvcRole**: True when `CloudFormationSvcRoleIncludeManagedPolicyArns` is not empty
- **IsPostDeployEnabled**: True when `PostDeployStageEnabled` is "true"
- **HasPostDeployS3StaticHostBucket**: True when `PostDeployS3StaticHostBucket` is not empty
- **HasPostDeployBuildSpecS3Location**: True when PostDeploy is enabled and `PostDeployBuildSpec` starts with "s3:"
- **UseDefaultPostDeployBuildSpecLocation**: True when `PostDeployBuildSpec` is empty
- **HasManagedPoliciesForPostDeploySvcRole**: True when `PostDeploySvcRoleIncludeManagedPolicyArns` is not empty
- **IsPostDeployEnabledAndNotDev**: True when both `IsNotDevelopment` and `IsPostDeployEnabled` are true
- **IsReleaseApprovalRequired**: True when `ReleaseApprovalRequired` is "true" - controls the `ApproveRelease` stage
- **IsDeployStageEnabled**: True when `DeployStageEnabled` is "true" - controls the Deploy stage
- **IsPromoteEnabled**: True when `PromoteTargetStageId` is not empty - controls the Promote stage
- **IsPromoteApprovalRequired**: True when `PromoteApprovalRequired` is "true"
- **IsPromoteEnabledAndApprovalRequired**: True when both `IsPromoteEnabled` and `IsPromoteApprovalRequired` - controls the `ApproveToPromote` stage
- **IsPromoteEnabledAndNotDev**: True when both `IsNotDevelopment` and `IsPromoteEnabled` - controls Promote resources
- **HasPromoteTargetAccount**: True when `PromoteTargetAccountId` is not empty
- **HasPromoteTargetRegion**: True when `PromoteTargetRegion` is not empty
- **HasPromoteTargetBucket**: True when `PromoteTargetBucket` is not empty

## Examples

### Basic Receiving Pipeline (Same-Account Promotion)

```yaml
Parameters:
  Prefix: "acme"
  ProjectId: "myapp"
  StageId: "beta"
  DeployEnvironment: "PROD"
  S3ArtifactsBucket: "cf-artifacts-123456789012-us-east-1-an"
  BuildSpec: "application-infrastructure/buildspec.yml"
  ReleaseApprovalRequired: "true"
  DeployStageEnabled: "true"
  AlarmNotificationEmail: "devops@example.com"
  S3ModuleLocation: "63klabs-atlas-us-east-1"
```

The origin pipeline (deployed with `template-pipeline.yml` or similar) should set `PromoteTargetStageId: "beta"` to route into this pipeline.

### Cross-Account Receiving Pipeline

```yaml
Parameters:
  Prefix: "acme"
  ProjectId: "myapp"
  StageId: "prod"
  DeployEnvironment: "PROD"
  S3ArtifactsBucket: "cf-artifacts-999999999999-us-east-1-an"
  ReleaseApprovalRequired: "true"
  AlarmNotificationEmail: "prod-devops@example.com"
  S3ModuleLocation: "63klabs-atlas-us-east-1"
```

Deployed in the receiving (PROD) account. The account-wide `account-wide-infrastructure.yml` stack in this account must set `PromotionSourceAccountIds` to include the sending account, and `EnablePromotionTrigger: "true"`. The sending pipeline (in a different account) sets `PromoteTargetStageId: "prod"`, `PromoteTargetAccountId: "999999999999"`.

### Chained Promotion (beta -> prod)

```yaml
Parameters:
  Prefix: "acme"
  ProjectId: "myapp"
  StageId: "beta"
  DeployEnvironment: "PROD"
  S3ArtifactsBucket: "cf-artifacts-123456789012-us-east-1-an"
  ReleaseApprovalRequired: "true"
  PromoteTargetStageId: "prod"
  PromoteApprovalRequired: "true"
  PromoteTargetAccountId: "999999999999"
  AlarmNotificationEmail: "devops@example.com"
  S3ModuleLocation: "63klabs-atlas-us-east-1"
```

This receiving pipeline (`beta`) both accepts promotions from an upstream `test` pipeline and, once its own Build/Deploy/PostDeploy succeed and `ApproveToPromote` is approved, promotes onward to a `prod` receiving pipeline in another account.

### Build-Only Receiving Workload

```yaml
Parameters:
  Prefix: "acme"
  ProjectId: "static-site"
  StageId: "prod"
  DeployEnvironment: "PROD"
  S3ArtifactsBucket: "cf-artifacts-123456789012-us-east-1-an"
  DeployStageEnabled: "false"
  S3StaticHostBucket: "acme-static-site-prod"
  AlarmNotificationEmail: "devops@example.com"
  S3ModuleLocation: "63klabs-atlas-us-east-1"
```

## Troubleshooting

### Pipeline Not Triggering

**Symptom:** The receiving pipeline never starts after the sending pipeline's Promote stage completes.

**Possible Causes:**
- `EnablePromotionTrigger` is `false` (or unset) on this account's `account-wide-infrastructure.yml` stack.
- The sending pipeline's `PromoteTargetStageId` does not exactly match this template's `StageId`.
- Cross-account: `PromotionSourceAccountIds` on `account-wide-infrastructure.yml` does not include the sending account, so the write failed with `AccessDenied` before the trigger object was written.
- `Prefix`/`ProjectId` mismatch between sending and receiving accounts.

**Solutions:**
1. Confirm `EnablePromotionTrigger: "true"` on the receiving account's `account-wide-infrastructure.yml`.
2. Compare the `WatchedPromotionKey` output on this stack against the sending pipeline's Promote CodeBuild logs (the key it wrote to).
3. For cross-account, verify `PromotionSourceAccountIds` includes the sending account and that the writer role matches `*-PromoteServiceRole`.
4. Check the sending pipeline's Promote CodeBuild logs for S3 `PutObject` errors.

### ApproveRelease Never Appears

**Symptom:** Expected a manual approval before Build, but the pipeline goes straight from Source to Build.

**Solution:** Confirm `ReleaseApprovalRequired` is `"true"` (the default). If it was intentionally set to `"false"`, review the [security warning](#releaseapprovalrequired) above - every incoming promotion will auto-release.

### Cross-Account Write Denied

**Symptom:** The sending pipeline's Promote stage fails with an S3 `AccessDenied` error.

**Solutions:**
1. Confirm the receiving account's `account-wide-infrastructure.yml` includes the sending account ID in `PromotionSourceAccountIds`.
2. Confirm the sending pipeline's writer role name ends in `-PromoteServiceRole` (the bucket policy condition matches this pattern).
3. Confirm the write is scoped to the `promotions/*` prefix only - writes outside this prefix are denied by design.

### Build or Deploy Stage Fails

Same troubleshooting steps as the origin templates apply once past the Source stage - see [template-pipeline-README.md](template-pipeline-README.md#troubleshooting) for Build/Deploy/PostDeploy guidance, since these stages use identical modules and behavior.

## Use With

- **Origin Pipelines** (write the promoted artifact):
  - [template-pipeline.yml](template-pipeline-README.md)
  - [template-pipeline-github.yml](template-pipeline-github-README.md)
  - [template-pipeline-build-only.yml](template-pipeline-build-only-README.md)
- **Account-Wide Infrastructure** (artifacts bucket, EventBridge, cross-account policy):
  - [account-wide-infrastructure.yml](../account/account-wide-infrastructure-README.md)
- Application Infrastructure (API Gateway, Event Bridge, Lambda, Step Functions, S3, DynamoDB, etc)
- OPTIONAL: Route53 and CloudFront for custom domains

## Related Templates

This template is commonly used with:

- **Origin Pipelines**:
  - [template-pipeline.yml](template-pipeline-README.md) - CodeCommit-sourced origin pipeline with a Promote stage
  - [template-pipeline-github.yml](template-pipeline-github-README.md) - GitHub-sourced origin pipeline with a Promote stage
  - [template-pipeline-build-only.yml](template-pipeline-build-only-README.md) - Build-only origin pipeline with a Promote stage

- **Account Templates**:
  - [account-wide-infrastructure.yml](../account/account-wide-infrastructure-README.md) - Account-wide artifacts bucket, cross-account promotion policy, and EventBridge opt-in

- **Application Infrastructure**: Your SAM template being deployed by the pipeline

## Tutorials

- Atlantis Tutorials: [https://github.com/63Klabs/atlantis-sam-templates/](https://github.com/63Klabs/atlantis-sam-templates/)

## Security Considerations

1. **Two Independent Approval Gates**: `ApproveRelease` (incoming) and `ApproveToPromote` (outbound) both default to `true` and must be explicitly disabled to remove human review.
2. **No Source-Provider Permissions**: `CodePipelineServiceRole` grants no CodeCommit or CodeConnections access since the source is an S3 object already covered by the artifacts-bucket permissions.
3. **Sole Cross-Account Writer**: Only `PromoteServiceRole` (used by the optional chained Promote stage) can write cross-account, and only to the `promotions/*` prefix of the resolved target bucket.
4. **Least Privilege**: All IAM roles follow least-privilege principles with scoped permissions; no AWS managed full-access policies are used.
5. **Permissions Boundaries**: Support for permissions boundaries to enforce organizational policies.
6. **Auditability**: Fixed approval action names (`ApproveRelease`, `ApproveToPromote`) allow the [approval-audit CLI](../../../admin-ops/README.md) to detect deployed pipelines with either gate disabled.

## Cost Considerations

**Monthly Costs (approximate):**
- CodePipeline: $1 per active pipeline
- CodeBuild: $0.005 per build minute (BUILD_GENERAL1_SMALL), across Build, optional PostDeploy, and optional Promote projects
- S3: Storage costs for the promoted archive, audit manifest, and pipeline artifacts (shared with the account-wide artifacts bucket)
- CloudWatch Logs: $0.50 per GB ingested + $0.03 per GB stored, across Build/PostDeploy/Promote log groups
- SNS: $0.50 per million notifications (minimal)
- EventBridge: No additional charge for the promotion-trigger rule beyond standard event ingestion

## Additional Resources

- [AWS CodePipeline User Guide](https://docs.aws.amazon.com/codepipeline/latest/userguide/)
- [AWS CodeBuild User Guide](https://docs.aws.amazon.com/codebuild/latest/userguide/)
- [Amazon S3 Event Notifications with EventBridge](https://docs.aws.amazon.com/AmazonS3/latest/userguide/EventBridge.html)
- [AWS SAM Developer Guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/)
- [GitHub Repository](https://github.com/63Klabs/atlantis-sam-templates/)
