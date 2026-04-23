# Account Management Stack Deployment

This guide covers deploying and updating the two account-level CloudFormation stacks that establish shared infrastructure for Atlantis-managed projects. These stacks are deployed once per account (or once per prefix/region) and provide the IAM roles, policies, connections, and configurations consumed by individual project pipelines.

All templates and modules are sourced from S3. You do not need a local clone of the template repository.

## Prerequisites

- AWS CLI v2 installed and configured with appropriate credentials
- Access to the S3 bucket containing Atlantis templates (`s3://63klabs/atlantis/templates/v2/`)
- IAM permissions to create CloudFormation stacks, IAM roles, and IAM policies
- For the project pipeline stack: permissions to create CodeConnections and API Gateway Account resources (if using those features)

## S3 Template and Module Locations

All references below use the following S3 base path:

```
s3://63klabs/atlantis/templates/v2/
```

Templates:

```
s3://63klabs/atlantis/templates/v2/account/template-account-management-roles.yml
s3://63klabs/atlantis/templates/v2/account/template-account-project-pipeline.yml
```

Modules referenced by the management roles template:

```
s3://63klabs/atlantis/templates/v2/modules/management-roles/pipeline-mgmt-role.yml
s3://63klabs/atlantis/templates/v2/modules/management-roles/storage-mgmt-role.yml
s3://63klabs/atlantis/templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml
s3://63klabs/atlantis/templates/v2/modules/management-roles/network-route53-mgmt-policy.yml
s3://63klabs/atlantis/templates/v2/modules/management-roles/network-cloudfront-mgmt-role.yml
s3://63klabs/atlantis/templates/v2/modules/management-roles/network-full-mgmt-role.yml
```

Modules referenced by the project pipeline template:

```
s3://63klabs/atlantis/templates/v2/modules/project-pipeline-policies/codebuild-crud.yml
s3://63klabs/atlantis/templates/v2/modules/project-pipeline-policies/cognito-crud.yml
s3://63klabs/atlantis/templates/v2/modules/actions/codeconnections-github.yml
s3://63klabs/atlantis/templates/v2/modules/actions/apigw-cloudwatch-role.yml
```

## Using JSON Parameter and Tag Files

Rather than passing parameters inline, store your configuration in JSON files within your management repository. This keeps CLI commands short, makes configuration reviewable in version control, and allows reuse across create and update operations.

### Parameter File Format

Create a file like `params-management-roles.json`:

```json
[
  { "ParameterKey": "Prefix", "ParameterValue": "acme" },
  { "ParameterKey": "PrefixUpper", "ParameterValue": "ACME" },
  { "ParameterKey": "S3BucketNameOrgPrefix", "ParameterValue": "" },
  { "ParameterKey": "ServiceRolePath", "ParameterValue": "/" },
  { "ParameterKey": "RolePath", "ParameterValue": "/" },
  { "ParameterKey": "PermissionsBoundaryArn", "ParameterValue": "" },
  { "ParameterKey": "GroupNames", "ParameterValue": "" },
  { "ParameterKey": "RoleNames", "ParameterValue": "" },
  { "ParameterKey": "UserNames", "ParameterValue": "" },
  { "ParameterKey": "PipelineMgmtRoleModuleUrl", "ParameterValue": "s3://63klabs/atlantis/templates/v2/modules/management-roles/pipeline-mgmt-role.yml" },
  { "ParameterKey": "StorageMgmtRoleModuleUrl", "ParameterValue": "s3://63klabs/atlantis/templates/v2/modules/management-roles/storage-mgmt-role.yml" },
  { "ParameterKey": "NetworkCloudFrontMgmtPolicyModuleUrl", "ParameterValue": "s3://63klabs/atlantis/templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml" },
  { "ParameterKey": "NetworkRoute53MgmtPolicyModuleUrl", "ParameterValue": "s3://63klabs/atlantis/templates/v2/modules/management-roles/network-route53-mgmt-policy.yml" },
  { "ParameterKey": "NetworkCloudFrontMgmtRoleModuleUrl", "ParameterValue": "s3://63klabs/atlantis/templates/v2/modules/management-roles/network-cloudfront-mgmt-role.yml" },
  { "ParameterKey": "NetworkFullMgmtRoleModuleUrl", "ParameterValue": "s3://63klabs/atlantis/templates/v2/modules/management-roles/network-full-mgmt-role.yml" }
]
```

### Tag File Format

Create a file like `tags-account.json`:

```json
[
  { "Key": "atlantis:ManagedBy", "Value": "CloudFormation" },
  { "Key": "atlantis:Environment", "Value": "account" },
  { "Key": "atlantis:Owner", "Value": "platform-team" }
]
```

### Suggested Management Repo Structure

```
my-account-management/
├── acme/
│   ├── params-management-roles.json
│   ├── params-project-pipeline.json
│   └── tags-account.json
├── ws/
│   ├── params-management-roles.json
│   └── tags-account.json
└── README.md
```

Each directory corresponds to a prefix (or org) and contains the parameter and tag files for that deployment.

---

## Stack 1: Management Roles

