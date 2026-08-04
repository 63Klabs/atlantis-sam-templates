# Implementation Plan: Pipeline Module Extraction

## Overview

Create 15 pipeline module files under `templates/v2/modules/pipeline/` for the
pieces that are common across the three pipeline templates, then refactor each
template to consume them via `Fn::Transform: AWS::Include` while preserving logical
IDs and (except for the two Intentional Behavior Changes) behavior. Each module is
a headerless single resource using long-form intrinsics with a header documenting
its parent prerequisites. Each template gets a version bump (first), the
`S3ModuleLocation`/`S3ModuleNamespace` parameters, a cfn-lint ignore set, and its
inline resources replaced by includes. Finish with CHANGELOG, documentation, and
validation.

Extraction of each module MUST be behavior-preserving: copy the current inline
resource, convert shorthand tags to long-form, drop the wrapping logical name, and
keep `Condition`/`DeletionPolicy`/`UpdateReplacePolicy`. The only deliberate
deltas are the CodeBuild image standardization and the `s3:GetBucketLocation`
superset in the reconciled CodeBuild role.

## Tasks

- [x] 1. Create pipeline notification modules (all three templates)
  - [x] 1.1 Create `templates/v2/modules/pipeline/pipeline-notification-topic.yml`
    - `Type: AWS::SNS::Topic`, no `Condition`; topic name `${AWS::StackName}-pipeline-notifications`, email subscription to `AlarmNotificationEmail`
    - Header lists parent params: `AlarmNotificationEmail` (and `AWS::StackName`); note long-form intrinsics
    - Long-form intrinsics only
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.7, 2.8_
  - [x] 1.2 Create `pipeline-notification-started-rule.yml`, `pipeline-notification-succeeded-rule.yml`, `pipeline-notification-failed-rule.yml`
    - `Type: AWS::Events::Rule` each; preserve EventPattern (STARTED/SUCCEEDED/FAILED), Target `Ref: PipelineNotificationTopic`, and the `Fn::Sub` InputTemplate/console link
    - Header states parent MUST name the topic `PipelineNotificationTopic`; params `Prefix`, `ProjectId`, `StageId` (and `AWS::Region`)
    - _Requirements: 1.1-1.6, 2.2, 2.3, 2.4, 2.6, 2.7, 2.8_
  - [x] 1.3 Create `pipeline-notification-topic-policy.yml`
    - `Type: AWS::SNS::TopicPolicy`; `Ref: PipelineNotificationTopic` for Topics and Resource
    - Header states parent MUST name the topic `PipelineNotificationTopic`
    - _Requirements: 1.1-1.5, 2.5, 2.6, 2.8_

- [x] 2. Create source trigger modules
  - [x] 2.1 Create `source-event-service-role.yml`
    - `Type: AWS::IAM::Role`, `Condition: IsNotDevelopment`; preserve RoleName, PermissionsBoundary `Fn::If`, StartPipelineExecution policy
    - Header params: `Prefix`, `ProjectId`, `StageId`, `RolePath`, `PermissionsBoundaryArn`; conditions `IsNotDevelopment`, `HasPermissionsBoundaryArn`
    - _Requirements: 1.1-1.6, 3.1, 3.2, 3.6_
  - [x] 2.2 Create `source-event-rule.yml`
    - `Type: AWS::Events::Rule`, `Condition: IsNotDevelopment`; preserve CodeCommit EventPattern, Target `Fn::GetAtt: [SourceEventServiceRole, Arn]`
    - Header states parent MUST name the role `SourceEventServiceRole`; params `Prefix`, `ProjectId`, `StageId`, `Repository`, `RepositoryBranch`; condition `IsNotDevelopment`
    - _Requirements: 1.1-1.6, 3.3, 3.4, 3.5, 3.6_

