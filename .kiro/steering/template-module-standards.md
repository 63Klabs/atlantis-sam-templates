---
inclusion: fileMatch
fileMatchPattern: 'templates/v2/**/*.{yml,yaml}'
---

# CloudFormation Module Standards

## Overview

This document defines the standards for authoring reusable **modules** (snippets consumed
via `AWS::Include`) and for authoring **parent templates** that assemble those modules.

Modules are stored under `templates/v2/modules/` and are loaded at deploy time from S3
using an `Fn::Transform` / `AWS::Include` transform:

```
s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/<category>/<module-name>.yml
```

Because a module is spliced directly into the parent template at the location of the
consuming resource, a module represents the **body of a single resource**, not a complete
template.

### Scope

These standards apply to:
- All module snippet files in `templates/v2/modules/`
- All parent templates in `templates/v2/` that consume modules via `AWS::Include`

## Module File Standards

### Do NOT Include a Logical ID

A module file describes a **single resource body only**. It MUST NOT declare a logical ID
and MUST NOT be wrapped in a `Resources:` block. The logical ID is supplied by the
**parent template** at the point where the `AWS::Include` transform is placed.

A module file starts at the resource-attribute level and lists only the resource
description: `Type`, `Properties`, and any other resource-level keys (`Condition`,
`DependsOn`, `Metadata`, `DeletionPolicy`, etc.).

**Correct** (`templates/v2/modules/management-roles/pipeline-mgmt-role.yml`):

```yaml
# -- Prefix-based CloudFormation Service Role for Pipeline Management --
Type: AWS::IAM::Role
Properties:
  Path:
    Ref: ServiceRolePath
  RoleName:
    Fn::Sub: "${PrefixUpper}-CloudFormation-Service-Role-Pipeline-Management"
  # ...
```

**Incorrect** (do NOT wrap in a logical ID or `Resources:` block):

```yaml
Resources:
  PrefixBasedCloudFormationPipelineMgmtServiceRole:   # WRONG - logical ID belongs in the parent
    Type: AWS::IAM::Role
    Properties:
      # ...
```

### Long-Form Intrinsic Functions Only

`AWS::Include` does not support YAML shorthand tags. All intrinsic functions in a module
MUST use long-form syntax:

- `Fn::Sub` (not `!Sub`)
- `Ref` (not `!Ref`)
- `Fn::GetAtt: [LogicalId, Attribute]` (not `!GetAtt`)
- `Fn::If`, `Fn::Join`, `Fn::Not`, etc.

### Document the Module Contract in Comments

Because a module relies on parameters, conditions, and (sometimes) sibling logical IDs
defined by the parent, each module MUST open with a comment block that declares its
contract:

```yaml
# -- <Human-readable module title> --
# Parent template must define parameters:
#   Prefix, PrefixUpper, ..., S3ModuleLocation, S3ModuleNamespace
# Parent template must define conditions:
#   UseS3BucketNameOrgPrefix, HasPermissionsBoundaryArn, ...
# Parent must name the <role> resource '<ExpectedLogicalId>'   # if referenced via Fn::GetAtt
# NOTE: AWS::Include does not support YAML shorthand tags (!Sub, !Ref, etc.)
#       All intrinsic functions must use long-form syntax (Fn::Sub, Ref, etc.)
```

When a module references a sibling resource (for example a PassRole policy that references
its service role via `Fn::GetAtt`), the comment block MUST name the exact logical ID the
parent is required to use.

## Parent Template Standards

### Required Module Source Parameters

Any parent template that consumes one or more modules MUST declare the `S3ModuleLocation`
and `S3ModuleNamespace` parameters. These MUST use the **same** description, default,
allowed pattern, length constraints, and constraint description as defined in
`templates/v2/account/prefix-based-infrastructure.yml`:

