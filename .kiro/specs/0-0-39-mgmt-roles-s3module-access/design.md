# Design Document

## Overview

This design adds read-only S3 access permissions to three management role modules to enable CloudFormation's AWS::Include transform to resolve module snippets from an S3 bucket during stack deployments. The permissions are scoped to a specific bucket and namespace prefix, following the principle of least privilege.

### Current State

The `prefix-based-infrastructure.yml` template creates management roles by loading reusable module definitions from an S3 bucket using the AWS::Include transform. However, these management roles lack explicit permissions to read from the S3 bucket containing the modules they reference. This creates a gap where CloudFormation cannot resolve AWS::Include references during stack deployments.

### Proposed Solution

Add a consistent IAM policy statement named `S3ModuleBucketReadOnly` to three module files:
1. `pipeline-mgmt-role.yml` - Inline policy in the role definition
2. `storage-mgmt-role.yml` - Inline policy in the role definition
3. `network-cloudfront-mgmt-policy.yml` - Statement in the managed policy document

The statement grants read-only access (GetObject, GetObjectVersion, ListBucket) scoped to the S3 bucket and namespace path specified by parameters `S3ModuleLocation` and `S3ModuleNamespace`.

### Impact

- **Non-breaking change**: Adds permissions without modifying existing permissions or resource names
- **Scope**: Three module files require updates
- **Version**: PATCH increment (v0.0.0 remains unchanged in development mode)
- **Backward compatibility**: Existing stacks can update without parameter changes


## Architecture

### Components

The solution involves updating three existing CloudFormation module files:

1. **pipeline-mgmt-role.yml** - Contains inline IAM policies for the Pipeline Management Service Role
2. **storage-mgmt-role.yml** - Contains inline IAM policies for the Storage Management Service Role
3. **network-cloudfront-mgmt-policy.yml** - Contains a managed IAM policy shared by Network CloudFront and Network Full Management Roles

### Parent Template Integration

The `prefix-based-infrastructure.yml` parent template:
- Defines parameters `S3ModuleLocation` and `S3ModuleNamespace` at the template level
- Uses AWS::Include to load each module from S3
- Passes all parameters to included modules via CloudFormation's parameter inheritance

### Module Hierarchy

```
prefix-based-infrastructure.yml (parent)
├── Parameters: S3ModuleLocation, S3ModuleNamespace
└── Resources:
    ├── PrefixBasedCloudFormationPipelineMgmtServiceRole
    │   └── Loads: pipeline-mgmt-role.yml
    ├── PrefixBasedCloudFormationStorageMgmtServiceRole
    │   └── Loads: storage-mgmt-role.yml
    ├── PrefixBasedNetworkCloudFrontMgmtPolicy
    │   └── Loads: network-cloudfront-mgmt-policy.yml
    ├── PrefixBasedCloudFormationNetworkCloudFrontMgmtServiceRole
    │   └── Attaches: PrefixBasedNetworkCloudFrontMgmtPolicy
    └── PrefixBasedCloudFormationNetworkFullMgmtServiceRole
        └── Attaches: PrefixBasedNetworkCloudFrontMgmtPolicy
```

### Permission Flow

When CloudFormation deploys a stack using one of these management roles:
1. Service role assumes the management role identity
2. CloudFormation evaluates AWS::Include transforms in the stack template
3. CloudFormation needs S3 read permissions to fetch module content
4. The new `S3ModuleBucketReadOnly` statement grants the required access
5. CloudFormation resolves the include and continues deployment


## Components and Interfaces

### IAM Policy Statement Structure

The `S3ModuleBucketReadOnly` statement follows this exact structure across all three modules:

```yaml
- Sid: S3ModuleBucketReadOnly
  Effect: Allow
  Action:
    - s3:GetObject
    - s3:GetObjectVersion
    - s3:ListBucket
  Resource:
    - Fn::Sub: "arn:aws:s3:::${S3ModuleLocation}"
    - Fn::Sub: "arn:aws:s3:::${S3ModuleLocation}/${S3ModuleNamespace}/*"
  Condition:
    StringLike:
      s3:prefix:
        - Fn::Sub: "${S3ModuleNamespace}/*"
```

### Statement Components

#### Sid (Statement ID)
- **Value**: `S3ModuleBucketReadOnly`
- **Purpose**: Unique identifier for the statement within the policy
- **Consistency**: Identical across all three modules for maintainability

#### Effect
- **Value**: `Allow`
- **Purpose**: Grants the specified permissions (as opposed to denying them)

#### Actions
- **s3:GetObject**: Read object content at a specific version or latest version
- **s3:GetObjectVersion**: Read specific object versions (supports versioned buckets)
- **s3:ListBucket**: List objects within the bucket with prefix filtering
- **Rationale**: Minimum permissions required for CloudFormation to resolve AWS::Include references
- **Excluded**: Write operations (PutObject, DeleteObject, PutBucketPolicy) are not granted


#### Resources
Two resource ARNs are specified:

1. **Bucket-level access** (for ListBucket):
   ```yaml
   Fn::Sub: "arn:aws:s3:::${S3ModuleLocation}"
   ```
   - Grants permission to list objects in the bucket
   - Required for prefix-based filtering via Condition