This stack creates prefix-scoped IAM service roles and managed policies for Pipeline, Storage, and Network management. Deploy one stack per prefix per account.

### Stack Name Convention

```
<PrefixUpper>-Atlantis-Management-Roles
```

Example: `ACME-Atlantis-Management-Roles`

### Create Stack

```bash
aws cloudformation create-stack \
  --stack-name ACME-Atlantis-Management-Roles \
  --template-url https://s3.amazonaws.com/63klabs/atlantis/templates/v2/account/template-account-management-roles.yml \
  --parameters file://acme/params-management-roles.json \
  --tags file://acme/tags-account.json \
  --capabilities CAPABILITY_NAMED_IAM
```

### Update Stack

```bash
aws cloudformation update-stack \
  --stack-name ACME-Atlantis-Management-Roles \
  --template-url https://s3.amazonaws.com/63klabs/atlantis/templates/v2/account/template-account-management-roles.yml \
  --parameters file://acme/params-management-roles.json \
  --tags file://acme/tags-account.json \
  --capabilities CAPABILITY_NAMED_IAM
```

To update only specific parameters while keeping others unchanged, use `UsePreviousValue`:

```json
[
  { "ParameterKey": "Prefix", "UsePreviousValue": true },
  { "ParameterKey": "PrefixUpper", "UsePreviousValue": true },
  { "ParameterKey": "S3BucketNameOrgPrefix", "UsePreviousValue": true },
  { "ParameterKey": "ServiceRolePath", "UsePreviousValue": true },
  { "ParameterKey": "RolePath", "UsePreviousValue": true },
  { "ParameterKey": "PermissionsBoundaryArn", "ParameterValue": "arn:aws:iam::123456789012:policy/MyBoundary" },
  { "ParameterKey": "GroupNames", "UsePreviousValue": true },
  { "ParameterKey": "RoleNames", "UsePreviousValue": true },
  { "ParameterKey": "UserNames", "UsePreviousValue": true },
  { "ParameterKey": "PipelineMgmtRoleModuleUrl", "UsePreviousValue": true },
  { "ParameterKey": "StorageMgmtRoleModuleUrl", "UsePreviousValue": true },
  { "ParameterKey": "NetworkCloudFrontMgmtPolicyModuleUrl", "UsePreviousValue": true },
  { "ParameterKey": "NetworkRoute53MgmtPolicyModuleUrl", "UsePreviousValue": true },
  { "ParameterKey": "NetworkCloudFrontMgmtRoleModuleUrl", "UsePreviousValue": true },
  { "ParameterKey": "NetworkFullMgmtRoleModuleUrl", "UsePreviousValue": true }
]
```

### What Gets Created

| Resource | Description |
|----------|-------------|
| Pipeline Management Service Role | CloudFormation service role for deploying pipeline stacks |
| Pipeline Management Managed Policy | PassRole policy for the pipeline service role |
| Storage Management Service Role | CloudFormation service role for deploying storage stacks |
| Storage Management Managed Policy | PassRole policy for the storage service role |
| Network CloudFront Management Policy | Managed policy for CloudFront, OAC, cache policies, API GW domains |
| Network Route53 Management Policy | Managed policy for Route53 DNS record management |
| Network CloudFront Management Role | Developer service role (CloudFront only, no Route53) |
| Network CloudFront Management Managed Policy | PassRole policy for the CloudFront-only role |
| Network Full Management Role | Full access service role (CloudFront + Route53) |
| Network Full Management Managed Policy | PassRole policy for the full network role |

### Key Outputs

| Output | Export Name Pattern |
|--------|-------------------|
| Pipeline Service Role ARN | `<PREFIX>-CloudFormation-Pipeline-Mgmt-Service-Role-Arn` |
| Storage Service Role ARN | `<PREFIX>-CloudFormation-Storage-Mgmt-Service-Role-Arn` |
| Network CloudFront Role ARN | `<PREFIX>-CloudFormation-Network-CloudFront-Mgmt-Service-Role-Arn` |
| Network Full Role ARN | `<PREFIX>-CloudFormation-Network-Full-Mgmt-Service-Role-Arn` |

---

## Stack 2: Project Pipeline Resources

This stack creates account-wide, ABAC-scoped managed policies and shared resources (GitHub connections, API Gateway logging) for project pipelines. Deploy one stack per account (not per prefix).

### Stack Name Convention

```
<OrgPrefix>-Atlantis-Project-Pipeline
```

Example: `ACME-Atlantis-Project-Pipeline`

### Parameter File

Create `params-project-pipeline.json`:

