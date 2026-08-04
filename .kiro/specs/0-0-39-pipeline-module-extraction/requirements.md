# Requirements Document

## Introduction

This feature identifies the pieces that are duplicated across the three pipeline
templates and extracts them into reusable modules stored under
`templates/v2/modules/pipeline/`, then refactors the three pipeline templates to
consume those modules. The modules follow the same pattern already established by
the account templates (`account-wide-infrastructure.yml`,
`prefix-based-infrastructure.yml`): each module is a headerless single-resource
snippet (starts with `Type:`), consumed by a parent template through
`Fn::Transform: AWS::Include` resolved from
`s3://<S3ModuleLocation>/<S3ModuleNamespace>/templates/v2/modules/pipeline/<file>.yml`.
The including template assigns the logical name and keeps the parameters,
conditions, and mappings the module depends on.

The three pipeline templates today contain large amounts of identical YAML. The
notification block (SNS topic, three EventBridge rules, and topic policy) is
byte-for-byte identical across all three. The `CloudFormationSvcRole` (~350
lines), `CodeDeployServiceRole`, and the PostDeploy resources are identical
between `template-pipeline.yml` and `template-pipeline-github.yml`. Maintaining
these copies in lock-step is error prone (see the `future-update-pipeline-notifications`
and `0-0-31-pipeline-notification-formatting` specs), which is the motivation for
this extraction.

### Goals

- Create a `templates/v2/modules/pipeline/` module set for the pieces that are
  common across the pipeline templates.
- Refactor the three pipeline templates to consume those modules via
  `AWS::Include`, preserving each resource's existing logical ID and — except for
  the two intentional standardizations noted below — its deployed behavior.
- Keep the module authoring conventions consistent with the existing modules
  (long-form intrinsics, header comment contract, one resource per file).

### Resolved Decisions

These decisions were confirmed with the maintainer and are now fixed for this
spec:

1. **Scope — both phases.** This spec creates the module files AND refactors the
   three pipeline templates to consume them.
2. **Version control — in place with PATCH increments.** The templates are
   modified in place and their PATCH versions are incremented
   (`template-pipeline.yml` v2.0.20 → v2.0.21, `template-pipeline-github.yml`
   v2.0.3 → v2.0.4, `template-pipeline-build-only.yml` v2.0.5 → v2.0.6). The
   deploy-time requirement that the deploying role can read the module S3 bucket,
   and the provisioning of the `S3ModuleLocation` value, are handled by an
   external process and are OUT OF SCOPE for this spec.
3. **Resources that differ today:**
   - `CodeBuildProject` — the container image is standardized to
     `aws/codebuild/amazonlinux-x86_64-standard:5.0` (Amazon Linux 2023), which
     `template-pipeline.yml` already uses. This is extracted as a single module
     consumed by all three templates.
   - `CodeBuildServiceRole` — reconciled into a single module consumed by all
     three templates (see Intentional Behavior Changes).
   - `CodePipelineServiceRole` — left inline in each template (it differs across
     all three); NOT extracted.

### Intentional Behavior Changes

Everything in this feature preserves behavior EXCEPT the following two changes,
which are intentional standardizations approved by the maintainer and MUST be
recorded in the CHANGELOG and template documentation:

1. **CodeBuild image upgrade (github + build-only):** The `CodeBuildProject` in
   `template-pipeline-github.yml` and `template-pipeline-build-only.yml` changes
   from `aws/codebuild/amazonlinux2-x86_64-standard:5.0` (Node 20 / Python 3.12)
   to `aws/codebuild/amazonlinux-x86_64-standard:5.0` (Node 22 / Python 3.13 /
   Java Corretto 21). `template-pipeline.yml` is unchanged (already on this image).
2. **CodeBuild role permission superset (pipeline + github):** The reconciled
   `CodeBuildServiceRole` module adds the read-only `s3:GetBucketLocation` action
   (currently present only in build-only) to its bucket-listing statement, so a
   single definition serves all three templates without any template losing a
   permission. The bucket ARN construction is normalized to the `Fn::Sub` +
   `OrgPrefix` form used by pipeline + github, which is functionally identical to
   build-only's `Fn::Join` form.

## Glossary

