# Requirements Document

## Introduction

This feature creates account-wide S3 artifacts bucket modules for the `account-wide-infrastructure.yml` template. The modules are inspired by `template-storage-s3-artifacts.yml` but designed for account-level use with less restrictive permissions. The existing `template-storage-s3-artifacts.yml` remains unchanged — it serves a different purpose (per-project, prefix-scoped, restrictive permissions). The new account-wide modules provide a shared artifacts bucket accessible by ALL pipeline roles in the account regardless of prefix.

## Glossary

- **Module**: A YAML snippet file stored in S3 that defines a single CloudFormation resource, referenced via `Fn::Transform: AWS::Include` in parent templates. Starts with `Type:` at the top level (no wrapping resource logical name).
- **Account_Wide_Infrastructure_Template**: The template at `templates/v2/account/account-wide-infrastructure.yml` that deploys shared, account-level resources assembled from reusable modules
- **S3_Artifacts_Bucket_Module**: The new account-wide module snippet defining the `AWS::S3::Bucket` resource for shared pipeline artifacts, stored in `templates/v2/modules/account-wide/`
- **S3_Artifacts_Policy_Module**: The new account-wide module snippet defining the `AWS::S3::BucketPolicy` resource for the shared artifacts bucket, stored in `templates/v2/modules/account-wide/`
- **Storage_Template**: The existing template at `templates/v2/storage/template-storage-s3-artifacts.yml` that deploys a per-project, prefix-scoped S3 artifacts bucket (NOT modified by this feature)
- **OrgPrefix**: The organization-level prefix parameter used in the Account_Wide_Infrastructure_Template (uppercase, e.g., "ACME")
- **S3BucketNameOrgPrefix**: An optional lowercase organization prefix for S3 bucket naming to avoid length limits
- **RolePath**: The IAM path used for service roles referenced in bucket policy principals
- **S3ModuleLocation**: The S3 bucket name where module snippets are stored
- **S3ModuleNamespace**: The namespace path prefix within the S3 module bucket

## Requirements

### Requirement 1: Create Account-Wide S3 Artifacts Bucket Module

**User Story:** As a platform maintainer, I want an account-wide S3 artifacts bucket module, so that a shared artifacts bucket can be provisioned at the account level without per-project or prefix scoping.

#### Acceptance Criteria

