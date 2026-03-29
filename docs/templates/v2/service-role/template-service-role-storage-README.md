# template-service-role-storage.yml

Prefix-based IAM service role for deploying and managing storage infrastructure (S3, DynamoDB).

**Version:** v0.0.1  
**Last Updated:** 2025-08-09  
**Template:** [templates/v2/service-role/template-service-role-storage.yml](../../../../templates/v2/service-role/template-service-role-storage.yml)

## Overview

This template creates a prefix-based IAM service role and managed policy that enables CloudFormation to deploy and manage storage infrastructure including S3 buckets, DynamoDB tables, and related Lambda functions. The service role implements least-privilege permissions scoped to resources matching a specific prefix, enabling multi-team or multi-environment isolation.

### Key Features

- **Prefix-Based Scoping**: All permissions scoped to resources matching the specified prefix
- **CloudFormation Service Role**: Used when deploying storage CloudFormation stacks
- **Managed Policy**: Attachable to IAM users, groups, or roles for deployment permissions
- **Storage Resources**: Manages S3, DynamoDB, Lambda, CloudWatch, and EventBridge
- **Permissions Boundary Support**: Optional permissions boundary for additional security
- **Path-Based Organization**: Configurable IAM paths for role organization
- **Exported Outputs**: Service role ARN and name exported for cross-stack references
- **Least Privilege**: Minimal permissions required for storage management

### Use Cases

- Deploy S3 buckets for artifacts, static hosting, or data storage
- Create DynamoDB tables for application data
- Manage Lambda functions for S3 event handlers
- Prefix-based resource isolation and access control
- Multi-team AWS account with separated storage infrastructure
- Environment-based isolation (dev, test, prod prefixes)

### Prerequisites

- Defined resource prefix for organization (e.g., "acme", "team-a", "prod")
- (Optional) Permissions boundary policy ARN
- (Optional) Existing IAM users, groups, or roles to attach managed policy to

> **Important:** Deploy one service role per prefix. Multiple teams or environments should use different prefixes and separate service role stacks.

## Parameters

### Application Resource Naming

Parameters for naming and organizing the service role.