2. **Object-level access** (for GetObject, GetObjectVersion):
   ```yaml
   Fn::Sub: "arn:aws:s3:::${S3ModuleLocation}/${S3ModuleNamespace}/*"
   ```
   - Grants permission to read objects under the namespace path
   - Wildcard (`/*`) allows access to all objects within the namespace

#### Condition
```yaml
Condition:
  StringLike:
    s3:prefix:
      - Fn::Sub: "${S3ModuleNamespace}/*"
```

- **Purpose**: Restricts ListBucket operations to objects with keys matching the namespace prefix
- **Operator**: `StringLike` allows wildcard pattern matching
- **Context Key**: `s3:prefix` - the prefix parameter passed to ListBucket API calls
- **Effect**: Even though ListBucket operates at bucket level, this condition ensures only objects under `${S3ModuleNamespace}/` can be listed

### Parameter Dependencies

Both `S3ModuleLocation` and `S3ModuleNamespace` parameters are defined in the parent template and inherited by modules through AWS::Include's parameter passing mechanism.


### Module-Specific Implementation

#### 1. pipeline-mgmt-role.yml

**Location**: `templates/v2/modules/management-roles/pipeline-mgmt-role.yml`

**Current Structure**:
- Type: `AWS::IAM::Role`
- Contains inline `Policies` list with one PolicyDocument
- Last statement: `InspectServiceRole` (Sid for listing attached role policies)

**Insertion Point**:
Add the `S3ModuleBucketReadOnly` statement as the **last statement** in the `Statement` array within the PolicyDocument, after the existing `InspectServiceRole` statement.

**Header Update Required**:
Update the module header comment to include:
```yaml
# Parent template must define parameters:
#   Prefix, PrefixUpper, S3BucketNameOrgPrefix, ServiceRolePath, RolePath,
#   PermissionsBoundaryArn, GroupNames, RoleNames, UserNames,
#   S3ModuleLocation, S3ModuleNamespace
```

#### 2. storage-mgmt-role.yml

**Location**: `templates/v2/modules/management-roles/storage-mgmt-role.yml`

**Current Structure**:
- Type: `AWS::IAM::Role`
- Contains inline `Policies` list with one PolicyDocument
- Last statement: `InspectServiceRole` (Sid for listing attached role policies)

**Insertion Point**:
Add the `S3ModuleBucketReadOnly` statement as the **last statement** in the `Statement` array within the PolicyDocument, after the existing `InspectServiceRole` statement.

**Header Update Required**:
Update the module header comment to include:
```yaml
# Parent template must define parameters:
#   Prefix, PrefixUpper, S3BucketNameOrgPrefix, ServiceRolePath, RolePath,
#   PermissionsBoundaryArn, GroupNames, RoleNames, UserNames,
#   S3ModuleLocation, S3ModuleNamespace
```


#### 3. network-cloudfront-mgmt-policy.yml

**Location**: `templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml`

**Current Structure**:
- Type: `AWS::IAM::ManagedPolicy`
- Contains a `PolicyDocument` with statements
- Last statement: `AcmCertificateRead` (Sid for reading ACM certificates)

**Insertion Point**:
Add the `S3ModuleBucketReadOnly` statement as the **last statement** in the `Statement` array within the PolicyDocument, after the existing `AcmCertificateRead` statement.

**Header Update Required**:
Update the module header comment to include:
```yaml
# Parent template must define parameters:
#   Prefix, PrefixUpper, S3BucketNameOrgPrefix, ServiceRolePath,
#   S3ModuleLocation, S3ModuleNamespace
```

**Inheritance**:
This managed policy is attached to two service roles:
- `network-cloudfront-mgmt-role.yml` → Creates `PrefixBasedCloudFormationNetworkCloudFrontMgmtServiceRole`
- `network-full-mgmt-role.yml` → Creates `PrefixBasedCloudFormationNetworkFullMgmtServiceRole`

Both roles will automatically inherit the S3 read permissions through the managed policy attachment. No direct modification of these role modules is needed.


## Data Models

### Parameters

#### S3ModuleLocation
- **Type**: String
- **Format**: S3 bucket name (3-63 characters, lowercase alphanumeric and hyphens)
- **Example**: `63klabs-atlas-us-east-1`
- **Purpose**: Identifies the S3 bucket containing CloudFormation module snippets
- **Source**: Defined in parent template `prefix-based-infrastructure.yml`

#### S3ModuleNamespace
- **Type**: String
- **Format**: Path prefix (lowercase alphanumeric, hyphens, forward slashes)
- **Example**: `atlantis-sam-templates/v2`
- **Purpose**: Scopes module access to a specific namespace within the bucket
- **Source**: Defined in parent template `prefix-based-infrastructure.yml`
- **Default**: `atlantis`

### Resource ARN Formats

#### Bucket ARN
```
arn:aws:s3:::{S3ModuleLocation}
```
- Used for: ListBucket permission
- Scope: Entire bucket (filtered by condition)

#### Object ARN
```
arn:aws:s3:::{S3ModuleLocation}/{S3ModuleNamespace}/*
```
- Used for: GetObject, GetObjectVersion permissions
- Scope: All objects under the namespace path
- Wildcard: Matches any object key starting with `{S3ModuleNamespace}/`


### IAM Condition Context

