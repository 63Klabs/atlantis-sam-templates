# Service Role Templates

IAM service role templates for CloudFormation deployments, API Gateway logging, and GitHub connections.

## Overview

Service role templates create the IAM roles and policies required for CloudFormation to deploy and manage resources on your behalf. These roles implement the principle of least privilege, scoping permissions to specific resource prefixes and paths.

## Templates

### [template-service-role-api-gateway-cloudwatch](./template-service-role-api-gateway-cloudwatch-README.md)

Account-level IAM role for API Gateway to write logs to CloudWatch.

**Use Cases:**
- Enable CloudWatch logging for API Gateway REST APIs
- Centralized logging configuration at the account level
- Required once per AWS account per region

**Key Features:**
- Creates IAM role with API Gateway trust policy
- Attaches AWS managed policy for CloudWatch Logs
- Configures API Gateway account settings
- One-time setup per account/region

**Prerequisites:**
- None (account-level configuration)

---

### [template-service-role-codeconnections-github](./template-service-role-codeconnections-github-README.md)

GitHub connection for CodePipeline source integration.

**Use Cases:**
- Connect CodePipeline to GitHub repositories
- Enable automated deployments from GitHub
- Secure GitHub organization access

**Key Features:**
- Creates CodeConnections connection to GitHub
- Requires manual authorization in AWS Console
- Retained on stack deletion
- Supports GitHub organizations and personal accounts

**Prerequisites:**
- GitHub organization or personal account
- Admin permissions in GitHub organization (for authorization)

**Important:** Manual completion required after deployment to authorize the connection.

---

### [template-service-role-pipeline](./template-service-role-pipeline-README.md)

Prefix-based IAM service role for deploying and managing CI/CD pipelines.

**Use Cases:**
- Deploy CodePipeline infrastructure stacks
- Manage pipeline resources (CodeBuild, EventBridge, S3)
- Prefix-based resource isolation and access control

**Key Features:**
- Prefix-scoped permissions for resource isolation
- Manages CodePipeline, CodeBuild, EventBridge, S3, IAM
- Optional managed policy for users/groups/roles
- Permissions boundary support

**Prerequisites:**
- Defined resource prefix for organization
- Optional: Permissions boundary policy

---

### [template-service-role-storage](./template-service-role-storage-README.md)

Prefix-based IAM service role for deploying and managing storage infrastructure.

**Use Cases:**
- Deploy S3 buckets and DynamoDB tables
- Manage storage access policies
- Prefix-based resource isolation

**Key Features:**
- Prefix-scoped permissions for S3 and DynamoDB
- Manages Lambda functions for S3 event handlers
- Optional managed policy for users/groups/roles
- Permissions boundary support

**Prerequisites:**
- Defined resource prefix for organization
- Optional: Permissions boundary policy

## Common Use Cases

### Account-Level Setup

1. **API Gateway Logging** (`template-service-role-api-gateway-cloudwatch`)
   - Deploy once per account/region
   - Enables CloudWatch logging for all API Gateways
   - No ongoing maintenance required

2. **GitHub Integration** (`template-service-role-codeconnections-github`)
   - Deploy once per GitHub organization
   - Authorize connection in AWS Console
   - Use connection ARN in pipeline templates

### Prefix-Based Resource Management

1. **Pipeline Deployment** (`template-service-role-pipeline`)
   - Deploy once per resource prefix (e.g., "acme", "ws", "prod")
   - Use service role when deploying pipeline stacks
   - Attach managed policy to developer IAM users/groups

2. **Storage Deployment** (`template-service-role-storage`)
   - Deploy once per resource prefix
   - Use service role when deploying storage stacks
   - Attach managed policy to developer IAM users/groups

## Architecture Patterns

### Pattern 1: Multi-Team Organization

```
Organization
├── Team A (prefix: "teama")
│   ├── Service Role: Pipeline Management
│   ├── Service Role: Storage Management
│   └── Resources: teama-*
├── Team B (prefix: "teamb")
│   ├── Service Role: Pipeline Management
│   ├── Service Role: Storage Management
│   └── Resources: teamb-*
└── Shared
    ├── API Gateway CloudWatch Role (account-level)
    └── GitHub Connections (per organization)
```

### Pattern 2: Environment-Based Isolation