- [Prefix](#prefix)
- [PrefixUpper](#prefixupper)
- [S3BucketNameOrgPrefix](#s3bucketnameorgprefix)
- [ServiceRolePath](#servicerolepath)
- [RolePath](#rolepath)

#### Prefix

Prefix prepended to all managed resources (lowercase).

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | acme |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,6}[a-z0-9]$` |
| Min Length | 2 |
| Max Length | 8 |
| Constraint Description | 2 to 8 characters. Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. |

This prefix identifies resource ownership and access control. Short, descriptive 2-6 character values work best.

#### PrefixUpper

Prefix for service role name in uppercase.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | ACME |
| Allowed Pattern | `^[A-Z][A-Z0-9-]{0,6}[A-Z0-9]$` |
| Min Length | 2 |
| Max Length | 8 |
| Constraint Description | 2 to 8 characters. UPPER case alphanumeric and dashes. |

Used for service role naming. Must match the Prefix parameter but in uppercase.

#### S3BucketNameOrgPrefix

Optional organization prefix for S3 bucket names.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,18}[a-z0-9]$\|^$` |
| Constraint Description | May be empty or 2 to 20 characters (8 or less recommended). |

By default, buckets include account and region in the name. Use this parameter to specify your own prefix (like an org code) instead. Buckets are named `<Prefix>-<Region>-<AccountId>-<ProjectId>-<ResourceId>` or `<S3OrgPrefix>-<Prefix>-<ProjectId>-<ResourceId>`.

#### ServiceRolePath

Path for the service role itself.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\\/([a-zA-Z0-9-_]+[\\/])+$\|^\\/$` |
| Constraint Description | Must begin and end with a slash. |

Path to organize the service role. For example, `/service-roles/` or `/cloudformation/`.

#### RolePath

Path for application IAM roles and policies.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\\/([a-zA-Z0-9-_]+[\\/])+$\|^\\/$` |
| Constraint Description | Must begin and end with a slash. |

Path used for IAM roles and policies created by storage stacks. Examples: `/ws-storage/` or `/app_role/`

### External Resources

Parameters for external security policies.

- [PermissionsBoundaryArn](#permissionsboundaryarn)

#### PermissionsBoundaryArn

Optional IAM Permissions Boundary policy ARN.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^arn:aws:iam::\\d{12}:policy\\/[\\w+=,.@\\-\\/]*[\\w+=,.@\\-]+$` |
| Constraint Description | Must be empty or a valid IAM Policy ARN |

Permissions Boundary is a policy attached to roles to further restrict permissions. If specified, the service role will enforce this boundary when creating new IAM roles.

### Resources to Attach Managed Policy To

Parameters for attaching the managed policy to existing IAM principals.

- [GroupNames](#groupnames)
- [RoleNames](#rolenames)
- [UserNames](#usernames)

#### GroupNames

Optional IAM group names to attach managed policy to.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | "" (empty) |
| Allowed Pattern | `^[\\w+=,_.@\\-]+$\|^$` |
| Constraint Description | Must be comma delimited list of valid IAM Group names |

Friendly names (not ARNs) of existing IAM groups. For example: `Developers,DevOps`.

#### RoleNames

Optional IAM role names to attach managed policy to.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | "" (empty) |
| Allowed Pattern | `^[\\w+=,_.@\\-]+$\|^$` |
| Constraint Description | Must be comma delimited list of valid IAM Role names |

Friendly names (not ARNs) of existing IAM roles.

#### UserNames

Optional IAM user names to attach managed policy to.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | "" (empty) |
| Allowed Pattern | `^[\\w+=,_.@\\-]+$\|^$` |
| Constraint Description | Must be comma delimited list of valid IAM User names |

Friendly names (not ARNs) of existing IAM users.

## Resources

This template creates the following resources:

- [PrefixBasedCloudFormationStorageMgmtServiceRole](#prefixbasedcloudformationstoragemgmtservicerole) - AWS::IAM::Role
- [PrefixBasedManagedPolicy](#prefixbasedmanagedpolicy) - AWS::IAM::ManagedPolicy

### PrefixBasedCloudFormationStorageMgmtServiceRole

Type: AWS::IAM::Role

CloudFormation service role for deploying and managing storage infrastructure.

**Key Properties:**
- **Role Name**: `${PrefixUpper}-CloudFormation-Service-Role-Storage-Management`
- **Path**: ServiceRolePath parameter
- **Trust Policy**: Allows cloudformation.amazonaws.com to assume the role
- **Permissions Boundary**: Applied if PermissionsBoundaryArn is specified
- **Description**: Service Role to Create and Manage AWS S3, DynamoDB, and application access policies under prefix

**Permissions:**

1. **EventBridge Rules** (`ManageEventRulesByResourcePrefix`)
   - Full management of EventBridge rules matching `${Prefix}-*`
   - Actions: PutTargets, RemoveTargets, PutRule, DeleteRule, DescribeRule, TagResource, UntagResource
   - Scoped to: `arn:aws:events:${Region}:${Account}:rule/${Prefix}-*`
   - Use case: S3 event notifications to Lambda

2. **CloudFormation Stacks** (`ManageCloudFormationStacksByResourcePrefix`)
   - Full stack management for stacks matching `${Prefix}-*`
   - Actions: All Stack operations, ChangeSet operations, GetTemplate, GetTemplateSummary
   - Scoped to: `arn:aws:cloudformation:${Region}:${Account}:stack/${Prefix}-*`

3. **S3 Buckets** (`ManageBucketsByResourcePrefix`)
   - Full S3 management for buckets matching prefix pattern
   - Actions: All S3 actions
   - Scoped to: Buckets with `${S3OrgPrefix}-${Prefix}-*` or `${Prefix}-${Region}-${Account}-*` pattern
   - Use case: Create and manage S3 buckets for storage

4. **CloudWatch Alarms** (`CloudWatchAlarmsLimitedCRUDThisDeploymentOnly`)
   - Limited CloudWatch alarm management
   - Actions: PutMetricAlarm, DeleteAlarm*, TagResource, UntagResource, DescribeAlarms
   - Scoped to: `arn:aws:cloudwatch:${Region}:${Account}:alarm:${Prefix}-*`
   - Use case: Alarms for S3 and DynamoDB metrics

5. **CloudWatch Logs** (`LogGroupsLimitedCRUDThisDeploymentOnly`, `LogGroupsListAll`)
   - Limited log group management for Lambda functions
   - Actions: CreateLogGroup, DeleteLogGroup, PutRetentionPolicy, TagResource, etc.
   - Scoped to: `/aws/lambda/${Prefix}-*`
   - Use case: Log groups for Lambda event handlers

6. **Lambda Functions** (`LambdaCRUDThisDeploymentOnly`)
   - Full Lambda management for functions matching prefix
   - Actions: All lambda actions
   - Scoped to: `arn:aws:lambda:${Region}:${Account}:function:${Prefix}-*`
   - Use case: Lambda functions for S3 event processing

7. **DynamoDB Tables** (`DynamoDbCRUDThisDeploymentOnly`)
   - Full DynamoDB management for tables matching prefix
   - Actions: All dynamodb actions
   - Scoped to: `arn:aws:dynamodb:${Region}:${Account}:table/${Prefix}-*`
   - Use case: Create and manage DynamoDB tables

8. **IAM Worker Roles** (`PassAndDeleteWorkerRolesByResourcePrefix`, `ManageWorkerRolesByResourcePrefix`)
   - Pass and manage worker roles for Lambda and other services
   - Actions: PassRole, CreateRole, DeleteRole, AttachRolePolicy, etc.
   - Scoped to: `arn:aws:iam::${Account}:role${RolePath}${Prefix}-Worker-*`
   - Condition: Enforces permissions boundary if specified

9. **IAM Read-Only** (`IAMReadOnly`, `InspectServiceRole`)
   - Read-only access to IAM roles and policies
   - Actions: Get*, List*
   - Scoped to: All roles and policies (read-only)

### PrefixBasedManagedPolicy

Type: AWS::IAM::ManagedPolicy

Managed policy that grants users/groups/roles permission to deploy storage stacks using the service role.

**Key Properties:**
- **Path**: ServiceRolePath parameter
- **Attached To**: Groups, Roles, and/or Users specified in parameters
- **Description**: Managed Policy to Create and Manage AWS S3, DynamoDB, and application access policies under prefix

**Permissions:**

1. **Pass Service Role** (`AllowUserToPassSpecificCloudFormationServiceRole`)
   - Allows passing the service role to CloudFormation
   - Actions: iam:GetRole, iam:PassRole
   - Scoped to: The service role ARN
   - Condition: Only when passed to cloudformation.amazonaws.com

## Outputs

### PrefixBasedCloudFormationStorageMgmtServiceRoleArn

ARN of the CloudFormation service role.

**Value:** ARN of PrefixBasedCloudFormationStorageMgmtServiceRole

**Export Name:** `${PrefixUpper}-CloudFormation-Storage-Mgmt-Service-Role-Arn`

**Usage:** Use this ARN when deploying storage CloudFormation stacks.

**Example Value:** `arn:aws:iam::123456789012:role/ACME-CloudFormation-Service-Role-Storage-Management`

### PrefixBasedCloudFormationStorageMgmtServiceRoleName

Name of the CloudFormation service role.

**Value:** Name of PrefixBasedCloudFormationStorageMgmtServiceRole

**Export Name:** `${PrefixUpper}-CloudFormation-Storage-Mgmt-Service-Role-Name`

**Usage:** Reference the role name in other templates or scripts.

### PrefixBasedManagedPolicyArn

ARN of the managed policy.

**Value:** ARN of PrefixBasedManagedPolicy

**Export Name:** `${PrefixUpper}-CloudFormation-Storage-Mgmt-Service-ManagedPolicy-Arn`

**Usage:** Attach this policy to additional users, groups, or roles after deployment.

### PrefixBasedManagedPolicyName

Name of the managed policy.

**Value:** Name of PrefixBasedManagedPolicy

**Export Name:** `${PrefixUpper}-CloudFormation-Storage-Mgmt-Service-ManagedPolicy-Name`

**Usage:** Reference the policy name in other templates or scripts.

## Conditions

The template uses several conditions to control resource configuration:

- **UseS3BucketNameOrgPrefix**: True when S3BucketNameOrgPrefix is not empty
- **HasPermissionsBoundaryArn**: True when PermissionsBoundaryArn is not empty
- **HasGroupNames**: True when GroupNames is not empty
- **HasRoleNames**: True when RoleNames is not empty
- **HasUserNames**: True when UserNames is not empty

## Examples

### Basic Deployment

```bash
# Deploy service role for "acme" prefix
aws cloudformation create-stack \
  --stack-name acme-storage-service-role \
  --template-body file://template-service-role-storage.yml \
  --parameters \
    ParameterKey=Prefix,ParameterValue=acme \
    ParameterKey=PrefixUpper,ParameterValue=ACME \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### With Managed Policy Attached to Group

```bash
# Deploy and attach to Developers group
aws cloudformation create-stack \
  --stack-name acme-storage-service-role \
  --template-body file://template-service-role-storage.yml \
  --parameters \
    ParameterKey=Prefix,ParameterValue=acme \
    ParameterKey=PrefixUpper,ParameterValue=ACME \
    ParameterKey=GroupNames,ParameterValue=Developers \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### With S3 Organization Prefix

```bash
# Deploy with custom S3 prefix
aws cloudformation create-stack \
  --stack-name acme-storage-service-role \
  --template-body file://template-service-role-storage.yml \
  --parameters \
    ParameterKey=Prefix,ParameterValue=acme \
    ParameterKey=PrefixUpper,ParameterValue=ACME \
    ParameterKey=S3BucketNameOrgPrefix,ParameterValue=myorg \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### Using Service Role to Deploy Storage

```bash
# Deploy S3 bucket stack using the service role
aws cloudformation create-stack \
  --stack-name acme-artifacts-bucket \
  --template-body file://template-storage-s3-artifacts.yml \
  --role-arn arn:aws:iam::123456789012:role/ACME-CloudFormation-Service-Role-Storage-Management \
  --parameters \
    ParameterKey=Prefix,ParameterValue=acme \
    ParameterKey=ProjectId,ParameterValue=artifacts \
    ... \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

## Troubleshooting

### Access Denied When Deploying Storage Stack

**Symptom:** CloudFormation fails with "User is not authorized to perform: cloudformation:CreateStack" or similar.

**Possible Causes:**
- User doesn't have managed policy attached
- Service role ARN incorrect
- Resource names don't match prefix pattern

**Solutions:**
1. Verify managed policy is attached to user's group or role
2. Check service role ARN is correct in deployment command
3. Ensure all resource names in template start with the prefix
4. Verify user has `iam:PassRole` permission for the service role

### S3 Bucket Creation Fails

**Symptom:** CloudFormation fails when creating S3 bucket.

**Possible Causes:**
- Bucket name doesn't match prefix pattern
- S3BucketNameOrgPrefix parameter incorrect
- Bucket name already exists globally
- Bucket name too long

**Solutions:**
1. Verify bucket name matches `${S3OrgPrefix}-${Prefix}-*` or `${Prefix}-${Region}-${Account}-*` pattern
2. Check S3BucketNameOrgPrefix parameter matches template
3. Ensure bucket name is globally unique
4. Shorten bucket name if exceeding 63 characters

### Lambda Function Creation Fails

**Symptom:** CloudFormation fails when creating Lambda function for S3 events.

**Possible Causes:**
- Function name doesn't match prefix pattern
- Worker role creation failed
- Permissions boundary violation

**Solutions:**
1. Verify function name starts with `${Prefix}-`
2. Check worker role was created successfully
3. Ensure permissions boundary allows Lambda function creation
4. Review CloudFormation error message for specific issue

### DynamoDB Table Creation Fails

**Symptom:** CloudFormation fails when creating DynamoDB table.

**Possible Causes:**
- Table name doesn't match prefix pattern
- Table already exists
- Insufficient permissions

**Solutions:**
1. Verify table name starts with `${Prefix}-`
2. Check if table already exists in account/region
3. Ensure service role has DynamoDB permissions
4. Review CloudFormation error message

### Cannot Pass Service Role

**Symptom:** User cannot deploy stack with error "User is not authorized to perform: iam:PassRole".

**Possible Causes:**
- Managed policy not attached to user
- User's IAM policy doesn't allow PassRole
- Service role ARN incorrect

**Solutions:**
1. Attach managed policy to user's group or role
2. Verify user has `iam:PassRole` permission
3. Check service role ARN is correct
4. Ensure PassRole condition allows passing to cloudformation.amazonaws.com

## Related Templates

This service role is used to deploy:

- **Storage Templates**:
  - [template-storage-s3-oac-for-cloudfront.yml](../storage/template-storage-s3-oac-for-cloudfront-README.md)
  - [template-storage-s3-artifacts.yml](../storage/template-storage-s3-artifacts-README.md)
  - [template-storage-s3-devops.yml](../storage/template-storage-s3-devops-README.md)
  - [template-storage-s3-access-logs.yml](../storage/template-storage-s3-access-logs-README.md)
  - [template-storage-cache-data.yml](../storage/template-storage-cache-data-README.md)

## Security Considerations

1. **Least Privilege**: All permissions scoped to prefix-specific resources
2. **Prefix Isolation**: Different prefixes cannot access each other's resources
3. **Permissions Boundaries**: Support for organizational security policies
4. **Path-Based Organization**: IAM paths for additional access control
5. **Conditional Permissions**: Permissions boundary enforced when creating roles
6. **Audit Trail**: All actions logged via CloudTrail
7. **Managed Policy**: Separate policy for user access control
8. **S3 Bucket Policies**: Service role can create bucket policies for access control

## Best Practices

1. **One Service Role Per Prefix**: Deploy separate service roles for each team or environment
2. **Use Groups**: Attach managed policy to groups rather than individual users
3. **Permissions Boundaries**: Apply boundaries in regulated environments
4. **Descriptive Prefixes**: Use clear, short prefixes (2-6 characters)
5. **S3 Organization Prefix**: Use S3BucketNameOrgPrefix for shorter bucket names
6. **Path Organization**: Use IAM paths to organize roles by application or team
7. **Regular Review**: Periodically review service role permissions
8. **Export Usage**: Use exported outputs for cross-stack references

## Cost Considerations

**IAM Costs:**
- IAM roles and policies: No charge
- No ongoing costs for service roles

**Storage Costs:**
- S3: Storage, requests, and data transfer charges
- DynamoDB: Read/write capacity units or on-demand pricing
- Lambda: Invocations and duration charges (for event handlers)
- CloudWatch: Log storage and metrics

**Cost Optimization Tips:**
1. Use S3 lifecycle policies to transition data to cheaper storage classes
2. Enable S3 Intelligent-Tiering for automatic cost optimization
3. Use DynamoDB on-demand pricing for unpredictable workloads
4. Set appropriate CloudWatch log retention periods
5. Monitor and optimize Lambda function execution time

## Additional Resources

- [CloudFormation Service Roles](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-iam-servicerole.html)
- [S3 Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [IAM Permissions Boundaries](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html)
- [Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [GitHub Repository](https://github.com/63Klabs/atlantis-sam-templates/)