```json
[
  { "ParameterKey": "OrgPrefix", "ParameterValue": "ACME" },
  { "ParameterKey": "RolePath", "ParameterValue": "/" },
  { "ParameterKey": "CodeBuildCrudModuleUrl", "ParameterValue": "s3://63klabs/atlantis/templates/v2/modules/project-pipeline-policies/codebuild-crud.yml" },
  { "ParameterKey": "CognitoCrudModuleUrl", "ParameterValue": "s3://63klabs/atlantis/templates/v2/modules/project-pipeline-policies/cognito-crud.yml" },
  { "ParameterKey": "GitHubOrg", "ParameterValue": "my-github-org" },
  { "ParameterKey": "EnableApiGwCloudWatchLogs", "ParameterValue": "true" },
  { "ParameterKey": "CodeConnectionsGitHubModuleUrl", "ParameterValue": "s3://63klabs/atlantis/templates/v2/modules/actions/codeconnections-github.yml" },
  { "ParameterKey": "ApiGwCloudWatchModuleUrl", "ParameterValue": "s3://63klabs/atlantis/templates/v2/modules/actions/apigw-cloudwatch-role.yml" }
]
```

To skip the GitHub connection, set `GitHubOrg` to `""`. To skip API Gateway logging, set `EnableApiGwCloudWatchLogs` to `"false"`. The module URLs are still required even when the features are disabled (CloudFormation fetches the snippets but the resources inside are conditionally created).

### Create Stack

```bash
aws cloudformation create-stack \
  --stack-name ACME-Atlantis-Project-Pipeline \
  --template-url https://s3.amazonaws.com/63klabs/atlantis/templates/v2/account/template-account-project-pipeline.yml \
  --parameters file://acme/params-project-pipeline.json \
  --tags file://acme/tags-account.json \
  --capabilities CAPABILITY_NAMED_IAM
```

### Update Stack

```bash
aws cloudformation update-stack \
  --stack-name ACME-Atlantis-Project-Pipeline \
  --template-url https://s3.amazonaws.com/63klabs/atlantis/templates/v2/account/template-account-project-pipeline.yml \
  --parameters file://acme/params-project-pipeline.json \
  --tags file://acme/tags-account.json \
  --capabilities CAPABILITY_NAMED_IAM
```

### What Gets Created

| Resource | Condition | Description |
|----------|-----------|-------------|
| CodeBuild CRUD Managed Policy | Always | ABAC-scoped policy for CodeBuild and /aws/codebuild/ logs |
| Cognito CRUD Managed Policy | Always | ABAC-scoped policy for Cognito User Pool management |
| GitHub Connection | GitHubOrg is not empty | CodeConnections connection to GitHub (requires manual completion) |
| API Gateway CloudWatch Role | EnableApiGwCloudWatchLogs is true | IAM role + API Gateway Account config for CloudWatch logging |

### Post-Deployment: GitHub Connection

If you provided a `GitHubOrg`, the connection will be in a **PENDING** state. To activate it:

1. Open the CodeConnections console URL from the stack outputs
2. Find your connection and click "Update pending connection"
3. Authorize AWS to access your GitHub organization
4. The user completing this step must have admin permissions in the GitHub organization

### Key Outputs

| Output | Export Name Pattern | Condition |
|--------|-------------------|-----------|
| CodeBuild CRUD Policy ARN | `<ORG>-ProjectPipeline-CodeBuildCrud-Arn` | Always |
| Cognito CRUD Policy ARN | `<ORG>-ProjectPipeline-CognitoCrud-Arn` | Always |
| GitHub Connection ARN | `<ORG>-GitHub-Connection-Arn` | GitHubOrg provided |
| API GW CloudWatch Role ARN | `<ORG>-ApiGateway-CloudWatch-Role-Arn` | Logging enabled |

---

## Monitoring Stack Operations

### Wait for Completion

```bash
aws cloudformation wait stack-create-complete \
  --stack-name ACME-Atlantis-Management-Roles
```

```bash
aws cloudformation wait stack-update-complete \
  --stack-name ACME-Atlantis-Management-Roles
```

### Check Stack Status

```bash
aws cloudformation describe-stacks \
  --stack-name ACME-Atlantis-Management-Roles \
  --query "Stacks[0].StackStatus" \
  --output text
```

### View Stack Outputs

```bash
aws cloudformation describe-stacks \
  --stack-name ACME-Atlantis-Management-Roles \
  --query "Stacks[0].Outputs" \
  --output table
```

### View Stack Events (for troubleshooting)

```bash
aws cloudformation describe-stack-events \
  --stack-name ACME-Atlantis-Management-Roles \
  --query "StackEvents[?ResourceStatus=='CREATE_FAILED' || ResourceStatus=='UPDATE_FAILED']" \
  --output table
```

---

## Deployment Order

When setting up a new account:

1. Deploy **Management Roles** stack first (one per prefix)
2. Deploy **Project Pipeline** stack second (one per account)
3. Deploy individual project pipeline and storage stacks using the roles created above

When updating, either stack can be updated independently. The management roles stack does not depend on the project pipeline stack or vice versa.

---

## Deleting Stacks

Before deleting, verify no other stacks reference the exported values:

```bash
aws cloudformation list-imports \
  --export-name ACME-CloudFormation-Pipeline-Mgmt-Service-Role-Arn
```

If no imports are returned, the stack can be safely deleted:

```bash
aws cloudformation delete-stack \
  --stack-name ACME-Atlantis-Management-Roles
```

Note: The GitHub connection resource has `DeletionPolicy: Retain` and will not be deleted when the project pipeline stack is deleted. You must manually delete it from the CodeConnections console if needed.
