# Requirements Document

## Introduction

This feature enables CloudFormation templates that use `AWS::Include` transforms to resolve module S3 bucket locations regionally via a Mapping, removing the current hard dependency on deploying in the same region as the `63klabs` bucket (us-east-2). Templates will use a regional bucket mapping by default, with an optional override parameter for custom bucket locations. The namespace (path prefix within the bucket) is extracted into its own parameter for flexibility.

## Glossary

- **Template**: A CloudFormation YAML template file in the `templates/v2/` directory that uses `AWS::Include` transforms to import reusable modules from S3.
- **Module**: A reusable CloudFormation snippet stored in S3 and imported via `Fn::Transform` with `AWS::Include`.
- **Regional_Bucket_Mapping**: A CloudFormation `Mappings` section entry that maps AWS region names to their corresponding S3 bucket names for module storage.
- **S3ModuleLocation_Parameter**: The CloudFormation parameter that allows users to override the default regional bucket with a custom S3 bucket name.
- **S3ModuleNamespace_Parameter**: The CloudFormation parameter that specifies the path prefix (namespace) within the bucket where modules are stored.
- **HasS3ModuleLocation_Condition**: A CloudFormation condition that evaluates to true when the user has provided a custom S3 bucket name override.
- **Include_Location**: The S3 URI constructed for the `AWS::Include` transform `Location` property, combining the resolved bucket name, namespace, and module path.

## Requirements

### Requirement 1: S3ModuleLocation Parameter Accepts Only Bucket Name

**User Story:** As a template deployer, I want the S3ModuleLocation parameter to accept only a bucket name (not a bucket/path combination), so that bucket resolution and namespace are handled independently.

#### Acceptance Criteria

1. THE S3ModuleLocation_Parameter SHALL have a Type of `String`.
2. THE S3ModuleLocation_Parameter SHALL have a default value of empty string (`""`).
3. THE S3ModuleLocation_Parameter SHALL have a description stating it accepts an S3 bucket name to override the default regional bucket for module snippets.
4. THE S3ModuleLocation_Parameter SHALL have an AllowedPattern of `^$|^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$` that permits either an empty string or a valid S3 bucket name (3-63 characters, lowercase alphanumeric and hyphens, starting and ending with a lowercase letter or digit).
5. THE S3ModuleLocation_Parameter SHALL have a ConstraintDescription that states the value must be empty or a valid S3 bucket name between 3 and 63 characters containing only lowercase letters, numbers, and hyphens.
6. IF the S3ModuleLocation_Parameter value contains a forward slash, THEN THE S3ModuleLocation_Parameter SHALL reject the value via the AllowedPattern constraint.
7. WHEN the S3ModuleLocation_Parameter is left empty, THE Template SHALL use the Regional_Bucket_Mapping to resolve the bucket name for the current deployment region.

### Requirement 2: S3ModuleNamespace Parameter

**User Story:** As a template deployer, I want a separate namespace parameter, so that I can control the path prefix used within the module bucket independently of the bucket name.

#### Acceptance Criteria

1. THE S3ModuleNamespace_Parameter SHALL have a Type of `String`.
2. THE S3ModuleNamespace_Parameter SHALL have a default value of `atlantis`.
3. THE S3ModuleNamespace_Parameter SHALL have a description stating it specifies the namespace prefix within the S3 bucket where modules are stored.
4. THE S3ModuleNamespace_Parameter SHALL have an AllowedPattern of `^[a-z0-9][a-z0-9\-]*(\/[a-z0-9][a-z0-9\-]*)*$` that permits one or more path segments consisting of lowercase alphanumeric characters and hyphens, separated by forward slashes, without leading or trailing slashes.
5. THE S3ModuleNamespace_Parameter SHALL have a MinLength of 1 and a MaxLength of 128.
6. THE S3ModuleNamespace_Parameter SHALL have a ConstraintDescription explaining that the value must be 1 to 128 characters, containing only lowercase alphanumeric characters, hyphens, and forward slashes, must not start or end with a slash, and each segment between slashes must start with a lowercase alphanumeric character.
7. IF the S3ModuleNamespace_Parameter value fails the AllowedPattern validation, THEN THE Template SHALL reject the stack creation with the ConstraintDescription message.

### Requirement 3: Regional Bucket Mapping

**User Story:** As a template deployer, I want the template to automatically resolve the correct S3 bucket for my deployment region, so that I can deploy templates in any supported region without manually specifying a bucket.

#### Acceptance Criteria

1. THE Template SHALL include a `Mappings` section with a mapping named `RegionalModuleBuckets` containing entries for exactly 4 regions: `us-east-1`, `us-east-2`, `us-west-1`, and `us-west-2`.
2. THE Regional_Bucket_Mapping SHALL map `us-east-1` to bucket name `63klabs-atlas-us-east-1`.
3. THE Regional_Bucket_Mapping SHALL map `us-east-2` to bucket name `63klabs-zenith-us-east-2`.
4. THE Regional_Bucket_Mapping SHALL map `us-west-1` to bucket name `63klabs-fabric-us-west-1`.
5. THE Regional_Bucket_Mapping SHALL map `us-west-2` to bucket name `63klabs-orbit-us-west-2`.
6. THE Regional_Bucket_Mapping SHALL use `BucketName` as the key for the bucket name value within each region entry.
7. IF the template is deployed in a region not present in the Regional_Bucket_Mapping, THEN THE Template SHALL fail deployment with a CloudFormation mapping lookup error when no S3ModuleLocation override is provided.

### Requirement 4: Condition for S3ModuleLocation Override

**User Story:** As a template deployer, I want the template to detect whether I have provided a custom bucket name, so that it can choose between my override and the regional default.

#### Acceptance Criteria

