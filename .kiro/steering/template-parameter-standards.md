---
inclusion: fileMatch
fileMatchPattern: '**/{template,cfn}*.{yml,yaml}'
---

# CloudFormation Template Parameter Standards

## Overview

This document defines standard parameter names, formats, and definitions used across all CloudFormation templates in this repository. Following these standards ensures:

1. **Consistency**: Users have a predictable experience across all templates
2. **Maintainability**: Templates are easier to understand and modify
3. **Interoperability**: Templates can work together seamlessly
4. **Documentation**: Parameter purposes and constraints are clear

### Scope

These standards apply to:
- All CloudFormation templates in `templates/v2/`
- Template documentation in `docs/templates/v2/`
- Spec-driven development workflows
- AI-assisted template creation and modification

### When to Use These Standards

- **Creating new templates**: Use standard parameters with exact definitions
- **Modifying existing templates**: Align parameters with standards when possible
- **Cross-stack references**: Use standard parameter names for consistency
- **Documentation**: Reference this document for parameter descriptions

## Standard Parameters

### Prefix

**Purpose**: Namespace identifier for resource ownership and access control

**Metadata Group**: "Application Resource Naming"

**Definition**:
```yaml
Prefix:
  Type: String
  Description: Prefix pre-pended to all resources. This can be thought of as a
    Name Space used to identify ownership/access for teams, departments, etc.
    For example, resources named ws-* could belong to the web service team and
    could have IAM permissions to allow access to other ws-* resources. The
    Prefix must have a corresponding CloudFormation Service Role. Short,
    descriptive 2-6 character values work best. Due to resource naming length
    restrictions, length of Prefix + Project ID should not exceed 28
    characters. Resources are named
    <Prefix>-<ProjectId>-<StageId>-<ResourceId>
  Default: acme
  AllowedPattern: "^[a-z][a-z0-9-]{0,6}[a-z0-9]$"
  MinLength: 2
  MaxLength: 8
  ConstraintDescription: 2 to 8 characters. Lower case alphanumeric and dashes.
    Must start with a letter and end with a letter or number. Length of Prefix
    + Project ID should not exceed 28 characters.
```

**Usage Notes**:
- Typically 2-6 characters for optimal resource naming
- Must correspond to a CloudFormation Service Role
- Used for IAM permission boundaries and resource access control
- Combined length of Prefix + ProjectId should not exceed 28 characters

**Examples**: `ws`, `acme`, `devops`, `api`

---

### ProjectId

**Purpose**: Project or application identifier

**Metadata Group**: "Application Resource Naming"

**Definition**:
```yaml
ProjectId:
  Type: String
  Description: This is the Project or Application Identifier. If you receive 'S3
    bucket name too long' errors during stack creation, then you must shorten
    the Project ID or use an S3 Org Prefix. Due to resource naming length
    restrictions, length of Prefix + Project ID should not exceed 28
    characters. Resources are named
    <Prefix>-<ProjectId>-<StageId>-<ResourceId>
  AllowedPattern: "^[a-z][a-z0-9-]{0,24}[a-z0-9]$"
  MinLength: 2
  MaxLength: 26
  ConstraintDescription: Minimum of 2 characters (suggested maximum of 20). Lower
    case alphanumeric and dashes. Must start with a letter and end with a
    letter or number. Length of Prefix + Project ID should not exceed 28
    characters.
```

**Usage Notes**:
- Suggested maximum of 20 characters for optimal resource naming
- Combined length of Prefix + ProjectId should not exceed 28 characters
- If S3 bucket names are too long, use S3BucketNameOrgPrefix parameter
- Identifies the specific project or application within the namespace

**Examples**: `website`, `api`, `data-pipeline`, `user-service`

---

### StageId

**Purpose**: Deployment stage or branch alias

**Metadata Group**: "Application Resource Naming"