- **Module**: A YAML snippet file stored in S3 that defines a single
  CloudFormation resource, referenced via `Fn::Transform: AWS::Include` in a
  parent template. Starts with `Type:` at the top level (no wrapping resource
  logical name), optionally followed by `Condition:`, `DeletionPolicy:`,
  `UpdateReplacePolicy:`, and `Properties:`.
- **Pipeline_Modules_Directory**: The new directory `templates/v2/modules/pipeline/`
  that stores the pipeline module snippets.
- **Pipeline_Template**: `templates/v2/pipeline/template-pipeline.yml` (v2.0.20) —
  CodeCommit source, full Source → Build → Deploy → PostDeploy pipeline.
- **GitHub_Pipeline_Template**: `templates/v2/pipeline/template-pipeline-github.yml`
  (v2.0.3) — GitHub source via CodeConnections, full pipeline.
- **Build_Only_Pipeline_Template**: `templates/v2/pipeline/template-pipeline-build-only.yml`
  (v2.0.5) — CodeCommit source, Source → Build only (no CloudFormation/PostDeploy).
- **Notification_Modules**: The five modules that make up the pipeline
  notification block (SNS topic, three EventBridge rules, topic policy).
- **Parent_Prerequisites**: The parameters, conditions, mappings, and sibling
  resource logical IDs that a module references and that the including template
  MUST define.
- **S3ModuleLocation**: The S3 bucket name where module snippets are stored.
- **S3ModuleNamespace**: The namespace path prefix within the S3 module bucket
  (default `atlantis`).
- **Behavior_Parity**: The property that the fully resolved template (after the
  `AWS::Include` transform) is functionally equivalent to the pre-refactor
  template — same logical IDs, resource types, properties, and conditions —
  except for the two Intentional Behavior Changes listed above.

## Requirements

### Requirement 1: Pipeline Module Authoring Conventions

**User Story:** As a platform maintainer, I want all pipeline modules to follow
the established module conventions, so that they behave identically to the
account and management-role modules and resolve correctly through `AWS::Include`.

#### Acceptance Criteria

1. THE Pipeline_Modules_Directory SHALL be `templates/v2/modules/pipeline/` and all
   modules created by this feature SHALL be stored there.
2. Each module file SHALL define exactly one CloudFormation resource, beginning
   with `Type:` at the top level with no wrapping resource logical name, so that
   the including template assigns the logical name.
3. Each module SHALL use ONLY long-form intrinsic function syntax (`Ref:`,
   `Fn::Sub:`, `Fn::If:`, `Fn::GetAtt:`, `Fn::Join:`, `Fn::Select:`, `Fn::Split:`,
   `Fn::FindInMap:`, `Ref: "AWS::NoValue"`) and SHALL NOT contain YAML shorthand
   tags (`!Ref`, `!Sub`, `!If`, `!GetAtt`, `!Join`, etc.), because `AWS::Include`
   does not support shorthand tags.
4. Each module SHALL begin with a header comment block that documents its
   Parent_Prerequisites: the parameters it references, the conditions it
   references, any mappings it references, and any sibling resource logical IDs
   it references by name.
5. Each module header comment SHALL include the note that `AWS::Include` does not
   support YAML shorthand tags and that all intrinsics use long-form syntax,
   consistent with existing modules.
6. WHERE a resource has a `Condition` in the current inline template, the module
   SHALL retain that `Condition:` key referencing the parent-defined condition,
   and the header SHALL list it as a Parent_Prerequisite.
7. WHERE a resource has a `DeletionPolicy` or `UpdateReplacePolicy` in the current
   inline template, the module SHALL retain those keys unchanged.
8. Except for the two Intentional Behavior Changes, each module SHALL be a
   functional equivalent of the current inline resource it replaces
   (Behavior_Parity), differing only in intrinsic syntax form (long-form) and the
   removal of the wrapping logical name.

### Requirement 2: Pipeline Notification Modules (all three templates)

**User Story:** As a platform maintainer, I want the pipeline notification block
extracted into modules, so that notification changes are made once instead of
being duplicated across all three pipeline templates.

#### Acceptance Criteria

