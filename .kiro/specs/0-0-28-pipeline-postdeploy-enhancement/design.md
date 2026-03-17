# Design Document

## Overview

This design enhances the CloudFormation pipeline template to properly implement conditional PostDeploy stage functionality. The current implementation has several issues:

1. **Parameter naming inconsistency**: The parameter is defined as `PostDeployStageEnabled` but referenced as `EnablePostDeployStage` in metadata
2. **Missing conditional logic**: The PostDeploy stage and related resources are always created regardless of the parameter value
3. **Incomplete IAM permissions**: The PostDeployServiceRole has incorrect S3 buildspec permissions
4. **Lack of comprehensive testing**: No property-based tests validate the conditional logic and parameter validation

The design addresses these issues by implementing proper conditional resource creation, fixing parameter naming, correcting IAM permissions, and adding comprehensive property-based tests.

## Architecture

The enhanced pipeline template follows a conditional architecture pattern:

```
Parameters → Conditions → Resources → Pipeline Stages
     ↓           ↓           ↓            ↓
PostDeploy → IsPostDeploy → PostDeploy → PostDeploy
Enabled      Enabled        Resources    Stage
```

### Key Components

1. **Conditional Logic Layer**: CloudFormation conditions that control resource creation
2. **Resource Layer**: PostDeploy-specific resources (CodeBuild project, IAM roles, log groups)
3. **Pipeline Integration Layer**: Conditional inclusion of PostDeploy stage in the pipeline
4. **Testing Layer**: Property-based tests that validate conditional behavior and parameter validation

## Components and Interfaces

### Parameters

**Fixed Parameter Naming**:
- Standardize on `PostDeployStageEnabled` (current parameter name)
- Update metadata to reference correct parameter name
- Maintain backward compatibility

**Parameter Validation**:
- `PostDeployStageEnabled`: Boolean string ("true"/"false")
- `PostDeployBuildSpec`: Local path or S3 URI validation
- `PostDeployS3StaticHostBucket`: S3 bucket name validation

### Conditions

**New Condition**:
```yaml
IsPostDeployEnabled: !Equals [!Ref PostDeployStageEnabled, "true"]
```

**Enhanced Conditions**:
```yaml
HasPostDeployBuildSpecS3Location: !And 
  - !Condition IsPostDeployEnabled
  - !Not [!Equals [!Ref PostDeployBuildSpec, ""]]
  - !Equals [!Select [0, !Split [":", !Ref PostDeployBuildSpec]], "s3"]
```

### Resources

**Conditional Resources** (only created when `IsPostDeployEnabled` is true):
- `PostDeployServiceRole`: IAM role with corrected permissions
- `PostDeployProject`: CodeBuild project with proper configuration
- `PostDeployLogGroup`: CloudWatch log group with retention policy

**Pipeline Integration**:
- PostDeploy stage conditionally included in pipeline stages array
- Proper dependency management between Deploy and PostDeploy stages

## Data Models

### PostDeploy Configuration Model

```yaml
PostDeployConfig:
  enabled: boolean
  buildSpec: string (local path or S3 URI)
  s3StaticHostBucket: string (optional)
  serviceRole: IAM Role ARN
  project: CodeBuild Project
  logGroup: CloudWatch Log Group
```

### Pipeline Stage Model

