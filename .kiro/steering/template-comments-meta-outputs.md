# CloudFormation Template Comments, Metadata, and Outputs

## Overview

All CloudFormation templates in this repository must follow consistent standards for:
1. **Header Comments** - Template identification and documentation
2. **Section Comments** - AWS documentation links for each major section
3. **Metadata** - Parameter grouping and organization
4. **Outputs** - Resource references and cross-stack values

These standards ensure templates are self-documenting, user-friendly, and maintainable.

## Header Comments Section

### Required Elements

Every template MUST include a header comment section at the top with the following elements:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31  # If using SAM
Description: "Brief description of what this template does"

# Atlantis Template for AWS SAM Deployments
# [Category] Infrastructure Template (e.g., Pipeline, Storage, Network, Service Role)
# Author: Chad Kluck - 63klabs.net
# Version: vMAJOR.MINOR.PATCH/YYYY-MM-DD

# Documentation, Issues/Feature Requests, Latest Updates, and Security Reports on GitHub:
# https://github.com/63klabs/atlantis-cfn-template-repo-for-serverless-deployments/

# [Detailed description of template purpose and functionality]
# [Multiple lines explaining what resources are created]
# [Prerequisites and dependencies]

# USE WITH:
# - [Related template category]: [Template name]
#   - [path/to/template.yml]
# - [Another related template]
#   - [path/to/template.yml]

# TUTORIALS:
# - [Tutorial name]: [URL]
# - [Another tutorial]: [URL]
```

### Header Comment Rules

1. **Version Format**: Must follow `vMAJOR.MINOR.PATCH/YYYY-MM-DD` format (see template-version-control.md)
2. **Description**: Keep the CloudFormation Description field brief (1-2 lines)
3. **Detailed Description**: Provide comprehensive explanation in comments below version
4. **USE WITH**: List related templates that are commonly used together
5. **TUTORIALS**: Optional section for linking to relevant tutorials or guides
6. **Existing Comments**: Do NOT update existing header comments unless specifically required by a task

### When to Update Header Comments

- **New Templates**: Always include complete header comments
- **Template Updates**: Only update version and date (see template-version-control.md)
- **Breaking Changes**: Add notes about breaking changes in the detailed description
- **Steering Document Instructions**: Update header comments when specifically instructed by another steering document (e.g., template-version-control.md requires version/date updates)
- **Specification Requirements**: Update header comments when a specification or requirement workflow explicitly requires changes to documentation links, USE WITH, TUTORIALS, or other header content
- **DO NOT**: Modify header comments arbitrarily or without explicit instruction from steering documents, specifications, or requirement workflows

## Section Comments

### Required Section Documentation

Each major CloudFormation section MUST include a comment block with:
1. Section separator (visual divider)
2. Section name
3. AWS documentation link
4. Optional: Brief description or usage notes

### Section Comment Format

```yaml
# =============================================================================
# SECTION NAME
# -----------------------------------------------------------------------------
# https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/[section-reference].html
#
# [Optional: Brief description or usage notes]
#

SectionName:
  # Section content
```

### Standard Section Comments

**Metadata Section:**
```yaml
# =============================================================================
# META DATA
# -----------------------------------------------------------------------------
# https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-cloudformation-interface.html
#

Metadata:
  AWS::CloudFormation::Interface:
```

**Parameters Section:**
```yaml
# =============================================================================
# PARAMETERS
# -----------------------------------------------------------------------------
# https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/parameters-section-structure.html
#

Parameters:
```

**Conditions Section:**
```yaml
# =============================================================================
# CONDITIONS
# -----------------------------------------------------------------------------
# https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-conditions.html
#

Conditions:
```

**Mappings Section:**
```yaml
# =============================================================================
# MAPPINGS
# -----------------------------------------------------------------------------
# https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/mappings-section-structure.html
#

Mappings:
```

**Resources Section:**
```yaml
# =============================================================================
# RESOURCES
# -----------------------------------------------------------------------------
# https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/resources-section-structure.html
#

Resources:
```

**Outputs Section:**
```yaml
# =============================================================================
# OUTPUTS
# -----------------------------------------------------------------------------
# https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/outputs-section-structure.html
#
# Place anything interesting that you would like to quickly refer to in 
# your cloudformation OUTPUT section. Test URLs, direct links to resources, etc
#

Outputs:
```

### Subsection Comments

Within major sections, use subsection comments to organize related resources:

```yaml
  # ---------------------------------------------------------------------------
  # Subsection Name (e.g., Application Resource Naming, Supporting Resources)

  ResourceName:
    Type: AWS::Service::Resource