1. THE feature SHALL create `pipeline-notification-topic.yml` defining the
   `AWS::SNS::Topic` (currently `PipelineNotificationTopic`), with no resource
   `Condition`, subscribing `AlarmNotificationEmail` and naming the topic
   `${AWS::StackName}-pipeline-notifications`.
2. THE feature SHALL create `pipeline-notification-started-rule.yml` defining the
   `AWS::Events::Rule` for the STARTED state (currently `PipelineStartedRule`).
3. THE feature SHALL create `pipeline-notification-succeeded-rule.yml` defining the
   `AWS::Events::Rule` for the SUCCEEDED state (currently `PipelineSucceededRule`).
4. THE feature SHALL create `pipeline-notification-failed-rule.yml` defining the
   `AWS::Events::Rule` for the FAILED state (currently `PipelineFailedRule`).
5. THE feature SHALL create `pipeline-notification-topic-policy.yml` defining the
   `AWS::SNS::TopicPolicy` (currently `PipelineNotificationTopicPolicy`).
6. THE three notification rule modules and the topic policy module SHALL reference
   the SNS topic using long-form `Ref: PipelineNotificationTopic`, and their
   header comments SHALL state that the parent MUST name the topic resource
   `PipelineNotificationTopic`.
7. THE Notification_Modules' headers SHALL document Parent_Prerequisites:
   parameters `Prefix`, `ProjectId`, `StageId`, `AlarmNotificationEmail`, and
   pseudo-parameters `AWS::StackName`, `AWS::Region`.
8. THE Notification_Modules SHALL be functionally identical to the inline
   notification resources currently present in all three pipeline templates
   (Behavior_Parity).

### Requirement 3: Source Trigger Modules

**User Story:** As a platform maintainer, I want the source-trigger IAM role and
the CodeCommit source event rule extracted into modules, so that the
CodeCommit-based templates share a single definition.

#### Acceptance Criteria

1. THE feature SHALL create `source-event-service-role.yml` defining the
   `AWS::IAM::Role` (currently `SourceEventServiceRole`) with
   `Condition: IsNotDevelopment`, used by all three templates.
2. THE `source-event-service-role.yml` header SHALL document Parent_Prerequisites:
   parameters `Prefix`, `ProjectId`, `StageId`, `RolePath`, `PermissionsBoundaryArn`;
   conditions `IsNotDevelopment`, `HasPermissionsBoundaryArn`.
3. THE feature SHALL create `source-event-rule.yml` defining the
   `AWS::Events::Rule` for CodeCommit (currently `SourceEvent`) with
   `Condition: IsNotDevelopment`, used by Pipeline_Template and
   Build_Only_Pipeline_Template (NOT GitHub_Pipeline_Template).
4. THE `source-event-rule.yml` SHALL reference the source-event role using
   long-form `Fn::GetAtt: [SourceEventServiceRole, Arn]`, and its header SHALL
   state that the parent MUST name the role resource `SourceEventServiceRole`.
5. THE `source-event-rule.yml` header SHALL document Parent_Prerequisites:
   parameters `Prefix`, `ProjectId`, `StageId`, `Repository`, `RepositoryBranch`;
   condition `IsNotDevelopment`.
6. THE source trigger modules SHALL be functionally identical to the current
   inline `SourceEventServiceRole` and `SourceEvent` resources (Behavior_Parity).

### Requirement 4: Build Log Group Module (all three templates)

**User Story:** As a platform maintainer, I want the CodeBuild log group extracted
into a module, so that its retention policy is defined once.

#### Acceptance Criteria

1. THE feature SHALL create `codebuild-log-group.yml` defining the
   `AWS::Logs::LogGroup` (currently `CodeBuildLogGroup`) with
   `Condition: IsNotDevelopment`, `DeletionPolicy: Delete`, and
   `UpdateReplacePolicy: Retain`.
2. THE `codebuild-log-group.yml` header SHALL document Parent_Prerequisites:
   parameters `Prefix`, `ProjectId`, `StageId`; condition `IsNotDevelopment`.
3. THE module SHALL preserve the current log group name
   `/aws/codebuild/${Prefix}-${ProjectId}-${StageId}-Build` and the 90-day
   retention (Behavior_Parity).