#### s3:prefix Context Key
- **Type**: String
- **Used in**: ListBucket API calls
- **Format**: Path prefix without leading slash
- **Condition Operator**: `StringLike`
- **Pattern**: `{S3ModuleNamespace}/*`
- **Effect**: Restricts visible objects to those within the namespace

### Module Header Documentation Format

Each module has a header comment that documents required parent parameters. The updated format includes:

```yaml
# Parent template must define parameters:
#   [existing parameters],
#   S3ModuleLocation, S3ModuleNamespace
```

This documentation:
- Helps developers understand parameter dependencies
- Serves as a reference during troubleshooting
- Ensures AWS::Include parameter passing is complete
- Does not affect runtime behavior (comments are ignored by CloudFormation)


## Error Handling

### Missing Parameter Errors

**Scenario**: Parent template does not define `S3ModuleLocation` or `S3ModuleNamespace`

**CloudFormation Behavior**:
- Template validation fails with parameter reference error
- Error message: "Template error: instance of Fn::Sub references undefined parameter"
- Stack creation/update is blocked before any resources are created

**Resolution**:
- Ensure parent template defines both parameters
- This design assumes parameters already exist in `prefix-based-infrastructure.yml` (they do)

### Invalid Resource ARN Format

**Scenario**: Malformed S3 bucket name or namespace path

**CloudFormation Behavior**:
- IAM policy creation fails with invalid ARN error
- Stack creation/update rolls back automatically
- No partial permissions are granted

**Prevention**:
- Parameter constraints enforce valid formats:
  - `S3ModuleLocation`: 3-63 characters, lowercase alphanumeric and hyphens
  - `S3ModuleNamespace`: 1-128 characters, path segments with alphanumeric and hyphens

**Resolution**:
- Correct parameter values in parent template
- Redeploy stack with valid parameters


### Access Denied During Deployment

**Scenario**: CloudFormation attempts to resolve AWS::Include but S3 read permissions are missing

**CloudFormation Behavior**:
- Stack deployment fails with "Access Denied" error
- Error context indicates S3 GetObject failure
- Stack rolls back to previous state

**Post-Implementation Prevention**:
- The `S3ModuleBucketReadOnly` statement prevents this error
- Management roles can now read module snippets from S3

**Troubleshooting Steps**:
1. Verify management role has the new policy statement
2. Check S3 bucket policy allows role access
3. Confirm bucket and namespace parameters are correct
4. Validate objects exist at expected S3 paths

### Namespace Path Mismatch

**Scenario**: Modules stored under different namespace than specified in parameter

**CloudFormation Behavior**:
- AWS::Include transform fails with "object not found" error
- Stack deployment fails and rolls back
- IAM permissions are correctly scoped but objects are inaccessible

**Resolution**:
- Verify S3 object keys match pattern: `{S3ModuleNamespace}/templates/v2/modules/...`
- Correct `S3ModuleNamespace` parameter value
- Upload modules to correct S3 path


### Policy Size Limit Exceeded

**Scenario**: Adding the new statement exceeds IAM policy size limits

**IAM Limits**:
- Inline role policy: 10,240 characters maximum
- Managed policy: 6,144 characters maximum

**Current State Analysis**:
- pipeline-mgmt-role.yml: ~5,800 characters - sufficient headroom
- storage-mgmt-role.yml: ~6,900 characters - sufficient headroom
- network-cloudfront-mgmt-policy.yml: ~4,100 characters - sufficient headroom

**New Statement Size**: ~350 characters

**Risk Assessment**: LOW - All three modules have adequate space for the new statement

**Mitigation** (if limit ever approached):
- Consolidate similar statements using wildcard patterns
- Split large inline policies into separate managed policies
- Use more concise Fn::Sub expressions


## Security Analysis

### Principle of Least Privilege

**Read-Only Access**:
- Actions limited to: `GetObject`, `GetObjectVersion`, `ListBucket`
- No write permissions: `PutObject`, `DeleteObject`, `PutBucketPolicy` are excluded
- No bucket configuration changes: `PutBucketVersioning`, `PutLifecycleConfiguration` are excluded
- No access control modifications: `PutBucketAcl`, `PutObjectAcl` are excluded

**Rationale**:
Management roles only need to read module snippets during stack deployment. Write operations are not required for CloudFormation's AWS::Include functionality.

### Scoping and Boundaries

**Bucket Scoping**:
- Access limited to single bucket: `${S3ModuleLocation}`
- No wildcard bucket access (no `arn:aws:s3:::*`)
- Other S3 buckets remain inaccessible

**Path Scoping**:
- Object access restricted to: `${S3ModuleLocation}/${S3ModuleNamespace}/*`
- ListBucket operations filtered by condition: `s3:prefix = ${S3ModuleNamespace}/*`
- Objects outside namespace path are inaccessible

**Namespace Isolation**:
If multiple teams use the same S3 bucket with different namespaces:
- Team A with namespace `team-a` can only access objects under `s3://.../team-a/*`
- Team B with namespace `team-b` can only access objects under `s3://.../team-b/*`
- Cross-team access is prevented by path scoping


### Condition-Based Filtering

**ListBucket Protection**:
The condition clause prevents enumeration attacks:

```yaml
Condition:
  StringLike:
    s3:prefix:
      - Fn::Sub: "${S3ModuleNamespace}/*"
```

**Effect**:
- A ListBucket call without prefix filter is denied
- A ListBucket call with prefix outside namespace is denied
- Only ListBucket calls with prefix matching `${S3ModuleNamespace}/*` succeed

**Behavior Example**:
- Namespace: `atlantis-sam-templates/v2`
- ✅ Allowed: `ListBucket` with prefix `atlantis-sam-templates/v2/modules/`
- ❌ Denied: `ListBucket` with prefix `other-namespace/`
- ❌ Denied: `ListBucket` with no prefix (attempts to list entire bucket)

### Trust Relationship

**Service Principal**:
All three management roles have identical trust policies:
```yaml
AssumeRolePolicyDocument:
  Statement:
  - Sid: "EventTrustPolicy"
    Effect: Allow
    Action: sts:AssumeRole
    Principal:
      Service:
      - cloudformation.amazonaws.com
```

**Security Properties**:
- Only CloudFormation service can assume these roles
- Users cannot assume these roles directly
- Cross-account access is not permitted (no Principal with AWS account)
- Requires CloudFormation to be the actor for S3 access


### Versioned Object Access

**GetObjectVersion Permission**:
Grants access to specific object versions in versioned S3 buckets.

**Security Considerations**:
- Read-only access to version history
- Cannot delete versions (no `DeleteObjectVersion`)
- Cannot modify version metadata
- Useful for auditing and rollback scenarios

**Use Case**:
If the module bucket has versioning enabled:
- CloudFormation can reference specific object versions in AWS::Include
- Format: `s3://bucket/key?versionId=abc123`
- Management role can retrieve the specified version

### Permission Boundary Compatibility

**Existing Boundary Support**:
All three modules already support permissions boundaries via `PermissionsBoundaryArn` parameter.

**Impact of New Statement**:
- The S3 read permissions are added to inline/managed policies
- Permissions boundary (if applied) continues to restrict the role's maximum permissions
- If boundary does NOT allow S3 access, role still cannot access S3 despite this statement

**Best Practice Alignment**:
This design respects organizational permission boundaries. If a boundary restricts S3 access, administrators must update both the boundary and this policy.


## Testing Strategy

This feature involves Infrastructure as Code (CloudFormation templates) which is not suitable for property-based testing. Testing will focus on template validation, deployment verification, and integration testing.

### Template Validation

**Tool**: `cfn-lint`

**Scope**: All three modified module files

**Test Cases**:
1. **Syntax Validation**
   - Verify YAML syntax is valid
   - Confirm no duplicate keys
   - Check proper indentation

2. **CloudFormation Structure**
   - Validate IAM policy document structure
   - Verify Fn::Sub intrinsic functions are correctly formatted
   - Check Resource ARN patterns are valid
   - Confirm Condition syntax is correct

3. **Parameter References**
   - Ensure `S3ModuleLocation` and `S3ModuleNamespace` references resolve
   - Verify all Fn::Sub expressions have required parameters

4. **IAM Policy Compliance**
   - Check statement structure follows AWS IAM policy grammar
   - Verify Effect, Action, Resource, and Condition are properly formatted
   - Confirm Sid is unique within each policy

**Expected Results**:
- cfn-lint returns 0 errors for all three module files
- No warnings about policy structure or parameter references


### Deployment Verification

**Test Environment**: AWS account with CloudFormation permissions

**Prerequisites**:
- S3 bucket containing module snippets
- Valid `S3ModuleLocation` and `S3ModuleNamespace` values
- IAM permissions to create/update CloudFormation stacks

**Test Procedure**:
1. Deploy or update `prefix-based-infrastructure.yml` stack
2. Verify stack CREATE_COMPLETE or UPDATE_COMPLETE status
3. Check all four management roles are created/updated:
   - Pipeline Management Service Role
   - Storage Management Service Role
   - Network CloudFront Management Service Role
   - Network Full Management Service Role

**Verification Steps**:
1. Navigate to IAM console
2. Locate each management role
3. Review inline policies (for pipeline and storage roles)
4. Review managed policy (for network roles via attached policy)
5. Confirm `S3ModuleBucketReadOnly` statement exists
6. Verify statement structure matches design

**Expected Results**:
- All roles contain or inherit the new S3 read permissions
- Statement Sid is `S3ModuleBucketReadOnly`
- Actions: `s3:GetObject`, `s3:GetObjectVersion`, `s3:ListBucket`
- Resources reference correct `S3ModuleLocation` and `S3ModuleNamespace`
- Condition properly scopes ListBucket to namespace


### Integration Testing

**Objective**: Verify management roles can deploy stacks that use AWS::Include to reference S3 modules

**Test Case 1: Pipeline Stack Deployment**
1. Create a test pipeline stack template with AWS::Include referencing module from S3
2. Deploy using Pipeline Management Service Role
3. Verify stack deploys successfully
4. Confirm AWS::Include resolved module content from S3

**Test Case 2: Storage Stack Deployment**
1. Create a test storage stack template with AWS::Include referencing module from S3
2. Deploy using Storage Management Service Role
3. Verify stack deploys successfully
4. Confirm AWS::Include resolved module content from S3