```
Organization
├── Development (prefix: "dev")
│   ├── Service Role: Pipeline Management
│   ├── Service Role: Storage Management
│   └── Resources: dev-*
├── Production (prefix: "prod")
│   ├── Service Role: Pipeline Management
│   ├── Service Role: Storage Management
│   └── Resources: prod-*
└── Shared
    └── Account-level roles
```

## Security Best Practices

### Principle of Least Privilege

1. **Prefix-Based Scoping**: Service roles only manage resources matching their prefix
2. **Resource Type Restrictions**: Roles limited to specific AWS services
3. **Path-Based Organization**: Use IAM paths to organize roles and policies
4. **Permissions Boundaries**: Apply boundaries to further restrict role capabilities

### IAM Best Practices

1. **Service Roles**: Use dedicated service roles for CloudFormation
2. **Managed Policies**: Attach managed policies to users/groups for deployment permissions
3. **Role Separation**: Separate roles for different resource types (pipeline vs storage)
4. **Audit Trail**: All actions logged via CloudTrail

### Permissions Boundaries

Permissions boundaries provide an additional layer of security:
- Define maximum permissions a role can have
- Required by some organizations for compliance
- Applied when creating new IAM roles
- Specified via PermissionsBoundaryArn parameter

## Deployment Notes

### Deployment Order

1. **Account-Level Roles** (once per account/region)
   - `template-service-role-api-gateway-cloudwatch`
   - `template-service-role-codeconnections-github` (per GitHub org)

2. **Prefix-Based Roles** (once per prefix)
   - `template-service-role-pipeline`
   - `template-service-role-storage`

### Update Behavior

- **Service Roles**: In-place updates for policy changes
- **Managed Policies**: In-place updates, affects attached users/groups/roles immediately
- **GitHub Connections**: Retained on stack deletion, requires manual deletion

### Manual Steps Required

**GitHub Connection Authorization:**
1. Deploy `template-service-role-codeconnections-github` stack
2. Navigate to AWS Console URL from stack outputs
3. Find connection and click "Update pending connection"
4. Authorize AWS to access GitHub organization
5. Connection status changes from PENDING to AVAILABLE

## Integration with Other Templates

Service role templates enable deployment of:

- **Pipeline Templates**: Use pipeline service role
  - `template-pipeline-github.yml`
  - `template-pipeline.yml`
  - `template-pipeline-build-only.yml`

- **Storage Templates**: Use storage service role
  - `template-storage-s3-oac-for-cloudfront.yml`
  - `template-storage-s3-artifacts.yml`
  - `template-storage-s3-devops.yml`
  - `template-storage-s3-access-logs.yml`
  - `template-storage-cache-data.yml`

- **Network Templates**: Use pipeline or storage service role
  - `template-network-route53-cloudfront-s3-apigw.yml`

## Troubleshooting

### Common Issues

**CloudFormation Access Denied**
- Verify correct service role is specified
- Check service role has permissions for resource type
- Ensure resource names match prefix pattern
- Verify permissions boundary (if used) allows action

**GitHub Connection Pending**
- Connection requires manual authorization in AWS Console
- User must have admin permissions in GitHub organization
- Check ConsoleUrl output for authorization link
- Connection remains PENDING until authorized

**IAM PassRole Errors**
- Verify managed policy is attached to user/group/role
- Check user has iam:PassRole permission for service role
- Ensure service role ARN matches expected pattern

**Permissions Boundary Violations**
- Verify permissions boundary ARN is correct
- Check boundary policy allows required actions
- Ensure service role respects boundary when creating roles

## Cost Considerations

### IAM Costs

- **IAM Roles and Policies**: No charge
- **API Gateway Logging**: CloudWatch Logs storage and data ingestion costs
- **GitHub Connections**: No charge for the connection itself

### Cost Optimization

1. **Reuse Service Roles**: One service role per prefix, not per project
2. **Managed Policies**: Attach to groups rather than individual users
3. **Log Retention**: Configure appropriate retention for CloudWatch Logs

## Additional Resources

- [IAM Roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html)
- [IAM Permissions Boundaries](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html)
- [CloudFormation Service Roles](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-iam-servicerole.html)
- [API Gateway CloudWatch Logging](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-logging.html)
- [CodeConnections for GitHub](https://docs.aws.amazon.com/dtconsole/latest/userguide/connections.html)
