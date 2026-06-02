# account-wide-infrastructure

Account-wide resources: ABAC-scoped managed policies, shared connections, and optional S3 artifacts bucket — Assembled from reusable modules.

**Version:** v0.0.0/2026-04-28  
**Template:** [templates/v2/account/account-wide-infrastructure.yml](../../../../templates/v2/account/account-wide-infrastructure.yml)

## Overview

This template creates account-wide infrastructure for the Atlantis DevOps Platform. It assembles shared resources from reusable module snippets stored in S3 using `AWS::Include` transforms. Resources include ABAC-scoped managed policies for CloudFormation service roles, shared GitHub connections, optional API Gateway CloudWatch logging, and an optional shared S3 artifacts bucket.

### Use Cases

- Deploy ABAC-scoped managed policies (CodeBuild CRUD, Cognito CRUD) for CloudFormation service roles
- Create a shared GitHub connection for all pipeline templates in the account
- Enable account-level API Gateway CloudWatch logging (one-time per-region setup)
- Provision a shared S3 artifacts bucket accessible by all pipeline roles

### Prerequisites

- S3 bucket containing the Atlantis module snippets (provided by 63klabs regional buckets or your own)
- IAM permissions to create managed policies, IAM roles, CodeConnections, and S3 buckets
- (Optional) Existing S3 access log bucket if enabling artifacts bucket logging

### Important Notes

- This template should be deployed **once per account per region** before any project-specific templates
- The GitHub connection requires manual authorization in the AWS Console after deployment
- All optional resources are disabled by default — enable them via parameters
- Module snippets are loaded from S3 at deploy time via `AWS::Include` transforms
- Resources use conditions for optional creation — no errors occur when features are disabled

## Parameters

### Organization Naming

Parameters that define the organization-level naming for exported resources.