**Test Case 3: Network Stack Deployment**
1. Create a test network stack template with AWS::Include referencing module from S3
2. Deploy using Network CloudFront Management Service Role
3. Verify stack deploys successfully
4. Confirm AWS::Include resolved module content from S3

**Test Case 4: Network Stack with Route53**
1. Create a test network stack with AWS::Include and Route53 resources
2. Deploy using Network Full Management Service Role
3. Verify stack deploys successfully
4. Confirm AWS::Include resolved module content from S3

**Expected Results**:
- All stacks deploy without Access Denied errors
- AWS::Include transforms resolve successfully
- Module content is fetched from S3 and incorporated into deployed stacks
- Stack resources are created as defined in modules


### Permission Verification Testing

**Test Case 5: Read Access Confirmation**
1. Use AWS IAM Policy Simulator or CloudTrail
2. Simulate/execute `s3:GetObject` on `s3://${S3ModuleLocation}/${S3ModuleNamespace}/test-module.yml`
3. Verify operation is ALLOWED

**Test Case 6: Write Access Denial**
1. Use AWS IAM Policy Simulator or attempt actual operation
2. Simulate/execute `s3:PutObject` on `s3://${S3ModuleLocation}/${S3ModuleNamespace}/test-module.yml`
3. Verify operation is DENIED (Access Denied)

**Test Case 7: Namespace Isolation**
1. Use AWS IAM Policy Simulator
2. Simulate `s3:GetObject` on `s3://${S3ModuleLocation}/other-namespace/module.yml`
3. Verify operation is DENIED (outside namespace scope)

**Test Case 8: ListBucket Filtering**
1. Use AWS IAM Policy Simulator
2. Simulate `s3:ListBucket` on `${S3ModuleLocation}` with prefix `${S3ModuleNamespace}/`
3. Verify operation is ALLOWED
4. Simulate `s3:ListBucket` on `${S3ModuleLocation}` with prefix `other-namespace/`
5. Verify operation is DENIED (condition not met)

**Expected Results**:
- Read operations within namespace: ALLOWED
- Write operations: DENIED
- Read operations outside namespace: DENIED
- ListBucket with correct prefix: ALLOWED
- ListBucket with incorrect prefix: DENIED


### Backward Compatibility Testing

**Test Case 9: Existing Stack Update**
1. Identify an existing stack deployed with old management role (without S3 permissions)
2. Update `prefix-based-infrastructure.yml` stack with new module versions
3. Verify management role stack update completes successfully
4. Update an existing application stack (no parameter changes needed)
5. Verify application stack update succeeds

**Expected Results**:
- Management role stack update: UPDATE_COMPLETE
- No parameter errors during update
- Application stacks continue functioning
- New S3 permissions available for future AWS::Include usage

**Test Case 10: New Stack Deployment**
1. Deploy fresh `prefix-based-infrastructure.yml` stack with new module versions
2. Deploy new application stacks using the management roles
3. Verify all stacks deploy successfully
4. Confirm management roles have S3 permissions from initial creation

**Expected Results**:
- Management role stack: CREATE_COMPLETE
- Application stacks deploy without issues
- S3 permissions present in newly created roles


### Negative Testing

**Test Case 11: Missing S3ModuleLocation Parameter**
1. Create a test module that references `${S3ModuleLocation}` in Fn::Sub
2. Deploy parent template WITHOUT defining S3ModuleLocation parameter
3. Verify CloudFormation validation error occurs
4. Confirm error message indicates undefined parameter reference

**Expected Results**:
- Template validation fails before resource creation
- Clear error message about missing parameter
- No partial resources created

**Test Case 12: Malformed Namespace**
1. Set `S3ModuleNamespace` to invalid value (e.g., `/leading-slash/`)
2. Attempt to deploy management role stack
3. Verify parameter validation error due to AllowedPattern constraint

**Expected Results**:
- Stack creation blocked by parameter constraint
- Error indicates parameter does not match allowed pattern
- No IAM resources created with invalid namespace