```

### When to Add Section Comments

- **New Templates**: Always include all section comments
- **Template Updates**: Add missing section comments if the section doesn't have them
- **Existing Comments**: Do NOT modify existing section comments

## Metadata Section

### Purpose

The Metadata section organizes parameters into logical groups for the CloudFormation console, making it easier for users to understand and fill out parameters.

### Required for All Templates

Every template MUST include a `Metadata` section with `AWS::CloudFormation::Interface` that groups parameters logically.

### Metadata Structure

```yaml
Metadata:
  AWS::CloudFormation::Interface:
    ParameterGroups:
      - Label:
          default: "Group Name"
        Parameters:
          - Parameter1
          - Parameter2
          - Parameter3
      - Label:
          default: "Another Group Name"
        Parameters:
          - Parameter4
          - Parameter5
```

### Standard Parameter Groups

Organize parameters into logical groups. Common groups include:

1. **Application Resource Naming** / **Resource Naming**
   - Prefix, ProjectId, StageId
   - S3BucketNameOrgPrefix, RolePath
   - PermissionsBoundaryArn

2. **Deployment Environment** / **Deployment Environment Information**
   - DeployEnvironment
   - Environment-specific settings

3. **Supporting Resources** / **External Resources**
   - References to existing resources (S3 buckets, ARNs, etc.)
   - Dependencies on other stacks

4. **Feature-Specific Groups**
   - Group parameters by feature or functionality
   - Examples: "Routing for CloudFront", "API Gateway Configuration", "Logging Configuration"

### Metadata Best Practices

1. **Logical Grouping**: Group related parameters together
2. **Consistent Naming**: Use consistent group names across templates
3. **Order Matters**: List groups in the order users should fill them out
4. **All Parameters**: Every parameter must be listed in a group
5. **Clear Labels**: Use descriptive, user-friendly group labels

## Outputs Section

### Purpose

The Outputs section provides:
1. **Quick Reference Links**: Direct links to AWS console resources
2. **Cross-Stack Values**: Values needed by other stacks
3. **Copy-Paste Values**: Values users need to copy into other stack parameters
4. **Verification Info**: Confirmation of what was created

### Required for All Templates

Every template MUST include an Outputs section with relevant resource information.

### Output Types

#### 1. Console Links (Quick Reference)

Provide direct links to AWS console for easy access to resources:

```yaml
Outputs:
  DynamoDbWebConsole:
    Description: "DynamoDb Table Web Console"
    Value: !Sub "https://console.aws.amazon.com/dynamodbv2/home?region=${AWS::Region}#table?name=${TableName}"

  LambdaFunctionConsole:
    Description: "Lambda Function in AWS Console"
    Value: !Sub "https://console.aws.amazon.com/lambda/home?region=${AWS::Region}#/functions/${FunctionName}"

  CloudWatchLogsConsole:
    Description: "CloudWatch Logs for Lambda Function"
    Value: !Sub "https://console.aws.amazon.com/cloudwatch/home?region=${AWS::Region}#logsV2:log-groups/log-group/${LogGroupName}"
```

#### 2. Resource Identifiers

Output resource names, ARNs, and domains that users need to reference:

```yaml
Outputs:
  BucketName:
    Description: "The S3 Bucket Name"
    Value: !Ref BucketName

  BucketArn:
    Description: "The S3 Bucket ARN"
    Value: !GetAtt Bucket.Arn

  OriginBucketDomainForCloudFront:
    Description: "Domain to use for CloudFront S3 Origin"
    Value: !GetAtt Bucket.DomainName

  FunctionArn:
    Description: "Lambda Function ARN"
    Value: !GetAtt Function.Arn
```

#### 3. Cross-Stack References (Exports)

Use exports for values that need to be shared across multiple stacks in the account:

```yaml
Outputs:
  ServiceRoleArn:
    Description: "The ARN of the CloudFormation Service Role"
    Value: !GetAtt ServiceRole.Arn
    Export:
      Name: !Sub "${PrefixUpper}-CloudFormation-Service-Role-Arn"

  ManagedPolicyArn:
    Description: "The ARN of the Managed Policy"
    Value: !Ref ManagedPolicy
    Export:
      Name: !Sub "${PrefixUpper}-Managed-Policy-Arn"