- [OrgPrefix](#orgprefix)

### IAM Configuration

IAM path configuration for managed policies and roles.

- [RolePath](#rolepath)

### GitHub Connection

Configuration for the shared GitHub connection via AWS CodeConnections.

- [GitHubOrg](#githuborg)

### API Gateway

Optional API Gateway CloudWatch logging configuration.

- [EnableApiGwCloudWatchLogs](#enableapigwcloudwatchlogs)

### S3 Artifacts Bucket

Optional shared S3 artifacts bucket for pipeline build artifacts.

- [EnableS3ArtifactsBucket](#enables3artifactsbucket)
- [S3BucketNameOrgPrefix](#s3bucketnameorgprefix)
- [S3LogBucketName](#s3logbucketname)

### Module Source

Configuration for where module snippets are loaded from.

- [S3ModuleLocation](#s3modulelocation)
- [S3ModuleNamespace](#s3modulenamespace)

---

#### OrgPrefix

Organization-level prefix prepended to managed policy names for identification and grouping. For example, 'ACME' would produce policy names like 'ACME-ProjectPipeline-CodeBuildCrud'.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | ACME |
| Allowed Pattern | `^[A-Z][A-Z0-9-]{0,18}[A-Z0-9]$` |
| Min Length | 2 |
| Max Length | 20 |
| Constraint Description | 2 to 20 characters. Upper case alphanumeric and dashes. Must start with a letter and end with a letter or number. |

#### RolePath

Path to use for IAM Managed Policies created by this template. Use to organize policies within your IAM structure.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\/([a-zA-Z0-9-_]+[\/])+$\|^\/$` |
| Constraint Description | May only contain alphanumeric characters, forward slashes, underscores, and dashes. Must begin and end with a slash. |

#### GitHubOrg

GitHub organization or username to connect to. Leave empty to skip creating a GitHub connection.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |

> **Note:** After deployment, you must manually authorize the GitHub connection in the AWS Console at CodeConnections → Connections. The connection will remain in PENDING status until authorized.

#### EnableApiGwCloudWatchLogs

Set to 'true' to create the account-level IAM role and API Gateway Account configuration required for API Gateway to push logs to CloudWatch. This is a one-time, per-account, per-region setup.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | false |
| Allowed Values | true, false |
| Constraint Description | Must be 'true' or 'false'. |

#### EnableS3ArtifactsBucket

Set to 'true' to create a shared, account-wide S3 artifacts bucket for pipeline build artifacts. This bucket is accessible by all pipeline roles in the account.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | false |
| Allowed Values | true, false |
| Constraint Description | Must be 'true' or 'false'. |

> **Note:** When enabled, this creates an S3 bucket with a bucket policy granting access to all CodePipeline, CodeBuild, and CloudFormation service roles in the account (regardless of prefix). This is an alternative to per-project artifacts buckets created by `template-storage-s3-artifacts.yml`.

#### S3BucketNameOrgPrefix

Optional lowercase organization prefix prepended to the S3 artifacts bucket name for uniqueness. Leave empty to omit. Example: 'acme' would produce 'acme-cf-artifacts-123456789012-us-east-1-an'.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,18}[a-z0-9]$\|^$` |
| Constraint Description | May be empty or 2 to 20 characters (8 or less recommended). Lower case alphanumeric and dashes. Must start and end with a letter or number. |

> **Tip:** Keep this prefix short (8 characters or less) to avoid exceeding the 63-character S3 bucket name limit. The full bucket name follows the pattern: `[S3BucketNameOrgPrefix-]cf-artifacts-{AccountId}-{Region}-an`.

#### S3LogBucketName

Optional S3 bucket name for server access logging of the artifacts bucket. Leave empty to disable logging.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$\|^$` |
| Constraint Description | Must be a valid S3 bucket name or empty. Must be between 3 and 63 characters long. Lower case alphanumeric and dashes. Must start and end with a letter or number. |

> **Important:** The log bucket must already exist before deploying this template with logging enabled. The log bucket should have appropriate permissions to receive S3 server access logs.

#### S3ModuleLocation

S3 bucket name containing module snippets. Modules are loaded from `s3://<S3ModuleLocation>/<S3ModuleNamespace>/templates/v2/modules/*`.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None (required) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$` |
| Min Length | 3 |
| Max Length | 63 |
| Constraint Description | Must be a valid S3 bucket name between 3 and 63 characters containing only lowercase letters, numbers, and hyphens. |

**Regional buckets provided by 63klabs:**
- `63klabs-atlas-us-east-1` (US East - N. Virginia)
- `63klabs-zenith-us-east-2` (US East - Ohio)
- `63klabs-fabric-us-west-1` (US West - N. California)
- `63klabs-orbit-us-west-2` (US West - Oregon)

Admins must supply their own bucket if deploying outside these regions.

#### S3ModuleNamespace

Namespace prefix within the S3 module bucket. This is the path prefix where modules are stored. Modules are loaded from `s3://<BucketName>/<S3ModuleNamespace>/templates/v2/modules/*`.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | atlantis |
| Allowed Pattern | `^[a-z0-9][a-z0-9\-]*(/[a-z0-9][a-z0-9\-]*)*$` |
| Min Length | 1 |
| Max Length | 128 |
| Constraint Description | Must be 1 to 128 characters containing only lowercase alphanumeric characters, hyphens, and forward slashes. Must not start or end with a slash. Each segment between slashes must start with a lowercase alphanumeric character. |

## Resources

- [CloudFormationCodeBuildPolicy](#cloudformationcodebuildpolicy) - AWS::IAM::ManagedPolicy (via AWS::Include)
- [CloudFormationCognitoPolicy](#cloudformationcognitopolicy) - AWS::IAM::ManagedPolicy (via AWS::Include)
- [GitHubConnection](#githubconnection) - AWS::CodeStarConnections::Connection (Conditional: HasGitHubOrg, via AWS::Include)
- [ApiGatewayCloudWatchLogsRole](#apigatewaycloudwatchlogsrole) - AWS::IAM::Role (Conditional: EnableApiGatewayLogging, via AWS::Include)
- [ApiGatewayAccount](#apigatewayaccount) - AWS::ApiGateway::Account (Conditional: EnableApiGatewayLogging, via AWS::Include)
- [S3ArtifactsBucketRegional](#s3artifactsbucketregional) - AWS::S3::Bucket (Conditional: EnableS3ArtifactsBucket, via AWS::Include)
- [S3ArtifactBucketPolicy](#s3artifactbucketpolicy) - AWS::S3::BucketPolicy (Conditional: EnableS3ArtifactsBucket, via AWS::Include)

### CloudFormationCodeBuildPolicy

Type: AWS::IAM::ManagedPolicy (via AWS::Include)

ABAC-scoped managed policy granting CodeBuild and CloudWatch Logs CRUD permissions. Scoped via the `atlantis:ApplicationDeploymentId` tag on the principal. Attach this policy to CloudFormation service roles that need to create and manage CodeBuild projects and their associated log groups.

**Module Source:** `templates/v2/modules/pipeline-policies/codebuild-crud.yml`

### CloudFormationCognitoPolicy

Type: AWS::IAM::ManagedPolicy (via AWS::Include)

ABAC-scoped managed policy granting Cognito User Pool CRUD permissions. Scoped via the `atlantis:ApplicationDeploymentId` tag on the principal. Attach this policy to CloudFormation service roles that need to manage Cognito User Pools.

**Module Source:** `templates/v2/modules/pipeline-policies/cognito-crud.yml`

### GitHubConnection

Type: AWS::CodeStarConnections::Connection (via AWS::Include)  
Condition: HasGitHubOrg

Creates a shared GitHub connection via AWS CodeConnections. This connection is used by pipeline templates as the source provider for GitHub repositories. The connection requires manual authorization in the AWS Console after creation.

**Module Source:** `templates/v2/modules/account-wide/codeconnections-github.yml`

> **Manual Step Required:** After deployment, navigate to AWS Console → Developer Tools → Connections and complete the pending connection authorization with your GitHub account.

### ApiGatewayCloudWatchLogsRole

Type: AWS::IAM::Role (via AWS::Include)  
Condition: EnableApiGatewayLogging

Creates an IAM role that allows API Gateway to push logs to CloudWatch. This is a one-time, per-account, per-region configuration.

**Module Source:** `templates/v2/modules/account-wide/apigw-cloudwatch-role.yml`

### ApiGatewayAccount

Type: AWS::ApiGateway::Account (via AWS::Include)  
Condition: EnableApiGatewayLogging  
DependsOn: ApiGatewayCloudWatchLogsRole

Configures the API Gateway account settings to use the CloudWatch logging role. This enables all API Gateway stages in the account/region to push execution and access logs to CloudWatch.

**Module Source:** `templates/v2/modules/account-wide/apigw-cloudwatch-account.yml`

### S3ArtifactsBucketRegional

Type: AWS::S3::Bucket (via AWS::Include)  
Condition: EnableS3ArtifactsBucket

Creates a shared S3 artifacts bucket for pipeline build artifacts. The bucket is accessible by all pipeline roles in the account regardless of prefix.

**Key Configuration:**
- **Bucket Name:** `[S3BucketNameOrgPrefix-]cf-artifacts-{AccountId}-{Region}-an`
- **DeletionPolicy:** Retain (preserves artifacts if stack is deleted)
- **Versioning:** Enabled
- **Encryption:** AES256 server-side encryption
- **Public Access:** Fully blocked (all four public access blocks enabled)
- **Lifecycle:** Objects expire after 395 days, noncurrent versions after 30 days, incomplete multipart uploads abort after 1 day
- **Logging:** Conditional on S3LogBucketName parameter

**Module Source:** `templates/v2/modules/account-wide/s3-artifacts-bucket.yml`

### S3ArtifactBucketPolicy

Type: AWS::S3::BucketPolicy (via AWS::Include)  
Condition: EnableS3ArtifactsBucket

Bucket policy for the shared S3 artifacts bucket. Enforces HTTPS-only access and grants permissions to all pipeline service roles in the account.

**Policy Statements:**
| Statement | Effect | Principal | Actions |
|-----------|--------|-----------|---------|
| DenyNonSecureTransportAccess | Deny | * | s3:* (when SecureTransport=false) |
| WhitelistedGet | Allow | CodePipeline/CodeBuild/CloudFormation roles | s3:GetObject, s3:GetObjectVersion, s3:GetBucketVersioning |
| WhitelistedPut | Allow | CodePipeline/CodeBuild roles | s3:PutObject |

**Principal Patterns (unprefixed wildcards):**
- `arn:aws:iam::{AccountId}:role{RolePath}CodePipelineServiceRole-*`
- `arn:aws:iam::{AccountId}:role{RolePath}CodeBuildServiceRole-*`
- `arn:aws:iam::{AccountId}:role{RolePath}CloudFormationSvcRole-*`

**Module Source:** `templates/v2/modules/account-wide/s3-artifacts-bucket-policy.yml`

> **Note:** Unlike the per-project `template-storage-s3-artifacts.yml`, this bucket policy uses unprefixed wildcard patterns, granting access to ALL pipeline roles in the account regardless of their Prefix. This is intentional for account-wide shared usage.

## Outputs

### CodeBuildCrudPolicyArn

ARN of the CodeBuild CRUD managed policy. Pass this to pipeline templates via the `CloudFormationSvcRoleIncludeManagedPolicyArns` parameter.

| Attribute | Value |
|-----------|-------|
| Export Name | `{OrgPrefix}-ProjectPipeline-CodeBuildCrud-Arn` |
| Example Value | `arn:aws:iam::123456789012:policy/ACME-ProjectPipeline-CodeBuildCrud` |

### CodeBuildCrudPolicyName

Name of the CodeBuild CRUD managed policy.

| Attribute | Value |
|-----------|-------|
| Example Value | `ACME-ProjectPipeline-CodeBuildCrud` |

### CognitoCrudPolicyArn

ARN of the Cognito CRUD managed policy. Pass this to pipeline templates via the `CloudFormationSvcRoleIncludeManagedPolicyArns` parameter.

| Attribute | Value |
|-----------|-------|
| Export Name | `{OrgPrefix}-ProjectPipeline-CognitoCrud-Arn` |
| Example Value | `arn:aws:iam::123456789012:policy/ACME-ProjectPipeline-CognitoCrud` |

### CognitoCrudPolicyName

Name of the Cognito CRUD managed policy.

| Attribute | Value |
|-----------|-------|
| Example Value | `ACME-ProjectPipeline-CognitoCrud` |

### GitHubConnectionArn

Condition: HasGitHubOrg

ARN of the GitHub connection. Pass this to pipeline templates via the `GitHubConnectionArn` parameter.

| Attribute | Value |
|-----------|-------|
| Export Name | `{OrgPrefix}-GitHub-Connection-Arn` |
| Example Value | `arn:aws:codeconnections:us-east-1:123456789012:connection/abc123-def456-789` |

> **Note:** You must manually complete the connection in the AWS Console before it can be used by pipeline templates.

### GitHubConnectionStatus

Condition: HasGitHubOrg

Status of the GitHub connection. Will show PENDING until manually authorized in the AWS Console.

| Attribute | Value |
|-----------|-------|
| Example Value | `PENDING` or `AVAILABLE` |

### CodeConnectionsConsole

Condition: HasGitHubOrg

URL to complete the GitHub connection setup in the AWS Console.

| Attribute | Value |
|-----------|-------|
| Example Value | `https://us-east-1.console.aws.amazon.com/codesuite/settings/connections` |

### ApiGatewayCloudWatchLogsRoleArn

Condition: EnableApiGatewayLogging

ARN of the IAM role used by API Gateway to push logs to CloudWatch.

| Attribute | Value |
|-----------|-------|
| Export Name | `{OrgPrefix}-ApiGateway-CloudWatch-Role-Arn` |
| Example Value | `arn:aws:iam::123456789012:role/ACME-ApiGateway-CloudWatchLogs` |

### S3ArtifactsBucketName

Condition: EnableS3ArtifactsBucket

Name of the S3 artifacts bucket for pipeline build artifacts.

| Attribute | Value |
|-----------|-------|
| Export Name | `{OrgPrefix}-S3-Artifacts-Bucket-Name` |
| Example Value | `acme-cf-artifacts-123456789012-us-east-1-an` |

### S3ArtifactsBucketConsole

Condition: EnableS3ArtifactsBucket

S3 console link for the artifacts bucket.

| Attribute | Value |
|-----------|-------|
| Example Value | `https://s3.console.aws.amazon.com/s3/buckets/acme-cf-artifacts-123456789012-us-east-1-an` |

### IamPoliciesConsole

IAM Policies console link for quick access to view created policies.

| Attribute | Value |
|-----------|-------|
| Example Value | `https://console.aws.amazon.com/iam/home#/policies` |

## Conditions

| Condition | Logic | Purpose |
|-----------|-------|---------|
| HasGitHubOrg | GitHubOrg ≠ "" | Controls GitHub connection creation |
| EnableApiGatewayLogging | EnableApiGwCloudWatchLogs = "true" | Controls API Gateway CloudWatch role and account configuration |
| EnableS3ArtifactsBucket | EnableS3ArtifactsBucket = "true" | Controls S3 artifacts bucket and policy creation |
| UseS3BucketNameOrgPrefix | S3BucketNameOrgPrefix ≠ "" | Determines if org prefix is prepended to bucket name |
| HasLoggingBucket | S3LogBucketName ≠ "" | Determines if S3 server access logging is enabled |

## Examples

### Minimal Deployment (Policies Only)

Deploy with just the mandatory parameters to get ABAC-scoped managed policies:

```
OrgPrefix: ACME
RolePath: /
S3ModuleLocation: 63klabs-atlas-us-east-1
S3ModuleNamespace: atlantis
```

### Full Deployment with All Features

Enable all optional features:

```
OrgPrefix: ACME
RolePath: /service-roles/
GitHubOrg: my-github-org
EnableApiGwCloudWatchLogs: true
EnableS3ArtifactsBucket: true
S3BucketNameOrgPrefix: acme
S3LogBucketName: acme-access-logs-123456789012-us-east-1-an
S3ModuleLocation: 63klabs-atlas-us-east-1
S3ModuleNamespace: atlantis
```

### S3 Artifacts Bucket Only

Enable just the shared artifacts bucket:

```
OrgPrefix: ACME
RolePath: /
EnableS3ArtifactsBucket: true
S3BucketNameOrgPrefix: acme
S3ModuleLocation: 63klabs-atlas-us-east-1
S3ModuleNamespace: atlantis
```

This creates: `acme-cf-artifacts-123456789012-us-east-1-an`

## Related Templates

- **[template-storage-s3-artifacts](../storage/template-storage-s3-artifacts-README.md)**: Per-project, prefix-scoped S3 artifacts bucket (alternative to the account-wide bucket)
- **[template-service-role-pipeline](../service-role/template-service-role-pipeline-README.md)**: Per-project service roles that use the managed policies exported by this template
- **[template-pipeline-github](../pipeline/template-pipeline-github-README.md)**: CI/CD pipeline that references the GitHub connection and managed policy exports

## Troubleshooting

### Module Loading Fails

- Verify the `S3ModuleLocation` bucket exists and is accessible from the deploying account
- Check that `S3ModuleNamespace` matches the path structure in the bucket
- Ensure the CloudFormation service role has `s3:GetObject` permission on the module bucket

### GitHub Connection Stays PENDING

- Navigate to AWS Console → Developer Tools → Connections
- Click on the pending connection and complete authorization with your GitHub account
- The connection status output will update on the next stack update

### S3 Bucket Name Already Exists

- S3 bucket names are globally unique — if the name is taken, add or change the `S3BucketNameOrgPrefix`
- The bucket name pattern is: `[S3BucketNameOrgPrefix-]cf-artifacts-{AccountId}-{Region}-an`

### Managed Policy Limit Reached

- AWS accounts have a default limit of 1500 managed policies
- If you hit this limit, request an increase via AWS Support

### Stack Deletion with Retained Resources

- The S3 artifacts bucket uses `DeletionPolicy: Retain` — it will NOT be deleted when the stack is deleted
- You must manually delete the bucket after stack deletion if no longer needed
- This protects pipeline artifacts needed for rollbacks