**Test Case 13: Non-existent S3 Bucket**
1. Deploy management role stack with valid but non-existent S3ModuleLocation
2. Management role stack should succeed (IAM policy creation doesn't validate bucket existence)
3. Attempt to deploy application stack using AWS::Include
4. Verify AWS::Include fails with "bucket does not exist" error

**Expected Results**:
- Management role stack: CREATE_COMPLETE (IAM doesn't validate bucket)
- Application stack using AWS::Include: CREATE_FAILED with S3 error
- Demonstrates IAM permissions are correctly configured but bucket must exist


## Rollback Strategy

### Development Phase Rollback

**Git Revert**:
If issues are discovered during development (before deployment):

```bash
git revert <commit-hash>
```

This reverts the changes to the three module files, removing the S3ModuleBucketReadOnly statements.

**Impact**: 
- No deployed resources affected (changes only in repository)
- Clean rollback with full git history preserved

### Post-Deployment Rollback

**Scenario**: Issues discovered after deploying updated management role stack

**Option 1: Stack Update with Previous Version**
1. Identify previous version of module files (before S3 statement addition)
2. Upload previous module versions to S3 (different path or use S3 versioning)
3. Update `prefix-based-infrastructure.yml` stack pointing to previous module versions
4. CloudFormation updates management roles, removing S3ModuleBucketReadOnly statement

**Impact**:
- Management roles lose S3 read permissions
- Existing stacks continue functioning (don't use AWS::Include)
- New stacks using AWS::Include will fail until S3 permissions restored


**Option 2: Manual IAM Policy Edit**
1. Navigate to IAM console
2. Locate each management role
3. Edit inline policy (for pipeline/storage roles) or managed policy (for network roles)
4. Remove `S3ModuleBucketReadOnly` statement
5. Save policy

**Impact**:
- Faster rollback (no CloudFormation stack update required)
- Creates configuration drift (IAM differs from module source code)
- Next stack update will reapply S3 permissions (requires revert in source)

**Recommendation**: Use Option 1 (stack update) to maintain consistency between source code and deployed resources.

### Rollback Testing

Before deploying to production, verify rollback procedures work:

1. Deploy updated management role stack (with S3 permissions)
2. Verify stacks can use AWS::Include successfully
3. Roll back to previous module versions
4. Verify management role stack updates successfully
5. Confirm S3ModuleBucketReadOnly statement is removed from roles
6. Test that AWS::Include fails without permissions (confirms rollback worked)

**Expected Results**:
- Rollback completes without errors
- Management roles return to previous state
- Clear understanding of rollback impact on AWS::Include functionality


### Emergency Rollback Procedure

**When to Use**: Critical security issue or production outage related to S3 permissions

**Steps**:
1. Immediately edit IAM policies in console to remove S3ModuleBucketReadOnly
2. Document the manual change in incident log
3. Investigate root cause
4. Plan proper source code revert for next maintenance window
5. Update management role stack with reverted module versions

**Communication**:
- Notify stakeholders that AWS::Include functionality will be unavailable
- Document which stacks/deployments are affected
- Provide timeline for proper rollback via source code

**Post-Incident**:
- Root cause analysis: Why did S3 permissions cause issues?
- Update testing strategy to catch similar issues in future
- Consider canary deployments for future IAM permission changes


## Version Management

### Template Version Strategy

**Parent Template**: `prefix-based-infrastructure.yml`
- Current version: `v0.0.0/2026-04-28`
- Development mode: PATCH remains at 0
- No version increment during active development
- Date will update to reflect last modification

**Module Files**: No individual versions
- Modules are versioned as part of repository release
- Individual module files don't have version headers
- Version tracking occurs at repository level

### Repository Versioning

**Current State**:
The repository uses semantic versioning:
- MAJOR.MINOR.PATCH format
- Version tracked in CHANGELOG.md and git tags

**This Change Impact**:
- **Type**: PATCH increment (backward compatible addition)
- **Reasoning**: 
  - Adds permissions without removing existing functionality
  - No breaking changes to interfaces or parameters
  - Existing stacks can update without parameter modifications
  - Only adds read permissions, doesn't change existing security boundaries

**Next Release**:
When this feature is released, repository version will increment PATCH:
- If current version is `v0.9.8`, next release would be `v0.9.9`
- If current version is `v1.2.3`, next release would be `v1.2.4`


### Development Mode Versioning

**During Active Development**:
- `prefix-based-infrastructure.yml` version remains `v0.0.0`
- PATCH=0 indicates unreleased development version
- Date updates with each modification
- Format: `v0.0.0/YYYY-MM-DD`

**Upon Release**:
- Update version to next semantic version
- Add release date: `vX.Y.Z (YYYY-MM-DD)`
- Create git tag matching version
- Update CHANGELOG.md with version and changes

### Module Update Propagation

**S3 Module Distribution**:
1. Modules are stored in S3 at: `s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/management-roles/`
2. When repository is updated, modules must be uploaded to S3
3. Existing deployed stacks reference S3 module locations via AWS::Include
4. Next stack update will use new module versions from S3

**Version Consistency**:
- Parent template version in repository reflects overall template state
- Module files in S3 must match repository version
- Mismatched versions between repository and S3 can cause deployment issues
- Best practice: Upload modules to S3 as part of release process


## Implementation Notes

### File Locations

**Module Files to Modify**:
```
templates/v2/modules/management-roles/
├── pipeline-mgmt-role.yml
├── storage-mgmt-role.yml
└── network-cloudfront-mgmt-policy.yml
```

**Parent Template** (for reference, no changes needed):
```
templates/v2/account/prefix-based-infrastructure.yml
```

### Exact Insertion Points

**1. pipeline-mgmt-role.yml**:
- Navigate to: `Properties.Policies[0].PolicyDocument.Statement`
- Insert new statement after the last existing statement (after `InspectServiceRole`)
- Maintain consistent indentation (6 spaces for statement level)

**2. storage-mgmt-role.yml**:
- Navigate to: `Properties.Policies[0].PolicyDocument.Statement`
- Insert new statement after the last existing statement (after `InspectServiceRole`)
- Maintain consistent indentation (6 spaces for statement level)

**3. network-cloudfront-mgmt-policy.yml**:
- Navigate to: `Properties.PolicyDocument.Statement`
- Insert new statement after the last existing statement (after `AcmCertificateRead`)
- Maintain consistent indentation (6 spaces for statement level)


### YAML Formatting Requirements

**Indentation**:
- Use spaces, not tabs
- Statement level: 6 spaces
- Property level within statement: 8 spaces
- List items within properties: 8 spaces (after `- `)

**Long-Form Intrinsic Functions**:
- AWS::Include does not support shorthand YAML tags (`!Sub`, `!Ref`)
- Use long-form syntax: `Fn::Sub`, `Ref`
- This applies to all CloudFormation functions within module files

**Example Formatting**:
```yaml
      - Sid: S3ModuleBucketReadOnly
        Effect: Allow
        Action:
          - s3:GetObject
          - s3:GetObjectVersion
          - s3:ListBucket
        Resource:
          - Fn::Sub: "arn:aws:s3:::${S3ModuleLocation}"
          - Fn::Sub: "arn:aws:s3:::${S3ModuleLocation}/${S3ModuleNamespace}/*"
        Condition:
          StringLike:
            s3:prefix:
              - Fn::Sub: "${S3ModuleNamespace}/*"
```

### Header Comment Updates

**Format**:
```yaml
# Parent template must define parameters:
#   [existing parameters],
#   S3ModuleLocation, S3ModuleNamespace
```

**Placement**:
- Top of file, before resource definition
- After existing parameter list
- Maintain alphabetical order (optional but preferred)


### Consistency Checklist

Before committing changes, verify:

- [ ] All three module files have identical S3ModuleBucketReadOnly statement structure
- [ ] Sid is exactly `S3ModuleBucketReadOnly` in all three files
- [ ] Action list order is identical: GetObject, GetObjectVersion, ListBucket
- [ ] Resource ARN format uses Fn::Sub with same parameter references
- [ ] Condition structure is identical across files
- [ ] Header comments updated to include S3ModuleLocation and S3ModuleNamespace
- [ ] YAML indentation is consistent (6 spaces for statement level)
- [ ] Long-form intrinsic functions used (Fn::Sub, not !Sub)
- [ ] No trailing whitespace or extra blank lines
- [ ] File endings have newline character

### Validation Commands

**CloudFormation Linting**:
```bash
cfn-lint templates/v2/modules/management-roles/pipeline-mgmt-role.yml
cfn-lint templates/v2/modules/management-roles/storage-mgmt-role.yml
cfn-lint templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml
```

**Expected Output**: No errors (exit code 0)

**YAML Validation**:
```bash
yamllint templates/v2/modules/management-roles/pipeline-mgmt-role.yml
yamllint templates/v2/modules/management-roles/storage-mgmt-role.yml
yamllint templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml
```

**Expected Output**: No syntax errors


## Alternative Approaches Considered

### Alternative 1: Wildcard S3 Access

**Approach**: Grant `s3:*` on all resources

```yaml
- Sid: S3FullAccess
  Effect: Allow
  Action: s3:*
  Resource: "*"
```

**Rejected Because**:
- Violates principle of least privilege
- Grants write permissions (PutObject, DeleteObject) unnecessarily
- Allows access to all S3 buckets, not scoped to module bucket
- Security risk: Management roles could modify or delete any S3 data

### Alternative 2: No Condition on ListBucket

**Approach**: Allow ListBucket without prefix condition

```yaml
- Sid: S3ModuleBucketReadOnly
  Effect: Allow
  Action:
    - s3:GetObject
    - s3:ListBucket
  Resource:
    - Fn::Sub: "arn:aws:s3:::${S3ModuleLocation}"
    - Fn::Sub: "arn:aws:s3:::${S3ModuleLocation}/*"
```

**Rejected Because**:
- Allows enumeration of entire bucket contents
- Could expose presence of other namespaces or sensitive file names
- Condition-based filtering provides better isolation


### Alternative 3: Separate Managed Policy for S3 Access

**Approach**: Create a new managed policy containing only S3 permissions, attach to all roles

**Advantages**:
- Single source of truth for S3 permissions
- Easier to update (change one policy affects all roles)
- Clearer separation of concerns

**Rejected Because**:
- Adds complexity (additional CloudFormation resource)
- Increases policy count per role (approaching AWS limits)
- Current approach is simpler and sufficient
- Inline/managed policy already exist for each role type
- Adding statement to existing policies is more maintainable

### Alternative 4: Resource-Based S3 Bucket Policy

**Approach**: Instead of adding IAM permissions to roles, add bucket policy allowing role access

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowManagementRoles",
    "Effect": "Allow",
    "Principal": {
      "AWS": [
        "arn:aws:iam::ACCOUNT:role/PATH/ROLE1",
        "arn:aws:iam::ACCOUNT:role/PATH/ROLE2"
      ]
    },
    "Action": ["s3:GetObject", "s3:ListBucket"],
    "Resource": ["arn:aws:s3:::bucket/*", "arn:aws:s3:::bucket"]
  }]
}
```

**Rejected Because**:
- Requires managing S3 bucket policy in addition to IAM policies
- Bucket may be shared across accounts/teams (can't modify bucket policy)
- IAM role-based permissions are more portable and maintainable
- Bucket policy approach doesn't scale well (hard-coded role ARNs)


### Alternative 5: Pre-signed URLs for Modules

**Approach**: Generate pre-signed S3 URLs for modules, embed in AWS::Include

```yaml
Fn::Transform:
  Name: AWS::Include
  Parameters:
    Location: "https://bucket.s3.amazonaws.com/module.yml?signature=..."