```yaml
  S3ModuleLocation:
    Type: String
    Description: "S3 bucket name containing module snippets. Modules are loaded from s3://<S3ModuleLocation>/<S3ModuleNamespace>/templates/v2/modules/*. Bucket must be in same region as deployment. Regional buckets provided by 63klabs: 63klabs-atlas-us-east-1, 63klabs-zenith-us-east-2, 63klabs-fabric-us-west-1, 63klabs-orbit-us-west-2. Admins must supply their own bucket if deploying outside us-*"
    AllowedPattern: "^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$"
    MinLength: 3
    MaxLength: 63
    ConstraintDescription: "Must be a valid S3 bucket name between 3 and 63 characters containing only lowercase letters, numbers, and hyphens."

  S3ModuleNamespace:
    Type: String
    Description: "Namespace prefix within the S3 module bucket. This is the path prefix where modules are stored. Modules are loaded from s3://<BucketName>/<S3ModuleNamespace>/templates/v2/modules/*"
    Default: "atlantis"
    AllowedPattern: "^[a-z0-9][a-z0-9\\-]*(\\/[a-z0-9][a-z0-9\\-]*)*$"
    MinLength: 1
    MaxLength: 128
    ConstraintDescription: "Must be 1 to 128 characters containing only lowercase alphanumeric characters, hyphens, and forward slashes. Must not start or end with a slash. Each segment between slashes must start with a lowercase alphanumeric character."
```

> **Important:** `S3ModuleLocation` and `S3ModuleNamespace` are the canonical definitions.
> Do not alter the description, pattern, or constraints on a per-template basis. If the
> definition changes, update `prefix-based-infrastructure.yml` first, then propagate the
> identical definition to every consuming template.

### Metadata Grouping

Group `S3ModuleLocation` and `S3ModuleNamespace` under a `"Module Source"` label in the
`AWS::CloudFormation::Interface` metadata:

```yaml
Metadata:
  AWS::CloudFormation::Interface:
    ParameterGroups:
      # ... other groups ...
      - Label:
          default: "Module Source"
        Parameters:
          - S3ModuleLocation
          - S3ModuleNamespace
```

### Consuming a Module (Logical ID Lives Here)

The parent template declares the logical ID and uses the `AWS::Include` transform to pull
in the module body:

```yaml
Resources:

  PrefixBasedCloudFormationPipelineMgmtServiceRole:
    Fn::Transform:
      Name: AWS::Include
      Parameters:
        Location: !Sub "s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/management-roles/pipeline-mgmt-role.yml"
```

The parent template MUST also define every parameter and condition that the consumed
modules declare in their contract comment blocks, and MUST use the exact sibling logical
IDs the modules expect.

### cfn-lint Suppressions

Because `AWS::Include` content is not visible to cfn-lint, parent templates that consume
modules typically need to suppress the following checks (add only those that apply):

```yaml
Metadata:
  cfn-lint:
    config:
      ignore_checks:
        - E6101 # Resources from AWS::Include modules are not visible to cfn-lint
        - W2001 # Parameters consumed by AWS::Include modules appear unused
        - W8001 # Conditions consumed by AWS::Include modules appear unused
```

## Validation Checklist

### Module Files

- [ ] No logical ID and no `Resources:` wrapper — resource description only
- [ ] Starts at the resource-attribute level (`Type`, `Properties`, ...)
- [ ] Opens with a comment block declaring required parent parameters and conditions
- [ ] Names any sibling logical IDs it references via `Fn::GetAtt`
- [ ] Uses long-form intrinsic functions only (no `!Sub`, `!Ref`, `!GetAtt`)

### Parent Templates

- [ ] Declares `S3ModuleLocation` and `S3ModuleNamespace` with the exact definitions from `prefix-based-infrastructure.yml`
- [ ] Groups both parameters under a `"Module Source"` metadata label
- [ ] Defines every parameter and condition required by the modules it consumes
- [ ] Uses the sibling logical IDs the modules expect
- [ ] Adds the appropriate `cfn-lint` suppressions for `AWS::Include`

## Related Documents

- [Template Parameter Standards](.kiro/steering/template-parameter-standards.md) - Standard parameter definitions
- [Template Comments, Metadata, and Outputs](.kiro/steering/template-comments-meta-outputs.md) - Documentation standards
- [Modules README](../../templates/v2/modules/README.md) - Inventory of available modules