### Requirement 5: Build Modules (all three templates)

**User Story:** As a platform maintainer, I want the CodeBuild service role and
CodeBuild project extracted into standardized modules, so that all three
templates share one build definition on a single container image.

#### Acceptance Criteria

1. THE feature SHALL create `codebuild-service-role.yml` defining the
   `AWS::IAM::Role` (currently `CodeBuildServiceRole`) with
   `Condition: IsNotDevelopment`, reconciled to serve all three templates.
2. THE `codebuild-service-role.yml` SHALL include `s3:GetBucketLocation` in its
   bucket-listing statement (superset that preserves Build_Only_Pipeline_Template's
   capability) and SHALL construct bucket ARNs using the `Fn::Sub` + `OrgPrefix`
   form used by Pipeline_Template and GitHub_Pipeline_Template (functionally
   identical to build-only's `Fn::Join` form).
3. THE `codebuild-service-role.yml` header SHALL document Parent_Prerequisites:
   parameters `Prefix`, `ProjectId`, `StageId`, `RolePath`, `PermissionsBoundaryArn`,
   `S3ArtifactsBucket`, `S3BucketNameOrgPrefix`, `S3StaticHostBucket`,
   `ParameterStoreHierarchy`, `DeployEnvironment`, `BuildSpec`,
   `CodeBuildSvcRoleIncludeManagedPolicyArns`; conditions `IsNotDevelopment`,
   `HasPermissionsBoundaryArn`, `HasManagedPoliciesForCodeBuildSvcRole`,
   `UseS3BucketNameOrgPrefix`, `HasS3StaticHostBucket`, `HasS3BuildSpecLocation`.
4. THE feature SHALL create `codebuild-project.yml` defining the
   `AWS::CodeBuild::Project` (currently `CodeBuildProject`) with
   `Condition: IsNotDevelopment`, standardized on the container image
   `aws/codebuild/amazonlinux-x86_64-standard:5.0`.
5. THE `codebuild-project.yml` SHALL reference the build role using long-form
   `Fn::GetAtt: [CodeBuildServiceRole, Arn]`, and its header SHALL state that the
   parent MUST name the role resource `CodeBuildServiceRole`.
6. THE `codebuild-project.yml` header SHALL document Parent_Prerequisites:
   parameters `Prefix`, `ProjectId`, `StageId`, `S3ArtifactsBucket`,
   `S3BucketNameOrgPrefix`, `Repository`, `RepositoryBranch`,
   `ParameterStoreHierarchy`, `DeployEnvironment`, `AlarmNotificationEmail`,
   `S3StaticHostBucket`, `RolePath`, `PermissionsBoundaryArn`, `BuildSpec`;
   conditions `IsNotDevelopment`, `UseS3BucketNameOrgPrefix`,
   `HasS3BuildSpecLocation`, `UseDefaultBuildSpecLocation`.
7. Apart from the two Intentional Behavior Changes (image upgrade for
   github/build-only; `s3:GetBucketLocation` superset for pipeline/github), the
   build modules SHALL be functionally identical to the current inline resources
   (Behavior_Parity). The differing `BuildSpec` parameter DEFAULT values remain in
   each parent template's Parameters section and are NOT part of these modules.

### Requirement 6: Deploy Service Role Modules (Pipeline + GitHub templates)

**User Story:** As a platform maintainer, I want the CloudFormation and CodeDeploy
service roles extracted into modules, so that the large, identical IAM
definitions shared by the two full pipelines are maintained once.

#### Acceptance Criteria

1. THE feature SHALL create `cloudformation-svc-role.yml` defining the
   `AWS::IAM::Role` (currently `CloudFormationSvcRole`) with no resource
   `Condition`.
2. THE `cloudformation-svc-role.yml` header SHALL document Parent_Prerequisites:
   parameters `Prefix`, `ProjectId`, `StageId`, `RolePath`, `PermissionsBoundaryArn`,
   `S3ArtifactsBucket`, `S3BucketNameOrgPrefix`, `ParameterStoreHierarchy`,
   `DeployEnvironment`, `CloudFormationSvcRoleIncludeManagedPolicyArns`;
   conditions `HasPermissionsBoundaryArn`, `HasManagedPoliciesForCloudFormationSvcRole`,
   `UseS3BucketNameOrgPrefix`; mappings `LambdaInsightsAccountId`,
   `LambdaParamSecretsAccountId`.
3. THE `cloudformation-svc-role.yml` SHALL reference the region-to-account mappings
   using long-form `Fn::FindInMap: [LambdaInsightsAccountId, {Ref: "AWS::Region"}, AccountId]`
   (and the equivalent for `LambdaParamSecretsAccountId`), and its header SHALL
   state that the parent MUST define both mappings.
4. THE feature SHALL create `codedeploy-service-role.yml` defining the
   `AWS::IAM::Role` (currently `CodeDeployServiceRole`) with no resource
   `Condition`.
5. THE `codedeploy-service-role.yml` header SHALL document Parent_Prerequisites:
   parameters `Prefix`, `ProjectId`, `StageId`, `RolePath`, `PermissionsBoundaryArn`;
   condition `HasPermissionsBoundaryArn`.
6. THE deploy service role modules SHALL be functionally identical to the current
   inline resources shared by Pipeline_Template and GitHub_Pipeline_Template
   (Behavior_Parity).

### Requirement 7: PostDeploy Modules (Pipeline + GitHub templates)

**User Story:** As a platform maintainer, I want the PostDeploy service role,
CodeBuild project, and log group extracted into modules, so that the optional
PostDeploy stage is defined once for the two full pipelines.

#### Acceptance Criteria

1. THE feature SHALL create `postdeploy-service-role.yml` defining the
   `AWS::IAM::Role` (currently `PostDeployServiceRole`) with
   `Condition: IsPostDeployEnabledAndNotDev`.
2. THE feature SHALL create `postdeploy-project.yml` defining the
   `AWS::CodeBuild::Project` (currently `PostDeployProject`) with
   `Condition: IsPostDeployEnabledAndNotDev`.
3. THE feature SHALL create `postdeploy-log-group.yml` defining the
   `AWS::Logs::LogGroup` (currently `PostDeployLogGroup`) with
   `Condition: IsPostDeployEnabledAndNotDev`, `DeletionPolicy: Delete`, and
   `UpdateReplacePolicy: Retain`.
4. THE `postdeploy-project.yml` SHALL reference the PostDeploy role using long-form
   `Fn::GetAtt: [PostDeployServiceRole, Arn]`, and its header SHALL state that the
   parent MUST name the role resource `PostDeployServiceRole`. The PostDeploy
   project SHALL use the same container image as `codebuild-project.yml`
   (`aws/codebuild/amazonlinux-x86_64-standard:5.0`), which both full templates
   already use for PostDeploy.
5. THE PostDeploy modules' headers SHALL document Parent_Prerequisites: parameters
   `Prefix`, `ProjectId`, `StageId`, `RolePath`, `PermissionsBoundaryArn`,
   `S3ArtifactsBucket`, `S3BucketNameOrgPrefix`, `ParameterStoreHierarchy`,
   `DeployEnvironment`, `PostDeployS3StaticHostBucket`, `PostDeployBuildSpec`,
   `PostDeploySvcRoleIncludeManagedPolicyArns`; conditions
   `IsPostDeployEnabledAndNotDev`, `HasPermissionsBoundaryArn`,
   `HasManagedPoliciesForPostDeploySvcRole`, `HasPostDeployS3StaticHostBucket`,
   `HasPostDeployBuildSpecS3Location`, `UseDefaultPostDeployBuildSpecLocation`,
   `UseS3BucketNameOrgPrefix`.
6. THE PostDeploy modules SHALL be functionally identical to the current inline
   resources shared by Pipeline_Template and GitHub_Pipeline_Template
   (Behavior_Parity).

### Requirement 8: Integrate Modules into the Pipeline Templates

**User Story:** As a platform maintainer, I want the pipeline templates to consume
the new modules through `AWS::Include`, so that the duplicated inline resources
are replaced by shared references while preserving behavior.

#### Acceptance Criteria

1. Each modified template SHALL add the `S3ModuleLocation` and `S3ModuleNamespace`
   parameters using the exact definitions used by the account templates, and SHALL
   add a "Module Source" parameter group to the `AWS::CloudFormation::Interface`
   metadata containing both.
2. Each modified template's `Metadata` SHALL add the cfn-lint `ignore_checks` set
   `E3001`, `E3005`, `E6101`, `W2001`, `W8001` consistent with the account
   templates.
3. Each extracted resource SHALL be replaced by a `Fn::Transform: AWS::Include`
   block keyed at the SAME logical ID it currently uses (e.g.,
   `PipelineNotificationTopic`, `CloudFormationSvcRole`, `CodeBuildProject`), with
   `Location` `s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/pipeline/<file>.yml`.
4. WHERE an extracted resource had a `Condition`, the resource `Condition` SHALL be
   preserved by retaining the `Condition:` key inside the module, so the resolved
   resource is conditioned exactly as before.
5. WHERE the inline `ProjectPipeline` uses `DependsOn: CodeBuildProject` (and any
   other DependsOn), that dependency SHALL be preserved; `ProjectPipeline` and
   `CodePipelineServiceRole` remain inline in each template.
6. THE Pipeline_Template SHALL consume: the five Notification_Modules,
   `source-event-service-role.yml`, `source-event-rule.yml`,
   `codebuild-log-group.yml`, `codebuild-service-role.yml`, `codebuild-project.yml`,
   `cloudformation-svc-role.yml`, `codedeploy-service-role.yml`, and the three
   PostDeploy modules (15 modules).
7. THE GitHub_Pipeline_Template SHALL consume: the five Notification_Modules,
   `source-event-service-role.yml`, `codebuild-log-group.yml`,
   `codebuild-service-role.yml`, `codebuild-project.yml`, `cloudformation-svc-role.yml`,
   `codedeploy-service-role.yml`, and the three PostDeploy modules (14 modules); it
   SHALL NOT consume `source-event-rule.yml`.
8. THE Build_Only_Pipeline_Template SHALL consume: the five Notification_Modules,
   `source-event-service-role.yml`, `source-event-rule.yml`,
   `codebuild-log-group.yml`, `codebuild-service-role.yml`, and
   `codebuild-project.yml` (10 modules).
9. WHERE a template consumes modules, ALL parameters, conditions, and mappings
   referenced by those modules SHALL remain defined in the parent template
   (including the `LambdaInsightsAccountId` and `LambdaParamSecretsAccountId`
   mappings in the two full templates).
10. WHERE a template consumes modules, THE fully resolved template SHALL preserve
    Behavior_Parity with the pre-refactor template (same logical IDs, resource
    types, properties, conditions, and outputs), except for the two Intentional
    Behavior Changes.

### Requirement 9: Version Control, Changelog, and Documentation

**User Story:** As a platform maintainer, I want template versioning, the
changelog, and documentation updated to reflect the extraction, so that the
change is traceable and users understand the new module dependency and the two
intentional behavior changes.

#### Acceptance Criteria

1. THE `template-pipeline.yml` version SHALL be incremented from v2.0.20 to
   v2.0.21 with the current date; THE `template-pipeline-github.yml` version SHALL
   be incremented from v2.0.3 to v2.0.4; THE `template-pipeline-build-only.yml`
   version SHALL be incremented from v2.0.5 to v2.0.6.
2. THE CHANGELOG.md SHALL be updated under the `v0.0.39 (unreleased)` section
   referencing this spec (`0-0-39-pipeline-module-extraction`), listing the new
   pipeline modules and each affected template with its new version, and calling
   out the two Intentional Behavior Changes (CodeBuild image upgrade for
   github/build-only; `s3:GetBucketLocation` added to pipeline/github CodeBuild
   role).
3. THE documentation SHALL be updated for the three modified templates and SHALL
   note the module-source parameters (`S3ModuleLocation`, `S3ModuleNamespace`) and
   the deploy-time requirement that the deploying role can read the module S3
   bucket.
4. THE pipeline module set SHALL be listed in the modules documentation
   (`templates/v2/modules/README.md` and/or the docs module index) so users can
   discover the available pipeline modules.
5. THE version increment for each template SHALL be performed as the FIRST change
   to that template (before extraction edits), per the template-version-control
   steering.