```

**Rejected Because**:
- Pre-signed URLs expire (requires frequent regeneration)
- Complex to manage (URL generation, template updates)
- Doesn't scale to multiple modules (each needs pre-signed URL)
- IAM permission approach is simpler and more maintainable
- CloudFormation doesn't easily support dynamic URL generation

### Selected Approach Justification

The selected approach (adding IAM policy statement) is optimal because:

1. **Security**: Read-only, scoped permissions following least privilege
2. **Simplicity**: Single statement addition to existing policies
3. **Maintainability**: Consistent structure across modules
4. **Scalability**: Works for any number of modules without changes
5. **Portability**: No dependency on external bucket policies or URL generation
6. **Namespace Isolation**: Condition-based filtering prevents cross-namespace access
7. **AWS Best Practices**: Aligns with AWS IAM and CloudFormation recommendations


## Future Considerations

### Cross-Region Module Access

**Current Design**: Scoped to single S3ModuleLocation bucket

**Future Enhancement**: Support multiple buckets for different regions

**Potential Approach**:
```yaml
- Sid: S3ModuleBucketReadOnly
  Effect: Allow
  Action:
    - s3:GetObject
    - s3:GetObjectVersion
    - s3:ListBucket
  Resource:
    - Fn::Sub: "arn:aws:s3:::${S3ModuleLocation}"
    - Fn::Sub: "arn:aws:s3:::${S3ModuleLocation}/${S3ModuleNamespace}/*"
    - Fn::Sub: "arn:aws:s3:::${S3ModuleLocationBackup}"
    - Fn::Sub: "arn:aws:s3:::${S3ModuleLocationBackup}/${S3ModuleNamespace}/*"