**Definition**:
```yaml
StageId:
  Type: String
  Description: This is an alias for the branch. It does not need to match
    CodeCommitBranch or DeployEnvironment. Due to resource naming restrictions
    you can use this to provide shorter names without special characters that
    are allowed in branch names. For example if you have a 'test/feature-98'
    branch, you could use 'tf98' as the StageId. Resources are named
    <Prefix>-<ProjectId>-<StageId>-<ResourceId>
  AllowedPattern: "^[a-z][a-z0-9-]{0,6}[a-z0-9]$"
  MinLength: 2
  MaxLength: 8
  ConstraintDescription: 2 to 8 characters. Lower case alphanumeric and dashes.
    Must start with a letter and end with a letter or number.
```

**Usage Notes**:
- Does not need to match branch name or DeployEnvironment
- Use short aliases for branches with special characters or long names
- Allows multiple stages within the same DeployEnvironment
- Examples: 'test' and 't98' could both be in TEST environment

**Examples**: `dev`, `test`, `prod`, `beta`, `tf98`

---

### S3LogBucketName

**Purpose**: S3 bucket name for service logging (CloudFront, ALB, etc.)

**Metadata Group**: "Supporting Resources"

**Definition**:
```yaml
S3LogBucketName:
  Type: String
  Description: The name of the S3 bucket used for CloudFront logging. Leave empty to disable logging. Must be a valid S3 bucket name (without .s3.amazonaws.com suffix).
  Default: ""
  AllowedPattern: "^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$|^$"
  ConstraintDescription: Must be a valid S3 bucket name or empty. Must be between 3 and 63 characters long. Lower case alphanumeric and dashes. Must start and end with a letter or number.
```

**Usage Notes**:
- Empty string disables logging (default)
- Bucket must exist before stack deployment
- Bucket must have appropriate policy to allow service to write logs
- Do not include `.s3.amazonaws.com` suffix
- Used for optional logging configuration

**Examples**: `acme-logs`, `cloudfront-logs-prod`, `my-log-bucket`

---

### S3BucketNameOrgPrefix

**Purpose**: Organization prefix for S3 bucket naming to avoid length limits

**Metadata Group**: "Application Resource Naming"

**Definition**:
```yaml
S3BucketNameOrgPrefix:
  Type: String
  Description: "By default, to enforce uniqueness, buckets include account and region in the bucket name. However, due to character limits, you can specify your own S3 prefix (like an org code). This will be used in addition to the Prefix entered above. Note that this length is shared with the recommended length of 20 characters for Resource Identifiers. So if you have a 10 character S3BucketNameOrgPrefix, you are limited to 10 characters for your bucket name identifier in your templates. Buckets are named <Prefix>-<Region>-<AccountId>-<ProjectId>-<StageId>-<ResourceId> or <S3OrgPrefix>-<Prefix>-<ProjectId>-<StageId>-<ResourceId>"
  Default: ""
  AllowedPattern: "^[a-z0-9][a-z0-9-]{0,18}[a-z0-9]$|^$"
  ConstraintDescription: "May be empty or 2 to 20 characters (8 or less recommended). Lower case alphanumeric and dashes. Must start and end with a letter or number."
```

**Usage Notes**:
- Empty string uses default naming: `<Prefix>-<Region>-<AccountId>-<ProjectId>-<StageId>-<ResourceId>`
- Non-empty uses: `<S3OrgPrefix>-<Prefix>-<ProjectId>-<StageId>-<ResourceId>`
- Recommended 8 characters or less
- Length is shared with resource identifier length (total 20 characters recommended)
- Use when default bucket names exceed S3's 63-character limit

**Examples**: `acme`, `myorg`, `company`

---

### DeployEnvironment

**Purpose**: Deployment environment classification for conditional logic

**Metadata Group**: "Deployment Environment"

**Definition**:
```yaml
DeployEnvironment:
  Type: String
  Description: "What deploy/testing environment will this run under? An environment can contain multiple stages (for example 'test' and 't98' would be in 'TEST' environment, and 'beta' and 'prod' stages would deploy to 'PROD'). Utilize this environment variable to determine your tests, app logging levels, and conditionals in the template. For example, PROD will use gradual deployment while DEV and TEST is AllAtOnce. Other resources, such as dashboards and alarms  (which cost money) could be created in PROD and not DEV or TEST. Suggested use: DEV for local SAM deployment, TEST for test/QA deployments, PROD for stage, beta, and main/prod deployments."
  Default: "PROD"
  AllowedValues: ["DEV", "TEST", "PROD"]
  ConstraintDescription: "Must specify DEV, TEST, or PROD."
```

