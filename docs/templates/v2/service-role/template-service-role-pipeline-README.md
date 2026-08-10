# template-service-role-pipeline.yml

Prefix-based IAM service role for deploying and managing CI/CD pipeline infrastructure.

**Version:** v0.0.19  
**Last Updated:** 2026-08-10  
**Template:** [templates/v2/service-role/template-service-role-pipeline.yml](../../../../templates/v2/service-role/template-service-role-pipeline.yml)

> **NOTE:** This template is deprecated in favor of deploying prefix-based infrastructure during account administration set-up. Account Admins, see: [Atlantis DevOps Platform Administration Guide](https://github.com/63Klabs/atlantis-platform-admin)

## Overview

This template creates a prefix-based IAM service role and managed policy that enables CloudFormation to deploy and manage CodePipeline infrastructure. The service role implements least-privilege permissions scoped to resources matching a specific prefix, enabling multi-team or multi-environment isolation.

### Key Features

- **Prefix-Based Scoping**: All permissions scoped to resources matching the specified prefix
- **CloudFormation Service Role**: Used when deploying pipeline CloudFormation stacks
- **Managed Policy**: Attachable to IAM users, groups, or roles for deployment permissions
- **Permissions Boundary Support**: Optional permissions boundary for additional security
- **Path-Based Organization**: Configurable IAM paths for role organization
- **Exported Outputs**: Service role ARN and name exported for cross-stack references
- **Least Privilege**: Minimal permissions required for pipeline management

### Use Cases

- Deploy CodePipeline infrastructure stacks for specific teams or projects
- Manage pipeline resources (CodeBuild, EventBridge, S3, IAM)
- Prefix-based resource isolation and access control
- Multi-team AWS account with separated CI/CD infrastructure
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
- [OrgPrefix](#orgprefix)
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

This prefix identifies resource ownership and access control. For example, resources named `ws-*` could belong to the web service team. Short, descriptive 2-6 character values work best.

#### PrefixUpper

Prefix for service role name in uppercase.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | ACME |
| Allowed Pattern | `^[A-Z][A-Z0-9-]{0,6}[A-Z0-9]$` |
| Min Length | 2 |
| Max Length | 8 |
| Constraint Description | 2 to 8 characters. UPPER case alphanumeric and dashes. Must start with a letter and end with a letter or number. |

Used for service role naming. Must match the Prefix parameter but in uppercase.

#### OrgPrefix

Organization-level prefix (UPPER CASE) used to resolve the account-wide S3 artifacts bucket export.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[A-Z][A-Z0-9-]{0,18}[A-Z0-9]$\|^$` |
| Max Length | 20 |
| Constraint Description | May be empty, or 2 to 20 characters. UPPER case alphanumeric and dashes. Must start with a letter and end with a letter or number. |

This prefix locates the account-wide export `${OrgPrefix}-S3-Artifacts-Bucket-Name` produced by `account-wide-infrastructure.yml`, so you do not have to look up and paste the artifacts bucket name. It is **distinct from `PrefixUpper`** (the team/namespace prefix) and is only needed when `S3ArtifactsBucket` is left empty and the bucket name is imported from the account-wide stack. Leave it empty if you supply `S3ArtifactsBucket` directly.

> **Note:** No `MinLength` is enforced so the empty default is valid. To use the export path, deploy `account-wide-infrastructure.yml` first with `EnableS3ArtifactsBucket = "true"` and a matching `OrgPrefix`. If `OrgPrefix` is empty while the import path is taken, the export name resolves to `-S3-Artifacts-Bucket-Name` and deployment fails with CloudFormation's native "No export named" error.

#### S3BucketNameOrgPrefix

Optional organization prefix for S3 bucket names.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{0,18}[a-z0-9]$\|^$` |
| Constraint Description | May be empty or 2 to 20 characters (8 or less recommended). |

By default, buckets include account and region in the name. Use this parameter to specify your own prefix (like an org code) instead. Buckets are named `<Prefix>-<Region>-<AccountId>-<ProjectId>-<StageId>-<ResourceId>` or `<S3OrgPrefix>-<Prefix>-<ProjectId>-<StageId>-<ResourceId>`.

#### ServiceRolePath

Path for the service role itself.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\\/([a-zA-Z0-9-_]+[\\/])+$\|^\\/$` |
| Constraint Description | Must begin and end with a slash. |

Path to organize the service role. For example, `/service-roles/` or `/cloudformation/`. This does not affect application resource paths.

#### RolePath

Path for application IAM roles and policies.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | / |
| Allowed Pattern | `^\\/([a-zA-Z0-9-_]+[\\/])+$\|^\\/$` |
| Constraint Description | Must begin and end with a slash. |

Path used for IAM roles and policies created by pipeline stacks. Separate applications from users or create separate paths per prefix. Specific paths may be required by permissions boundaries. Examples: `/ws-hello-world-test/` or `/app_role/`

### External Resources

Parameters for external security policies and shared resources.

- [PermissionsBoundaryArn](#permissionsboundaryarn)
- [S3ArtifactsBucket](#s3artifactsbucket)

#### PermissionsBoundaryArn

Optional IAM Permissions Boundary policy ARN.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^arn:aws:iam::\\d{12}:policy\\/[\\w+=,.@\\-\\/]*[\\w+=,.@\\-]+$` |
| Constraint Description | Must be empty or a valid IAM Policy ARN |

Permissions Boundary is a policy attached to roles to further restrict permissions. Your organization may or may not require boundaries. If specified, the service role will enforce this boundary when creating new IAM roles.

#### S3ArtifactsBucket

**DEPRECATED.** Name of the existing shared S3 artifacts bucket used by managed stacks.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$\|^$` |
| Max Length | 63 |
| Constraint Description | Must be empty or a valid S3 bucket name between 3 and 63 characters containing only lowercase letters, numbers, and hyphens. |

The artifacts bucket name is now derived automatically from the account-wide export `${OrgPrefix}-S3-Artifacts-Bucket-Name`. Supplying this parameter (a non-empty value) **overrides** the export lookup and is retained only for backward compatibility. The service role is granted `s3:GetObject` and `s3:GetObjectVersion` on keys prefixed with `${Prefix}-*` within the resolved bucket.

> **Note:** This parameter is defined so the standalone template matches its underlying management-role module, which references `${S3ArtifactsBucket}`. Earlier standalone versions did not declare it; it is now added as an optional, deprecated override.
>
> **Encouraged usage:** Leave this empty and set `OrgPrefix` so the bucket name is imported from `account-wide-infrastructure.yml`.

##### Export-Based Fallback Behavior

When `S3ArtifactsBucket` is empty, the management-role module resolves the artifacts bucket via `Fn::ImportValue` of the account-wide export `${OrgPrefix}-S3-Artifacts-Bucket-Name`. Because CloudFormation evaluates only the selected branch:

- **`S3ArtifactsBucket` non-empty (override):** The role is scoped to the supplied bucket and **no** cross-stack dependency on the account-wide export is created.
- **`S3ArtifactsBucket` empty (import):** The role is scoped to the imported bucket, and `Fn::ImportValue` creates a **hard cross-stack dependency** that prevents deletion or modification of the export while this stack references it.
- **`S3ArtifactsBucket` empty and export missing** (including an empty `OrgPrefix`): Deployment fails with CloudFormation's native "No export named `${OrgPrefix}-S3-Artifacts-Bucket-Name` found" error. No custom guard masks this.

> **Reminder:** This standalone template is deprecated in favor of prefix-based infrastructure deployed at the account level. See the deprecation note at the top of this document.

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

Friendly names (not ARNs) of existing IAM groups. For example: `Developers,DevOps`. Members of these groups will be able to deploy pipeline stacks using this service role.

#### RoleNames

Optional IAM role names to attach managed policy to.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | "" (empty) |
| Allowed Pattern | `^[\\w+=,_.@\\-]+$\|^$` |
| Constraint Description | Must be comma delimited list of valid IAM Role names |

Friendly names (not ARNs) of existing IAM roles. For example: `DeploymentRole,CICDRole`.

#### UserNames

Optional IAM user names to attach managed policy to.

| Attribute | Setting |
|-----------|---------|
| Type | CommaDelimitedList |
| Default | "" (empty) |
| Allowed Pattern | `^[\\w+=,_.@\\-]+$\|^$` |
| Constraint Description | Must be comma delimited list of valid IAM User names |

Friendly names (not ARNs) of existing IAM users. For example: `john.doe,jane.smith`.

### Module Source

Parameters for configuring where CloudFormation module snippets are loaded from. By default, modules are loaded from a regional S3 bucket based on the deployment region. You can override this with a custom bucket name and/or namespace.

- [S3ModuleLocation](#s3modulelocation)
- [S3ModuleNamespace](#s3modulenamespace)

#### S3ModuleLocation

S3 bucket name override for module snippets. Leave empty to use the default regional bucket from the RegionalModuleBuckets mapping.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | "" (empty) |
| Allowed Pattern | `^$\|^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$` |
| Constraint Description | Must be empty or a valid S3 bucket name between 3 and 63 characters containing only lowercase letters, numbers, and hyphens. |

When left empty (default), the template resolves the module bucket automatically using the `RegionalModuleBuckets` mapping based on the deployment region. If specified, modules are loaded from `s3://<S3ModuleLocation>/<S3ModuleNamespace>/templates/v2/modules/*`.

> **Tip:** Only specify this parameter if you are hosting module snippets in your own S3 bucket. For standard deployments in supported regions (us-east-1, us-east-2, us-west-1, us-west-2), leave this empty.

#### S3ModuleNamespace

Namespace prefix within the S3 module bucket. This is the path prefix where modules are stored.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | atlantis |
| Allowed Pattern | `^[a-z0-9][a-z0-9\-]*(\/[a-z0-9][a-z0-9\-]*)*$` |
| Min Length | 1 |
| Max Length | 128 |
| Constraint Description | Must be 1 to 128 characters containing only lowercase alphanumeric characters, hyphens, and forward slashes. Must not start or end with a slash. Each segment between slashes must start with a lowercase alphanumeric character. |

Modules are loaded from `s3://<BucketName>/<S3ModuleNamespace>/templates/v2/modules/*`. The default value `atlantis` points to the standard module location.

## Mappings

### RegionalModuleBuckets

Maps AWS regions to their corresponding S3 bucket names for module storage. This mapping is used when `S3ModuleLocation` is left empty (default behavior).

| Region | Bucket Name |
|--------|-------------|
| us-east-1 | 63klabs-atlas-us-east-1 |
| us-east-2 | 63klabs-zenith-us-east-2 |
| us-west-1 | 63klabs-fabric-us-west-1 |
| us-west-2 | 63klabs-orbit-us-west-2 |

> **Important:** If you deploy this template in a region not listed above without providing an `S3ModuleLocation` override, the stack will fail with a mapping lookup error. Supported regions for default module resolution are us-east-1, us-east-2, us-west-1, and us-west-2.

## Resources

This template creates the following resources:

- [PrefixBasedCloudFormationPipelineMgmtServiceRole](#prefixbasedcloudformationpipelinemgmtservicerole) - AWS::IAM::Role
- [PrefixBasedManagedPolicy](#prefixbasedmanagedpolicy) - AWS::IAM::ManagedPolicy

### PrefixBasedCloudFormationPipelineMgmtServiceRole

Type: AWS::IAM::Role

CloudFormation service role for deploying and managing pipeline infrastructure.

**Key Properties:**
- **Role Name**: `${PrefixUpper}-CloudFormation-Service-Role-Pipeline-Management`
- **Path**: ServiceRolePath parameter
- **Trust Policy**: Allows cloudformation.amazonaws.com to assume the role
- **Permissions Boundary**: Applied if PermissionsBoundaryArn is specified
- **Description**: Service Role to Create and Manage AWS CodePipeline for application projects under prefix

**Permissions:**

1. **EventBridge Rules** (`ManageEventRulesByResourcePrefix`)
   - Full management of EventBridge rules matching `${Prefix}-*`
   - Actions: PutTargets, RemoveTargets, PutRule, DeleteRule, DescribeRule, TagResource, UntagResource
   - Scoped to: `arn:aws:events:${Region}:${Account}:rule/${Prefix}-*`

2. **CloudFormation Stacks** (`ManageCloudFormationStacksByResourcePrefix`)
   - Full stack management for stacks matching `${Prefix}-*`
   - Actions: All Stack operations, ChangeSet operations, GetTemplate, GetTemplateSummary
   - Scoped to: `arn:aws:cloudformation:${Region}:${Account}:stack/${Prefix}-*`

3. **S3 Buckets** (`ManageBucketsByResourcePrefix`)
   - Full S3 management for buckets matching prefix pattern
   - Actions: All S3 actions
   - Scoped to: Buckets with `${S3OrgPrefix}-${Prefix}-*` or `${Prefix}-${Region}-${Account}-*` pattern

4. **CloudWatch Logs** (`ManageLogsByResourcePrefix`)
   - Full log management for CodeBuild log groups
   - Actions: All logs actions
   - Scoped to: `/aws/codebuild/${Prefix}-*`

5. **CodePipeline** (`ManageCodePipelineByResourcePrefix`)
   - Full CodePipeline management
   - Actions: All codepipeline actions
   - Scoped to: `arn:aws:codepipeline:${Region}:${Account}:${Prefix}-*`

6. **CodeBuild** (`ManageCodeBuildByResourcePrefix`)
   - Full CodeBuild project management
   - Actions: All codebuild actions
   - Scoped to: `arn:aws:codebuild:${Region}:${Account}:project/${Prefix}-*`

7. **IAM Worker Roles** (`PassAndDeleteWorkerRolesByResourcePrefix`, `ManageWorkerRolesByResourcePrefix`)
   - Pass and manage worker roles for pipeline resources
   - Actions: PassRole, CreateRole, DeleteRole, AttachRolePolicy, etc.
   - Scoped to: `arn:aws:iam::${Account}:role${RolePath}${Prefix}-Worker-*`
   - Condition: Enforces permissions boundary if specified

8. **IAM Read-Only** (`IAMReadOnly`, `InspectServiceRole`)
   - Read-only access to IAM roles and policies
   - Actions: Get*, List*
   - Scoped to: All roles and policies (read-only)

### PrefixBasedManagedPolicy

Type: AWS::IAM::ManagedPolicy

Managed policy that grants users/groups/roles permission to deploy pipeline stacks using the service role.

**Key Properties:**
- **Path**: ServiceRolePath parameter
- **Attached To**: Groups, Roles, and/or Users specified in parameters
- **Description**: Managed Policy to Create and Manage AWS CodePipeline for application projects under prefix

**Permissions:**

1. **Pass Service Role** (`AllowUserToPassSpecificCloudFormationServiceRole`)
   - Allows passing the service role to CloudFormation
   - Actions: iam:GetRole, iam:PassRole
   - Scoped to: The service role ARN
   - Condition: Only when passed to cloudformation.amazonaws.com

This policy enables users to deploy CloudFormation stacks using the service role without granting them direct access to create pipeline resources.

## Outputs

### PrefixBasedCloudFormationPipelineMgmtServiceRoleArn

ARN of the CloudFormation service role.

**Value:** ARN of PrefixBasedCloudFormationPipelineMgmtServiceRole

**Export Name:** `${PrefixUpper}-CloudFormation-Pipeline-Mgmt-Service-Role-Arn`

**Usage:** Use this ARN when deploying pipeline CloudFormation stacks via CLI or console.

**Example Value:** `arn:aws:iam::123456789012:role/ACME-CloudFormation-Service-Role-Pipeline-Management`

### PrefixBasedCloudFormationPipelineMgmtServiceRoleName

Name of the CloudFormation service role.

**Value:** Name of PrefixBasedCloudFormationPipelineMgmtServiceRole

**Export Name:** `${PrefixUpper}-CloudFormation-Pipeline-Mgmt-Service-Role-Name`

**Usage:** Reference the role name in other templates or scripts.

### PrefixBasedManagedPolicyArn

ARN of the managed policy.

**Value:** ARN of PrefixBasedManagedPolicy

**Export Name:** `${PrefixUpper}-CloudFormation-Pipeline-Mgmt-Service-ManagedPolicy-Arn`

**Usage:** Attach this policy to additional users, groups, or roles after deployment.

### PrefixBasedManagedPolicyName

Name of the managed policy.

**Value:** Name of PrefixBasedManagedPolicy

**Export Name:** `${PrefixUpper}-CloudFormation-Pipeline-Mgmt-Service-ManagedPolicy-Name`

**Usage:** Reference the policy name in other templates or scripts.

## Conditions

The template uses several conditions to control resource configuration:

- **HasS3ModuleLocation**: True when S3ModuleLocation is not empty. When true, the provided bucket name is used for module resolution instead of the RegionalModuleBuckets mapping.
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
  --stack-name acme-pipeline-service-role \
  --template-body file://template-service-role-pipeline.yml \
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
  --stack-name acme-pipeline-service-role \
  --template-body file://template-service-role-pipeline.yml \
  --parameters \
    ParameterKey=Prefix,ParameterValue=acme \
    ParameterKey=PrefixUpper,ParameterValue=ACME \
    ParameterKey=GroupNames,ParameterValue=Developers \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### With Permissions Boundary

```bash
# Deploy with permissions boundary
aws cloudformation create-stack \
  --stack-name acme-pipeline-service-role \
  --template-body file://template-service-role-pipeline.yml \
  --parameters \
    ParameterKey=Prefix,ParameterValue=acme \
    ParameterKey=PrefixUpper,ParameterValue=ACME \
    ParameterKey=PermissionsBoundaryArn,ParameterValue=arn:aws:iam::123456789012:policy/OrgBoundary \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### Using Service Role to Deploy Pipeline

```bash
# Deploy pipeline stack using the service role
aws cloudformation create-stack \
  --stack-name acme-myapp-prod-pipeline \
  --template-body file://template-pipeline.yml \
  --role-arn arn:aws:iam::123456789012:role/ACME-CloudFormation-Service-Role-Pipeline-Management \
  --parameters \
    ParameterKey=Prefix,ParameterValue=acme \
    ParameterKey=ProjectId,ParameterValue=myapp \
    ParameterKey=StageId,ParameterValue=prod \
    ... \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

## Troubleshooting

### Access Denied When Deploying Pipeline Stack

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

### Permissions Boundary Violation

**Symptom:** CloudFormation fails with "Cannot exceed permissions boundary" error.

**Possible Causes:**
- Service role trying to create resources not allowed by boundary
- Permissions boundary ARN incorrect
- Boundary policy too restrictive

**Solutions:**
1. Verify permissions boundary ARN is correct
2. Check boundary policy allows required actions
3. Ensure service role respects boundary when creating IAM roles
4. Review CloudFormation error message for specific denied action

### Cannot Create Worker Roles

**Symptom:** Pipeline stack fails when creating CodeBuild or CodePipeline service roles.

**Possible Causes:**
- Worker role names don't match `${Prefix}-Worker-*` pattern
- RolePath parameter doesn't match role paths in pipeline template
- Permissions boundary not applied to worker roles

**Solutions:**
1. Verify worker role names start with `${Prefix}-Worker-`
2. Check RolePath parameter matches pipeline template
3. Ensure pipeline template applies permissions boundary to worker roles
4. Review IAM role creation errors in CloudFormation events

### S3 Bucket Access Denied

**Symptom:** Pipeline fails to access S3 buckets.

**Possible Causes:**
- Bucket names don't match prefix pattern
- S3BucketNameOrgPrefix parameter incorrect
- Bucket in different account or region

**Solutions:**
1. Verify bucket names match `${S3OrgPrefix}-${Prefix}-*` or `${Prefix}-${Region}-${Account}-*` pattern
2. Check S3BucketNameOrgPrefix parameter matches actual bucket prefix
3. Ensure buckets are in same account and region
4. Review S3 permissions in service role policy

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

- **Pipeline Templates**:
  - [template-pipeline.yml](../pipeline/template-pipeline-README.md)
  - [template-pipeline-github.yml](../pipeline/template-pipeline-github-README.md)
  - [template-pipeline-build-only.yml](../pipeline/template-pipeline-build-only-README.md)

## Security Considerations

1. **Least Privilege**: All permissions scoped to prefix-specific resources
2. **Prefix Isolation**: Different prefixes cannot access each other's resources
3. **Permissions Boundaries**: Support for organizational security policies
4. **Path-Based Organization**: IAM paths for additional access control
5. **Conditional Permissions**: Permissions boundary enforced when creating roles
6. **Audit Trail**: All actions logged via CloudTrail
7. **Managed Policy**: Separate policy for user access control

## Best Practices

1. **One Service Role Per Prefix**: Deploy separate service roles for each team or environment
2. **Use Groups**: Attach managed policy to groups rather than individual users
3. **Permissions Boundaries**: Apply boundaries in regulated environments
4. **Descriptive Prefixes**: Use clear, short prefixes (2-6 characters)
5. **Path Organization**: Use IAM paths to organize roles by application or team
6. **Regular Review**: Periodically review service role permissions
7. **Export Usage**: Use exported outputs for cross-stack references

## Cost Considerations

**IAM Costs:**
- IAM roles and policies: No charge
- No ongoing costs for service roles

**Operational Costs:**
- Resources created by pipeline stacks incur standard AWS charges
- CodePipeline: $1 per active pipeline per month
- CodeBuild: Charged per build minute
- S3: Storage and request costs

## Additional Resources

- [CloudFormation Service Roles](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-iam-servicerole.html)
- [IAM Permissions Boundaries](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html)
- [IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [Least Privilege Principle](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#grant-least-privilege)
- [GitHub Repository](https://github.com/63Klabs/atlantis-sam-templates/)