```

**Considerations**:
- Requires additional parameters
- May impact policy size limits
- Fallback logic would need to be in application/deployment scripts

### Module Versioning in S3

**Current Design**: References latest module version at S3 path

**Future Enhancement**: Support explicit version references

**Potential Approach**:
- Use S3 object versioning
- Reference specific versions in AWS::Include: `s3://bucket/module.yml?versionId=abc123`
- GetObjectVersion permission (already included) enables this

**Benefits**:
- Reproducible deployments (specific module versions)
- Rollback capability (reference previous module version)
- Version pinning for production stability


### Audit Logging

**Current Design**: Relies on CloudTrail for S3 access logging

**Future Enhancement**: Explicit CloudWatch Logs integration

**Potential Approach**:
- Enable S3 server access logging for module bucket
- Configure CloudWatch Logs for CloudTrail S3 events
- Create metric filters for module access patterns

**Use Cases**:
- Audit which management roles accessed which modules
- Detect unusual access patterns (security monitoring)
- Track module usage for deprecation decisions

### Namespace-Level Permissions Boundary

**Current Design**: Single namespace parameter for all management roles

**Future Enhancement**: Different namespaces per management role type

**Potential Approach**:
```yaml
Parameters:
  PipelineModuleNamespace:
    Type: String
    Default: "atlantis/pipeline"
  
  StorageModuleNamespace:
    Type: String
    Default: "atlantis/storage"
```

**Benefits**:
- Finer-grained access control
- Separate module repositories per role type
- Team-specific module namespaces

**Challenges**:
- Increased parameter count
- More complex parent template
- May exceed parameter limits


### Module Signature Verification

**Current Design**: Trust-based (assumes modules in S3 are authentic)

**Future Enhancement**: Cryptographic signature verification

**Potential Approach**:
- Sign module files with private key
- Store signatures in S3 alongside modules
- Add verification step in deployment process (outside CloudFormation)

**Security Benefits**:
- Prevents tampering with modules in transit or at rest
- Ensures modules come from trusted source
- Meets compliance requirements for signed infrastructure code

**Implementation Challenges**:
- CloudFormation AWS::Include doesn't support signature verification
- Would require pre-processing step before stack deployment
- Adds complexity to deployment workflow

**Alternative**: Use S3 object lock and bucket versioning to ensure immutability


## Summary

This design adds read-only S3 access permissions to three management role modules, enabling CloudFormation's AWS::Include transform to resolve module snippets during stack deployments. The implementation follows the principle of least privilege by:

- Granting only read actions (GetObject, GetObjectVersion, ListBucket)
- Scoping access to a specific S3 bucket (S3ModuleLocation parameter)
- Restricting access to objects within a namespace path (S3ModuleNamespace parameter)
- Using conditions to filter ListBucket operations to the namespace

The change is non-breaking and backward compatible:
- Adds permissions without removing existing functionality
- No parameter changes required for existing stacks
- Qualifies as a PATCH version increment
- All existing security boundaries and trust relationships remain unchanged

Three module files require updates:
1. **pipeline-mgmt-role.yml** - Add inline policy statement
2. **storage-mgmt-role.yml** - Add inline policy statement
3. **network-cloudfront-mgmt-policy.yml** - Add managed policy statement (inherited by two network management roles)

Testing strategy includes template validation with cfn-lint, deployment verification, integration testing with AWS::Include, permission verification, and backward compatibility testing.

Rollback is straightforward via git revert (pre-deployment) or CloudFormation stack update with previous module versions (post-deployment).