```yaml
PipelineStage:
  name: "PostDeploy"
  condition: IsPostDeployEnabled
  actions:
    - name: "PackageExport"
      type: CodeBuild
      project: PostDeployProject
      inputArtifacts: [SourceArtifact]
      outputArtifacts: [PostDeployArtifact]
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Conditional Resource Creation
*For any* CloudFormation template configuration, when PostDeployStageEnabled is "true", all PostDeploy-related resources (PostDeployServiceRole, PostDeployProject, PostDeployLogGroup) should exist in the template, and when PostDeployStageEnabled is "false", none of these resources should exist in the template.
**Validates: Requirements 1.3, 1.4, 1.5**

### Property 2: Pipeline Stage Conditional Inclusion
*For any* pipeline configuration, when PostDeployStageEnabled is "true", the pipeline should contain a PostDeploy stage, and when PostDeployStageEnabled is "false", the pipeline should not contain a PostDeploy stage.
**Validates: Requirements 1.1, 1.2**

### Property 3: Parameter Naming Consistency
*For any* reference to the PostDeploy enable parameter throughout the template, the parameter name should be consistently "PostDeployStageEnabled" in all conditions, metadata, and references.
**Validates: Requirements 2.1**

### Property 4: Condition Name Consistency
*For any* PostDeploy-related conditional resource, all resources should reference the same condition name for consistency.
**Validates: Requirements 2.2**

### Property 5: BuildSpec Parameter Reference
*For any* PostDeploy CodeBuild project configuration, the BuildSpec property should correctly reference the PostDeployBuildSpec parameter.
**Validates: Requirements 2.3**

### Property 6: S3 BuildSpec IAM Permissions
*For any* PostDeploy configuration using S3 buildspec location, the PostDeployServiceRole should have appropriate S3 read permissions for the buildspec file.
**Validates: Requirements 2.4**

### Property 7: Environment Variable Configuration
*For any* PostDeploy CodeBuild project, the environment variables should include POST_DEPLOY_S3_STATIC_HOST_BUCKET when PostDeploy is enabled.
**Validates: Requirements 2.5**

### Property 8: Compute Environment Consistency
*For any* PostDeploy CodeBuild project, the compute environment configuration should match the Build stage configuration.
**Validates: Requirements 4.1**

### Property 9: S3 Permission Consistency
*For any* PostDeploy service role, the S3 permissions for artifact management should be similar to the CodeBuildServiceRole permissions.
**Validates: Requirements 4.2**

### Property 10: SSM Permission Consistency
*For any* PostDeploy service role, the SSM Parameter Store permissions should be similar to the CodeBuildServiceRole permissions.
**Validates: Requirements 4.3**

### Property 11: Core Environment Variable Consistency
*For any* PostDeploy CodeBuild project, it should receive the same core environment variables as the Build stage project.
**Validates: Requirements 4.4**

### Property 12: Log Group Configuration
*For any* PostDeploy configuration, when enabled, a dedicated CloudWatch log group should exist with proper retention policy.
**Validates: Requirements 4.5**

### Property 13: BuildSpec Path Validation
*For any* valid local buildspec file path ending with buildspec.yml or buildspec-postdeploy.yml, the parameter validation should accept it, and for invalid paths, it should reject them.
**Validates: Requirements 5.1**

### Property 14: S3 URI Validation
*For any* valid S3 URI with proper bucket and object key format, the buildspec parameter validation should accept it, and for invalid S3 URIs, it should reject them.
**Validates: Requirements 5.2**

### Property 15: Default BuildSpec Configuration
*For any* template configuration using default buildspec locations, the Build stage should use "buildspec.yml" and PostDeploy stage should use "buildspec-postdeploy.yml".
**Validates: Requirements 5.4, 5.5**

## Error Handling

### Parameter Validation Errors
- Invalid buildspec paths: CloudFormation parameter validation prevents stack creation
- Invalid S3 bucket names: Parameter constraints ensure proper format
- Invalid boolean values: AllowedValues constraint prevents invalid PostDeployStageEnabled values

### Resource Creation Errors
- Missing dependencies: Proper DependsOn attributes ensure correct creation order
- IAM permission errors: Comprehensive permission policies prevent runtime failures
- S3 access errors: Conditional IAM policies ensure proper S3 buildspec access

### Pipeline Execution Errors
- PostDeploy stage failures: Proper error propagation and notification through existing pipeline notification system
- Artifact handling: Consistent artifact naming and passing between stages

## Testing Strategy

### Property-Based Testing Approach

**Dual testing approach**:
- **Unit tests**: Verify specific examples, edge cases, and error conditions for parameter validation and resource configuration
- **Property tests**: Verify universal properties across all valid template configurations using generated inputs

**Property-based testing requirements**:
- Use pytest with Hypothesis library for Python-based CloudFormation template testing
- Configure each property test to run minimum 100 iterations for thorough validation
- Tag each property test with explicit reference to design document property
- Use format: `**Feature: pipeline-postdeploy-enhancement, Property {number}: {property_text}**`

**Unit testing coverage**:
- Specific parameter validation examples for buildspec paths and S3 URIs
- Resource naming pattern validation
- IAM permission structure verification
- Pipeline stage configuration examples

**Property testing coverage**:
- Conditional resource creation across all parameter combinations
- Parameter validation across generated valid/invalid inputs
- Resource consistency validation across different configurations
- Pipeline structure validation across enabled/disabled states

### Test Implementation Strategy

1. **Template Parsing Tests**: Load and validate CloudFormation YAML structure
2. **Parameter Validation Tests**: Property-based testing of parameter constraints
3. **Conditional Logic Tests**: Verify resource creation based on conditions
4. **Resource Structure Tests**: Validate resource configuration consistency
5. **Integration Tests**: End-to-end pipeline configuration validation

The testing approach ensures comprehensive coverage of both specific edge cases and general correctness properties, providing confidence in the template's reliability across all deployment scenarios.