```

#### 4. Configuration Values

Output configuration details that help users understand what was created:

```yaml
Outputs:
  AllowedCloudFrontAndCodeBuild:
    Description: "Access to bucket is restricted to CloudFront (Read) and CodeBuild (CRUD) with the following atlantis:Application tag value"
    Value: !Sub "${Prefix}-${ProjectId}"

  InvalidationEventsEnabled:
    Description: "Indicates whether S3 event notifications for cache invalidation are enabled"
    Value: !If [HasInvalidatorArn, "true", "false"]
```

### When to Use Exports

**Use Exports When:**
- The value is needed by multiple stacks across the account
- The resource is shared infrastructure (service roles, shared S3 buckets, shared DynamoDB tables)
- The value is account-wide or prefix-wide (not project-specific)
- The stack provides foundational resources used by many projects

**Do NOT Use Exports When:**
- The value is only needed by one other stack (use parameter passing instead)
- The resource is project-specific
- The value changes frequently
- You want flexibility to delete the stack (exports prevent deletion if referenced)

**Export Naming Convention:**
```yaml
Export:
  Name: !Sub "${PrefixUpper}-[Service]-[Resource]-[Attribute]"
  # Examples:
  # WS-CloudFormation-Service-Role-Arn
  # ACME-Storage-Bucket-Name
  # DEVOPS-Managed-Policy-Arn
```

### Output Best Practices

1. **Descriptive Names**: Use clear, descriptive output names
2. **Helpful Descriptions**: Explain what the output is and how to use it
3. **Console Links**: Include direct links to AWS console for major resources
4. **Essential Values**: Output values that users will need to reference
5. **Conditional Outputs**: Use conditions for optional resources
6. **Consistent Format**: Follow consistent naming and description patterns

### Required Outputs by Template Type

**Storage Templates:**
- Bucket names
- Bucket ARNs
- Bucket domains (for CloudFront origins)
- Console links to S3 buckets

**Pipeline Templates:**
- Pipeline name
- Pipeline ARN
- Console link to CodePipeline
- Build project names/ARNs

**Network Templates:**
- Distribution IDs
- Distribution domains
- API Gateway IDs/URLs
- Route53 record names
- Console links to CloudFront, API Gateway

**Service Role Templates:**
- Role ARNs (with exports)
- Role names (with exports)
- Policy ARNs (with exports)
- Policy names (with exports)

**Lambda/Compute Templates:**
- Function names
- Function ARNs
- Console links to Lambda functions
- Console links to CloudWatch Logs
- API endpoints (if applicable)

**Database Templates:**
- Table names
- Table ARNs
- Console links to DynamoDB tables
- Stream ARNs (if enabled)

## Implementation Rules

### For New Templates

When creating a new template:
1. ✅ Include complete header comments with all required elements
2. ✅ Add section comments for all major sections
3. ✅ Include Metadata section with parameter groups
4. ✅ Include Outputs section with relevant resource information
5. ✅ Follow all formatting and naming conventions

### For Template Updates

When updating an existing template:
1. ✅ Update version and date in header (see template-version-control.md)
2. ✅ Add missing section comments if sections don't have them
3. ✅ Add Metadata section if template doesn't have one
4. ✅ Add or update Outputs section with new resources
5. ✅ Update header comments when explicitly instructed by steering documents, specifications, or requirement workflows
6. ❌ Do NOT modify existing header comments arbitrarily (only when explicitly required)
7. ❌ Do NOT modify existing section comments

### For Spec-Driven Development

When implementing templates via specs:
1. First task should handle version increment (if PATCH > 0)
2. Ensure all new templates include complete comments, metadata, and outputs
3. When updating templates, add missing comments/metadata/outputs
4. Document any new outputs in the template documentation
5. Update CHANGELOG.md with significant changes

## Validation Checklist

Before completing a template task, verify:

- [ ] Header comments include version, description, USE WITH, and GitHub link
- [ ] All major sections have comment blocks with AWS documentation links
- [ ] Metadata section exists with logical parameter groups
- [ ] All parameters are listed in a parameter group
- [ ] Outputs section exists with relevant resource information
- [ ] Console links are provided for major resources
- [ ] Cross-stack values are outputted (with exports if appropriate)
- [ ] Output descriptions are clear and helpful
- [ ] Conditional outputs use conditions appropriately

## Examples

See existing templates for examples:
- `templates/v2/network/template-network-route53-cloudfront-s3-apigw.yml` - Comprehensive example
- `templates/v2/storage/template-storage-s3-oac-for-cloudfront.yml` - Storage example with outputs
- `templates/v2/service-role/template-service-role-pipeline.yml` - Service role with exports
- `templates/v2/pipeline/template-pipeline.yml` - Pipeline with console links