1. THE S3_Artifacts_Bucket_Module SHALL define a single `AWS::S3::Bucket` resource starting with `Type: AWS::S3::Bucket` at the top level (no wrapping resource logical name), following the same structure as the existing `apigw-cloudwatch-role.yml` module pattern
2. THE S3_Artifacts_Bucket_Module SHALL be stored at the path `templates/v2/modules/account-wide/s3-artifacts-bucket.yml`
3. THE S3_Artifacts_Bucket_Module SHALL include a header comment documenting the parent template prerequisites: parameters (`S3BucketNameOrgPrefix`, `S3LogBucketName`) and conditions (`UseS3BucketNameOrgPrefix`, `HasLoggingBucket`, `EnableS3ArtifactsBucket`)
4. THE S3_Artifacts_Bucket_Module SHALL include `Condition: EnableS3ArtifactsBucket` at the resource level to support conditional creation
5. THE S3_Artifacts_Bucket_Module SHALL construct the bucket name using `Fn::If` and `Fn::Sub`: when `UseS3BucketNameOrgPrefix` is true, the name SHALL be `${S3BucketNameOrgPrefix}-cf-artifacts-${AWS::AccountId}-${AWS::Region}-an`; when false, the name SHALL be `cf-artifacts-${AWS::AccountId}-${AWS::Region}-an`
6. THE S3_Artifacts_Bucket_Module SHALL NOT use `Prefix` or `ProjectId` parameters in the bucket name construction because the bucket is account-wide
7. THE S3_Artifacts_Bucket_Module SHALL include `DeletionPolicy: Retain` to preserve artifacts for rollback and audit purposes if the stack is accidentally deleted
8. THE S3_Artifacts_Bucket_Module SHALL include `VersioningConfiguration` with Status Enabled
9. THE S3_Artifacts_Bucket_Module SHALL include `PublicAccessBlockConfiguration` with all four blocks set to true (BlockPublicAcls, BlockPublicPolicy, IgnorePublicAcls, RestrictPublicBuckets)
10. THE S3_Artifacts_Bucket_Module SHALL include `BucketEncryption` with AES256 server-side encryption
11. THE S3_Artifacts_Bucket_Module SHALL include `LifecycleConfiguration` with a rule that expires objects after 395 days (slightly over 1 year, aligning with CodePipeline's artifact retention), expires noncurrent versions after 30 days, and aborts incomplete multipart uploads after 1 day
12. THE S3_Artifacts_Bucket_Module SHALL include conditional `LoggingConfiguration` guarded by the `HasLoggingBucket` condition, using `S3LogBucketName` as the destination bucket

### Requirement 2: Create Account-Wide S3 Artifacts Bucket Policy Module

**User Story:** As a platform maintainer, I want an account-wide S3 artifacts bucket policy module with less restrictive permissions than the storage template, so that ALL pipeline service roles in the account can access the shared artifacts bucket regardless of prefix.

#### Acceptance Criteria

1. THE S3_Artifacts_Policy_Module SHALL define a single `AWS::S3::BucketPolicy` resource starting with `Type: AWS::S3::BucketPolicy` at the top level (no wrapping resource logical name), following the same structure as existing modules
2. THE S3_Artifacts_Policy_Module SHALL be stored at the path `templates/v2/modules/account-wide/s3-artifacts-bucket-policy.yml`
3. THE S3_Artifacts_Policy_Module SHALL include a header comment documenting the parent template prerequisites: required parameters (`RolePath`), required conditions (`EnableS3ArtifactsBucket`), required pseudo-parameters (`AWS::AccountId`), and the logical name of the bucket resource it references (`S3ArtifactsBucketRegional`)
4. THE S3_Artifacts_Policy_Module SHALL include `Condition: EnableS3ArtifactsBucket` at the resource level to support conditional creation
5. THE S3_Artifacts_Policy_Module SHALL reference the bucket resource using long-form intrinsic function syntax (`Ref: S3ArtifactsBucketRegional` and `Fn::GetAtt: [S3ArtifactsBucketRegional, Arn]`) because `AWS::Include` does not support YAML shorthand tags
6. THE S3_Artifacts_Policy_Module SHALL include a `DenyNonSecureTransportAccess` statement that denies all S3 actions when `aws:SecureTransport` is false, applying to both the bucket ARN and all objects within it
7. THE S3_Artifacts_Policy_Module SHALL include a `WhitelistedGet` statement that allows `s3:GetObject`, `s3:GetObjectVersion`, and `s3:GetBucketVersioning` to CodePipeline, CodeBuild, and CloudFormation service roles using unprefixed wildcard patterns: `role${RolePath}CodePipelineServiceRole-*`, `role${RolePath}CodeBuildServiceRole-*`, `role${RolePath}CloudFormationSvcRole-*`
8. THE S3_Artifacts_Policy_Module SHALL include a `WhitelistedPut` statement that allows `s3:PutObject` to CodePipeline and CodeBuild service roles using unprefixed wildcard patterns: `role${RolePath}CodePipelineServiceRole-*`, `role${RolePath}CodeBuildServiceRole-*`
9. THE S3_Artifacts_Policy_Module SHALL NOT use a `UseProjectPrefix` condition or `Prefix` parameter because the account-wide bucket grants access to all pipeline roles regardless of prefix
10. THE S3_Artifacts_Policy_Module SHALL use `Fn::Sub` to construct IAM principal ARNs referencing `AWS::AccountId` and `RolePath`

### Requirement 3: Integrate S3 Artifacts Modules into Account-Wide Infrastructure Template

**User Story:** As a platform administrator, I want the option to create a shared S3 artifacts bucket at the account level via the account-wide infrastructure template, so that I can provision a single artifacts bucket without deploying the full storage template separately.

#### Acceptance Criteria

1. THE Account_Wide_Infrastructure_Template SHALL add an `EnableS3ArtifactsBucket` parameter of type String with allowed values "true" and "false" and default "false"
2. THE Account_Wide_Infrastructure_Template SHALL add an `EnableS3ArtifactsBucket` condition that evaluates to true when the `EnableS3ArtifactsBucket` parameter equals "true"
3. THE Account_Wide_Infrastructure_Template SHALL add an `S3BucketNameOrgPrefix` parameter of type String with default "", AllowedPattern `^[a-z0-9][a-z0-9-]{0,18}[a-z0-9]$|^$`, and ConstraintDescription "May be empty or 2 to 20 characters (8 or less recommended). Lower case alphanumeric and dashes. Must start and end with a letter or number."
4. THE Account_Wide_Infrastructure_Template SHALL add an `S3LogBucketName` parameter of type String with default "", AllowedPattern `^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$|^$`, and ConstraintDescription "Must be a valid S3 bucket name or empty. Must be between 3 and 63 characters long. Lower case alphanumeric and dashes. Must start and end with a letter or number."
5. WHEN `EnableS3ArtifactsBucket` is "true", THE Account_Wide_Infrastructure_Template SHALL include the S3 Artifacts Bucket module via `Fn::Transform: AWS::Include` with logical ID `S3ArtifactsBucketRegional` referencing the path `s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/account-wide/s3-artifacts-bucket.yml`
6. WHEN `EnableS3ArtifactsBucket` is "true", THE Account_Wide_Infrastructure_Template SHALL include the S3 Artifacts Policy module via `Fn::Transform: AWS::Include` with logical ID `S3ArtifactBucketPolicy` referencing the path `s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/account-wide/s3-artifacts-bucket-policy.yml`
7. THE Account_Wide_Infrastructure_Template SHALL add conditions `UseS3BucketNameOrgPrefix` (true when S3BucketNameOrgPrefix is not empty) and `HasLoggingBucket` (true when S3LogBucketName is not empty)
8. THE Account_Wide_Infrastructure_Template SHALL add an "S3 Artifacts Bucket" parameter group to the `AWS::CloudFormation::Interface` metadata containing `EnableS3ArtifactsBucket`, `S3BucketNameOrgPrefix`, and `S3LogBucketName`

### Requirement 4: Account-Wide S3 Artifacts Bucket Outputs

**User Story:** As a platform administrator, I want the account-wide infrastructure template to output the S3 artifacts bucket name when the bucket is created, so that I can reference it from other templates and stacks.

#### Acceptance Criteria

1. WHEN `EnableS3ArtifactsBucket` is "true", THE Account_Wide_Infrastructure_Template SHALL output the S3 artifacts bucket name using `Ref: S3ArtifactsBucketRegional` with Condition `EnableS3ArtifactsBucket` and a description of "Name of the S3 artifacts bucket for pipeline build artifacts"
2. WHEN `EnableS3ArtifactsBucket` is "true", THE Account_Wide_Infrastructure_Template SHALL export the S3 artifacts bucket name using the naming convention `${OrgPrefix}-S3-Artifacts-Bucket-Name` with Condition `EnableS3ArtifactsBucket`
3. WHEN `EnableS3ArtifactsBucket` is "true", THE Account_Wide_Infrastructure_Template SHALL output a console link to the S3 bucket using the format `https://s3.console.aws.amazon.com/s3/buckets/${S3ArtifactsBucketRegional}` with Condition `EnableS3ArtifactsBucket`