1. THE Template SHALL define a condition named `HasS3ModuleLocation` in the `Conditions` section.
2. THE HasS3ModuleLocation_Condition SHALL use the `!Not [!Equals [!Ref S3ModuleLocation, ""]]` intrinsic function pattern to compare the parameter value against an empty string.
3. WHEN the S3ModuleLocation_Parameter value is not an empty string, THE HasS3ModuleLocation_Condition SHALL evaluate to true.
4. WHEN the S3ModuleLocation_Parameter value is an empty string, THE HasS3ModuleLocation_Condition SHALL evaluate to false.

### Requirement 5: Include Location Resolution

**User Story:** As a template deployer, I want the AWS::Include transform locations to resolve the bucket dynamically based on the condition and mapping, so that modules load from the correct regional bucket or my custom override.

#### Acceptance Criteria

1. WHEN the HasS3ModuleLocation_Condition is true, THE Include_Location SHALL use the value of S3ModuleLocation_Parameter as the bucket name component of the S3 URI.
2. WHEN the HasS3ModuleLocation_Condition is false, THE Include_Location SHALL use the value retrieved via `!FindInMap [RegionalModuleBuckets, !Ref "AWS::Region", BucketName]` as the bucket name component of the S3 URI.
3. THE Include_Location SHALL use the S3ModuleNamespace_Parameter value as the first path segment immediately following the bucket name.
4. THE Include_Location SHALL follow the format `s3://<BucketName>/<Namespace>/templates/v2/modules/<module-path>`, where `<BucketName>` is the resolved bucket name, `<Namespace>` is the S3ModuleNamespace_Parameter value, and `<module-path>` is the relative path to the module YAML file within the `templates/v2/modules/` directory.
5. THE Include_Location SHALL be constructed using `!Sub` with a variable map containing two variables: `BucketName` resolved via `!If [HasS3ModuleLocation, !Ref S3ModuleLocation, !FindInMap [RegionalModuleBuckets, !Ref "AWS::Region", BucketName]]`, and `Namespace` resolved via `!Ref S3ModuleNamespace`.
6. WHEN a template contains multiple `AWS::Include` transforms, each Include_Location SHALL use the same `!Sub` variable map pattern for bucket and namespace resolution, differing only in the `<module-path>` segment.

### Requirement 6: All Affected Templates Updated Consistently

**User Story:** As a maintainer, I want all templates that use AWS::Include to be updated with the same regional resolution pattern, so that the module loading behavior is consistent across the platform.

#### Acceptance Criteria

1. THE Template `templates/v2/account/account-wide-infrastructure.yml` SHALL contain the S3ModuleLocation_Parameter, S3ModuleNamespace_Parameter, Regional_Bucket_Mapping, HasS3ModuleLocation_Condition, and Include_Location as defined in Requirements 1-5.
2. THE Template `templates/v2/account/prefix-based-infrastructure.yml` SHALL contain the S3ModuleLocation_Parameter, S3ModuleNamespace_Parameter, Regional_Bucket_Mapping, HasS3ModuleLocation_Condition, and Include_Location as defined in Requirements 1-5.
3. THE Template `templates/v2/service-role/template-service-role-pipeline.yml` SHALL contain the S3ModuleLocation_Parameter, S3ModuleNamespace_Parameter, Regional_Bucket_Mapping, HasS3ModuleLocation_Condition, and Include_Location as defined in Requirements 1-5.
4. THE Template `templates/v2/service-role/template-service-role-network-cloudfront.yml` SHALL contain the S3ModuleLocation_Parameter, S3ModuleNamespace_Parameter, Regional_Bucket_Mapping, HasS3ModuleLocation_Condition, and Include_Location as defined in Requirements 1-5.
5. THE Template `templates/v2/service-role/template-service-role-network-full.yml` SHALL contain the S3ModuleLocation_Parameter, S3ModuleNamespace_Parameter, Regional_Bucket_Mapping, HasS3ModuleLocation_Condition, and Include_Location as defined in Requirements 1-5.
6. THE Template `templates/v2/service-role/template-service-role-storage.yml` SHALL contain the S3ModuleLocation_Parameter, S3ModuleNamespace_Parameter, Regional_Bucket_Mapping, HasS3ModuleLocation_Condition, and Include_Location as defined in Requirements 1-5.
7. WHEN any affected template is updated, THE Template SHALL replace every existing `Fn::Transform` `AWS::Include` Location reference that uses the old `!Sub "s3://${S3ModuleLocation}/..."` format with the Include_Location format defined in Requirement 5.
8. WHEN any affected template is updated, THE Template SHALL not retain the previous S3ModuleLocation parameter definition that accepted a bucket/path combination (AllowedPattern matching `bucket/path` format).
9. WHEN any affected template is updated, THE Template SHALL use parameter definitions, mapping entries, condition logic, and Include_Location construction that are character-for-character identical across all 6 templates (excluding template-specific module paths in the Include Location URI).

### Requirement 7: Metadata Parameter Group Updated

**User Story:** As a template deployer using the CloudFormation console, I want the new S3ModuleNamespace parameter to appear alongside S3ModuleLocation in the parameter group, so that module source configuration is grouped logically.

#### Acceptance Criteria

1. THE Template Metadata `AWS::CloudFormation::Interface` ParameterGroups SHALL include a parameter group with the label "Module Source" containing exactly `S3ModuleLocation` and `S3ModuleNamespace` as its parameters.
2. THE "Module Source" parameter group SHALL list `S3ModuleLocation` as the first parameter and `S3ModuleNamespace` as the second parameter.
3. WHEN any affected template from Requirement 6 is updated, THE Template Metadata `AWS::CloudFormation::Interface` ParameterGroups SHALL include the "Module Source" parameter group with both `S3ModuleLocation` and `S3ModuleNamespace`.