**Usage Notes**:
- Used for conditional resource creation and configuration
- Multiple stages can exist within one environment
- DEV: Local development and SAM deployments
- TEST: Test and QA deployments
- PROD: Production, staging, and beta deployments
- Affects deployment strategies, logging levels, and resource creation

**Examples**: `DEV`, `TEST`, `PROD`

## Parameter Groups

### Standard Metadata Parameter Groups

CloudFormation templates should organize parameters into logical groups using the `AWS::CloudFormation::Interface` metadata. Use these standard group labels:

#### Application Resource Naming

**Label**: `"Application Resource Naming"` or `"Resource Naming"`

**Parameters**:
- Prefix
- ProjectId
- StageId
- S3BucketNameOrgPrefix
- RolePath (if applicable)
- PermissionsBoundaryArn (if applicable)

**Purpose**: Groups parameters that control resource naming and organization

---

#### Deployment Environment

**Label**: `"Deployment Environment"` or `"Deployment Environment Information"`

**Parameters**:
- DeployEnvironment

**Purpose**: Groups parameters that identify the deployment environment

---

#### Supporting Resources

**Label**: `"Supporting Resources"` or `"External Resources"`

**Parameters**:
- S3LogBucketName
- S3ArtifactsBucket (if applicable)
- Other references to existing resources

**Purpose**: Groups parameters that reference external or supporting resources

---

### Parameter Group Ordering

Recommended order for parameter groups in Metadata section:

1. Application Resource Naming
2. Deployment Environment
3. Supporting Resources
4. Feature-specific groups (e.g., "Routing for CloudFront", "API Gateway Configuration")

## Validation Patterns

### Reusable Regex Patterns

These patterns are used across standard parameters:

#### Lowercase Alphanumeric with Dashes (Letter Start/End)

**Pattern**: `^[a-z][a-z0-9-]{0,N}[a-z0-9]$`

**Used By**: Prefix, ProjectId, StageId

**Rules**:
- Must start with a lowercase letter
- May contain lowercase letters, numbers, and dashes
- Must end with a lowercase letter or number
- Length controlled by `{0,N}` where N = MaxLength - 2

**Examples**: `acme`, `my-app`, `test-123`

---

#### S3 Bucket Name Pattern

**Pattern**: `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$|^$`

**Used By**: S3LogBucketName, S3BucketNameOrgPrefix (with different length)

**Rules**:
- Must start with a lowercase letter or number
- May contain lowercase letters, numbers, and dashes
- Must end with a lowercase letter or number
- Length: 3-63 characters total
- Empty string allowed (indicated by `|^$`)

**Examples**: `my-bucket`, `logs-123`, `acme-data-prod`

---

#### IAM Path Pattern

**Pattern**: `^\\/([a-zA-Z0-9-_]+[\\/])+$|^\\/$`

**Used By**: RolePath

**Rules**:
- Must begin and end with forward slash
- May contain alphanumeric characters, dashes, underscores, and forward slashes
- Root path `/` is allowed

**Examples**: `/`, `/app_role/`, `/ws-hello-world-test/`

## Usage Guidelines

### When Creating New Templates

1. **Use Standard Parameters**: Include standard parameters with exact definitions from this document
2. **Follow Metadata Groups**: Organize parameters using standard group labels
3. **Maintain Consistency**: Use the same descriptions and constraints
4. **Document Deviations**: If you must deviate, document why in template comments

### When Modifying Existing Templates

1. **Align with Standards**: Update parameter definitions to match standards when possible
2. **Preserve Compatibility**: Don't change parameter names or types in existing templates
3. **Add Missing Parameters**: Add standard parameters if they're missing and needed
4. **Update Metadata**: Ensure parameters are in correct metadata groups