- [x] 3. Create build support and build modules (all three templates)
  - [x] 3.1 Create `codebuild-log-group.yml`
    - `Type: AWS::Logs::LogGroup`, `Condition: IsNotDevelopment`, `DeletionPolicy: Delete`, `UpdateReplacePolicy: Retain`; name `/aws/codebuild/${Prefix}-${ProjectId}-${StageId}-Build`, 90-day retention
    - Header params: `Prefix`, `ProjectId`, `StageId`; condition `IsNotDevelopment`
    - _Requirements: 1.1-1.7, 4.1, 4.2, 4.3_
  - [x] 3.2 Create `codebuild-service-role.yml` (reconciled for all three)
    - `Type: AWS::IAM::Role`, `Condition: IsNotDevelopment`; base on the pipeline+github policy content
    - Include `s3:GetBucketLocation` in the bucket-listing statement (superset preserving build-only)
    - Use `Fn::Sub` + `OrgPrefix` ARN construction (functionally identical to build-only's `Fn::Join`)
    - Header lists params/conditions per design; note the `s3:GetBucketLocation` superset
    - _Requirements: 1.1-1.6, 5.1, 5.2, 5.3, 5.7_
  - [x] 3.3 Create `codebuild-project.yml` (standardized image for all three)
    - `Type: AWS::CodeBuild::Project`, `Condition: IsNotDevelopment`; image `aws/codebuild/amazonlinux-x86_64-standard:5.0`
    - `Fn::GetAtt: [CodeBuildServiceRole, Arn]` for ServiceRole; preserve env vars and BuildSpec `Fn::If` logic
    - Header states parent MUST name the role `CodeBuildServiceRole`; lists params/conditions per design; note the image standardization
    - _Requirements: 1.1-1.6, 5.4, 5.5, 5.6, 5.7_

- [x] 4. Create deploy service role modules (pipeline + github)
  - [x] 4.1 Create `cloudformation-svc-role.yml`
    - `Type: AWS::IAM::Role`, no `Condition`; convert the full inline policy to long-form
    - `Fn::FindInMap: [LambdaInsightsAccountId, {Ref: "AWS::Region"}, AccountId]` and the `LambdaParamSecretsAccountId` equivalent
    - Header lists params/conditions AND mappings `LambdaInsightsAccountId`, `LambdaParamSecretsAccountId` (parent must define both)
    - _Requirements: 1.1-1.6, 6.1, 6.2, 6.3, 6.6_
  - [x] 4.2 Create `codedeploy-service-role.yml`
    - `Type: AWS::IAM::Role`, no `Condition`; preserve trust policy and `AWSCodeDeployRoleForLambda` managed policy
    - Header params: `Prefix`, `ProjectId`, `StageId`, `RolePath`, `PermissionsBoundaryArn`; condition `HasPermissionsBoundaryArn`
    - _Requirements: 1.1-1.6, 6.4, 6.5, 6.6_

- [x] 5. Create PostDeploy modules (pipeline + github)
  - [x] 5.1 Create `postdeploy-service-role.yml`
    - `Type: AWS::IAM::Role`, `Condition: IsPostDeployEnabledAndNotDev`; convert inline policy to long-form
    - Header lists params/conditions per design
    - _Requirements: 1.1-1.6, 7.1, 7.5, 7.6_
  - [x] 5.2 Create `postdeploy-project.yml`
    - `Type: AWS::CodeBuild::Project`, `Condition: IsPostDeployEnabledAndNotDev`; image `aws/codebuild/amazonlinux-x86_64-standard:5.0`
    - `Fn::GetAtt: [PostDeployServiceRole, Arn]`; preserve env vars and PostDeploy BuildSpec logic
    - Header states parent MUST name the role `PostDeployServiceRole`
    - _Requirements: 1.1-1.6, 7.2, 7.4, 7.5, 7.6_
  - [x] 5.3 Create `postdeploy-log-group.yml`
    - `Type: AWS::Logs::LogGroup`, `Condition: IsPostDeployEnabledAndNotDev`, `DeletionPolicy: Delete`, `UpdateReplacePolicy: Retain`; name `/aws/codebuild/${Prefix}-${ProjectId}-${StageId}-PostDeploy`
    - Header params: `Prefix`, `ProjectId`, `StageId`; condition `IsPostDeployEnabledAndNotDev`
    - _Requirements: 1.1-1.7, 7.3, 7.5, 7.6_

- [x] 6. Checkpoint - Verify module syntax
  - All 15 modules begin with `Type:` at the top level (no wrapping logical name)
  - No YAML shorthand tags (`!Ref`, `!Sub`, `!If`, `!GetAtt`, `!Join`, `!Select`, `!Split`, `!FindInMap`) in any module
  - `Condition`/`DeletionPolicy`/`UpdateReplacePolicy` retained where the inline resource had them
  - Each header lists the correct parent prerequisites and sibling logical IDs
  - Diff each module against its original inline resource to confirm behavior parity (only long-form rewrite, dropped logical name, and the two Intentional Behavior Changes)
  - Ensure all tests pass, ask the user if questions arise

- [x] 7. Integrate modules into `template-pipeline.yml` (CodeCommit, full + PostDeploy)
  - [x] 7.1 Increment version v2.0.20 → v2.0.21 with current date (FIRST edit)
    - _Requirements: 9.1, 9.5_
  - [x] 7.2 Add `S3ModuleLocation` and `S3ModuleNamespace` parameters (verbatim from account templates); add "Module Source" parameter group; add `cfn-lint` `ignore_checks` (E3001, E3005, E6101, W2001, W8001) to `Metadata`
    - _Requirements: 8.1, 8.2_
  - [x] 7.3 Replace inline resources with `AWS::Include` references at the SAME logical IDs: `PipelineNotificationTopic`, `PipelineStartedRule`, `PipelineSucceededRule`, `PipelineFailedRule`, `PipelineNotificationTopicPolicy`, `SourceEventServiceRole`, `SourceEvent`, `CodeBuildLogGroup`, `CodeBuildServiceRole`, `CodeBuildProject`, `CloudFormationSvcRole`, `CodeDeployServiceRole`, `PostDeployServiceRole`, `PostDeployProject`, `PostDeployLogGroup`
    - Keep `CodePipelineServiceRole` and `ProjectPipeline` inline; preserve `ProjectPipeline` `DependsOn: CodeBuildProject`
    - _Requirements: 8.3, 8.4, 8.5, 8.6, 8.10_
  - [x] 7.4 Verify all params/conditions/mappings referenced by consumed modules remain defined (including `LambdaInsightsAccountId`, `LambdaParamSecretsAccountId`)
    - _Requirements: 8.9_

- [x] 8. Integrate modules into `template-pipeline-github.yml` (GitHub, full + PostDeploy)
  - [x] 8.1 Increment version v2.0.3 → v2.0.4 with current date (FIRST edit)
    - _Requirements: 9.1, 9.5_
  - [x] 8.2 Add `S3ModuleLocation`/`S3ModuleNamespace` params, "Module Source" group, and cfn-lint `ignore_checks`
    - _Requirements: 8.1, 8.2_
  - [x] 8.3 Replace inline resources with includes at the SAME logical IDs: the five notification resources, `SourceEventServiceRole`, `CodeBuildLogGroup`, `CodeBuildServiceRole`, `CodeBuildProject`, `CloudFormationSvcRole`, `CodeDeployServiceRole`, `PostDeployServiceRole`, `PostDeployProject`, `PostDeployLogGroup`
    - Do NOT include `source-event-rule.yml`; keep `CodePipelineServiceRole` (with CodeConnectionsAccess) and `ProjectPipeline` inline
    - _Requirements: 8.3, 8.4, 8.5, 8.7, 8.10_
  - [x] 8.4 Verify referenced params/conditions/mappings remain defined (including `GitHubConnectionArn`, `LambdaInsightsAccountId`, `LambdaParamSecretsAccountId`)
    - _Requirements: 8.9_

- [x] 9. Integrate modules into `template-pipeline-build-only.yml` (CodeCommit, Source + Build)
  - [x] 9.1 Increment version v2.0.5 → v2.0.6 with current date (FIRST edit)
    - _Requirements: 9.1, 9.5_
  - [x] 9.2 Add `S3ModuleLocation`/`S3ModuleNamespace` params, "Module Source" group, and cfn-lint `ignore_checks`
    - _Requirements: 8.1, 8.2_
  - [x] 9.3 Replace inline resources with includes at the SAME logical IDs: the five notification resources, `SourceEventServiceRole`, `SourceEvent`, `CodeBuildLogGroup`, `CodeBuildServiceRole`, `CodeBuildProject`
    - Keep `CodePipelineServiceRole` and `ProjectPipeline` inline
    - _Requirements: 8.3, 8.4, 8.5, 8.8, 8.10_
  - [x] 9.4 Verify referenced params/conditions remain defined
    - _Requirements: 8.9_

- [x] 10. Checkpoint - Validate templates
  - Run cfn-lint on all three templates; confirm they parse with the new params, metadata, and includes
  - Confirm each include `Location` path resolves to `templates/v2/modules/pipeline/<file>.yml`
  - Confirm no consumed module references an undefined parameter/condition/mapping/sibling
  - Ensure all tests pass, ask the user if questions arise

- [x] 11. Update CHANGELOG and documentation
  - [x] 11.1 Update `CHANGELOG.md` under `v0.0.39 (unreleased)`
    - Under "Added": the 15 pipeline modules; reference `[Spec: 0-0-39-pipeline-module-extraction](.kiro/specs/0-0-39-pipeline-module-extraction/)`
    - Under "Changed": Pipeline: template-pipeline.yml v2.0.21, template-pipeline-github.yml v2.0.4, template-pipeline-build-only.yml v2.0.6 — refactored to consume pipeline modules
    - Call out the two Intentional Behavior Changes (CodeBuild image upgrade for github/build-only; `s3:GetBucketLocation` added to pipeline/github CodeBuild role)
    - _Requirements: 9.2_
  - [x] 11.2 Update template documentation
    - Update the three pipeline template READMEs (or create if missing) noting `S3ModuleLocation`/`S3ModuleNamespace` and the external deploy-time module-bucket access requirement
    - List the pipeline module set in `templates/v2/modules/README.md` and/or the docs module index
    - _Requirements: 9.3, 9.4_

- [x] 12. Final checkpoint
  - All 15 module files exist at `templates/v2/modules/pipeline/`
  - All three templates have version bumps, module-source params, cfn-lint metadata, and includes at preserved logical IDs
  - CHANGELOG and documentation updated
  - Ensure all tests pass, ask the user if questions arise

## Notes

- This feature is Infrastructure as Code — property-based testing is not applicable; rely on cfn-lint, module-syntax checks, and behavior-parity diffs.
- Modules MUST use long-form intrinsics only (`Ref:`, `Fn::Sub:`, `Fn::If:`, `Fn::GetAtt:`, `Fn::Join:`, `Fn::Select:`, `Fn::Split:`, `Fn::FindInMap:`) because `AWS::Include` does not support YAML shorthand tags.
- Version bump is the FIRST edit to each template (template-version-control steering).
- `CodePipelineServiceRole` and `ProjectPipeline` remain inline in all three templates.
- Two Intentional Behavior Changes only: CodeBuild image standardization (github/build-only) and the `s3:GetBucketLocation` superset (pipeline/github). Everything else is behavior-preserving.
- Provisioning `S3ModuleLocation` and granting the deploying role read access to the module bucket are handled by an external process (out of scope).

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "2.1", "2.2", "3.1", "3.2", "3.3", "4.1", "4.2", "5.1", "5.2", "5.3"] },
    { "id": 1, "tasks": ["6"] },
    { "id": 2, "tasks": ["7.1", "7.2", "7.3", "7.4", "8.1", "8.2", "8.3", "8.4", "9.1", "9.2", "9.3", "9.4"] },
    { "id": 3, "tasks": ["10"] },
    { "id": 4, "tasks": ["11.1", "11.2"] },
    { "id": 5, "tasks": ["12"] }
  ]
}
```