### When Using Spec-Driven Development

1. **Reference This Document**: Specs should reference standard parameter definitions
2. **Validate Consistency**: Ensure new parameters follow standards
3. **Update Documentation**: Template documentation should reflect standard parameters
4. **Test Compatibility**: Verify parameters work with related templates

### Cross-Stack References

When templates need to reference each other:

1. **Use Standard Names**: Rely on standard parameter names for predictability
2. **Export Consistently**: Use consistent export naming: `${PrefixUpper}-[Service]-[Resource]-[Attribute]`
3. **Document Dependencies**: Clearly document which templates work together
4. **Test Integration**: Verify templates integrate correctly

## Examples

### Example 1: Minimal Template Parameters

```yaml
Parameters:
  Prefix:
    Type: String
    Description: Prefix pre-pended to all resources...
    Default: acme
    AllowedPattern: "^[a-z][a-z0-9-]{0,6}[a-z0-9]$"
    MinLength: 2
    MaxLength: 8
    ConstraintDescription: 2 to 8 characters. Lower case alphanumeric and dashes...

  ProjectId:
    Type: String
    Description: This is the Project or Application Identifier...
    AllowedPattern: "^[a-z][a-z0-9-]{0,24}[a-z0-9]$"
    MinLength: 2
    MaxLength: 26
    ConstraintDescription: Minimum of 2 characters (suggested maximum of 20)...

  StageId:
    Type: String
    Description: This is an alias for the branch...
    AllowedPattern: "^[a-z][a-z0-9-]{0,6}[a-z0-9]$"
    MinLength: 2
    MaxLength: 8
    ConstraintDescription: 2 to 8 characters. Lower case alphanumeric and dashes...
```

### Example 2: Template with Optional Logging

```yaml
Parameters:
  # Standard naming parameters...
  
  S3LogBucketName:
    Type: String
    Description: The name of the S3 bucket used for CloudFront logging...
    Default: ""
    AllowedPattern: "^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$|^$"
    ConstraintDescription: Must be a valid S3 bucket name or empty...

Conditions:
  HasLogBucket: !Not
    - !Equals
      - !Ref S3LogBucketName
      - ''
```

### Example 3: Metadata Organization

```yaml
Metadata:
  AWS::CloudFormation::Interface:
    ParameterGroups:
      - Label:
          default: "Application Resource Naming"
        Parameters:
          - Prefix
          - ProjectId
          - StageId
          - S3BucketNameOrgPrefix
      
      - Label:
          default: "Deployment Environment"
        Parameters:
          - DeployEnvironment
      
      - Label:
          default: "Supporting Resources"
        Parameters:
          - S3LogBucketName
          - S3ArtifactsBucket
```

### Example 4: Resource Naming Pattern

```yaml
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !If
        - UseS3BucketNameOrgPrefix
        - !Sub "${S3BucketNameOrgPrefix}-${Prefix}-${ProjectId}-${StageId}-data"
        - !Sub "${Prefix}-${AWS::Region}-${AWS::AccountId}-${ProjectId}-${StageId}-data"
```

## Validation Checklist

When creating or modifying templates, verify:

- [ ] Standard parameters use exact definitions from this document
- [ ] Parameter descriptions match standard descriptions
- [ ] AllowedPattern regex matches standard patterns
- [ ] MinLength and MaxLength match standards
- [ ] ConstraintDescription matches standards
- [ ] Parameters are in correct Metadata groups
- [ ] Metadata group labels match standard labels
- [ ] Parameter group ordering follows recommendations
- [ ] Template documentation references standard parameters
- [ ] Cross-stack references use standard parameter names

## Related Documents

- [Template Version Control](.kiro/steering/template-version-control.md) - Version management guidelines
- [Template Comments, Metadata, and Outputs](.kiro/steering/template-comments-meta-outputs.md) - Documentation standards
- [Documentation for End-User CFN Templates](.kiro/steering/documentation-end-user-cfn-templates.md) - Documentation structure
- [Changelog Maintenance](.kiro/steering/changelog.md) - Changelog guidelines
