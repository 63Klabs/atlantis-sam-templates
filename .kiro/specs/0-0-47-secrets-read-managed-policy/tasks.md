# Implementation Plan: Secrets Read Managed Policies

## Overview

Add three account-wide, read-only, tag-matched (ABAC) IAM managed policies for Secrets Manager to `templates/v2/account/account-wide-infrastructure.yml`. Each policy is built from its own module in `templates/v2/modules/pipeline-policies/`. The work is additive: three module files, three `AWS::Include` resources and six outputs in the account-wide template, one fast unit test file, and documentation. No pipeline template or pipeline module changes.

Implementation language: YAML (CloudFormation modules and template) and Python (pytest unit tests). Per the repository testing guidelines, tests are fast example-based unit tests only. The design's Correctness Properties are checked by parametrizing the same assertions over the three modules, and no property-based tests are written.

## Tasks

- [x] 1. Create the three Secrets Read modules
  - [x] 1.1 Create `templates/v2/modules/pipeline-policies/secrets-read-deployment.yml`
    - Model the file on `codebuild-crud.yml` and `cognito-crud.yml` in the same directory, and on the module snippet in the design
    - Start the body at `Type: AWS::IAM::ManagedPolicy` with only `Type` and `Properties` at the top level, no logical ID and no `Resources:` block, and use long-form intrinsics only
    - Open with a comment block that states the parent template must define `OrgPrefix` and `RolePath`, the tag key `atlantis:ApplicationDeploymentId`, the value format `<Prefix>-<ProjectId>-<StageId>`, the reach, the fail-closed behavior, the tag-write control caveat, and that `kms:Decrypt` is not granted
    - Set `ManagedPolicyName` to `${OrgPrefix}-ManagedPolicyForPipeline-SecretsReadDeployment` (`Fn::Sub`), `Path` to `Ref: RolePath`, and a `Description` that says read-only and names `atlantis:ApplicationDeploymentId`
    - Add exactly one Allow statement with `Sid: SecretsReadDeploymentReadSecretTagMatch`, `Action` listing exactly `secretsmanager:GetSecretValue` and `secretsmanager:DescribeSecret` together, and `Resource` of `Fn::Sub: "arn:${AWS::Partition}:secretsmanager:*:${AWS::AccountId}:secret:*"`
    - Add `StringEquals` of `aws:ResourceTag/atlantis:ApplicationDeploymentId` to the plain string `${aws:PrincipalTag/atlantis:ApplicationDeploymentId}` (not inside `Fn::Sub`), and a quoted `"Null"` condition with `"false"` on both `aws:PrincipalTag/atlantis:ApplicationDeploymentId` and `aws:ResourceTag/atlantis:ApplicationDeploymentId`; both actions share these conditions in the one statement
    - Do not allow `ListSecrets`, `BatchGetSecretValue`, or any `secretsmanager:*` or `*` action
    - _Requirements: 1.2, 2.1, 2.4, 2.5, 2.6, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 5.1, 5.8, 5.9, 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 1.2 Create `templates/v2/modules/pipeline-policies/secrets-read-application.yml`
    - Same structure as 1.1 with tag key `atlantis:Application`, value format `<Prefix>-<ProjectId>`, policy name suffix `SecretsReadApplication`, and `Sid: SecretsReadApplicationReadSecretTagMatch`, with the same single statement allowing exactly `secretsmanager:GetSecretValue` and `secretsmanager:DescribeSecret`
    - Reach comment: all stages of one application
    - _Requirements: 1.3, 2.2, 2.4, 2.5, 2.6, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 5.2, 5.8, 5.9, 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 1.3 Create `templates/v2/modules/pipeline-policies/secrets-read-prefix.yml`
    - Same structure as 1.1 with tag key `atlantis:Prefix`, value format `<Prefix>`, policy name suffix `SecretsReadPrefix`, and `Sid: SecretsReadPrefixReadSecretTagMatch`, with the same single statement allowing exactly `secretsmanager:GetSecretValue` and `secretsmanager:DescribeSecret`
    - Reach comment: all applications under one prefix
    - _Requirements: 1.4, 2.3, 2.4, 2.5, 2.6, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 5.3, 5.8, 5.9, 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 2. Wire the modules into the account-wide template
  - [x] 2.1 Add resources and outputs to `templates/v2/account/account-wide-infrastructure.yml`
    - Read the file first and follow the style of the existing CodeBuild and Cognito policy resources and outputs
    - Add `SecretsReadDeploymentPolicy`, `SecretsReadApplicationPolicy`, and `SecretsReadPrefixPolicy` as `Fn::Transform` / `AWS::Include` resources after the Cognito policy resource and before `GitHubConnection`, with `Location` using `s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/pipeline-policies/secrets-read-<level>.yml`, and no `Condition`
    - Add outputs after `CognitoCrudPolicyName`: `SecretsRead{Deployment,Application,Prefix}PolicyArn` (value `!Ref` of the resource, description naming the `CloudFormationSvcRoleIncludeManagedPolicyArns`, `CodeBuildSvcRoleIncludeManagedPolicyArns`, and `PostDeploySvcRoleIncludeManagedPolicyArns` parameters, export `${OrgPrefix}-ProjectPipeline-SecretsRead<Level>-Arn`) and `SecretsRead{Deployment,Application,Prefix}PolicyName` (value `${OrgPrefix}-ManagedPolicyForPipeline-SecretsRead<Level>`, no export)
    - Do not rename or remove any existing parameter, resource, output, or export, and add no parameters
    - _Requirements: 1.1, 1.5, 1.6, 5.4, 5.5, 5.6, 5.7, 5.10_

  - [x] 2.2 Update the template header comment and version line
    - Set `# Version:` to `v2.1.0/<date of the change, YYYY-MM-DD>` and keep the version number `v2.1.0` (PATCH is 0, development mode per `.kiro/steering/template-version-control.md`)
    - Add the bullet `Secrets Manager read managed policies (deployment, application, prefix level; ABAC-scoped)` to the header resource list and extend the managed policy paragraph to mention the `atlantis:Application` and `atlantis:Prefix` tags
    - Leave the `OrgPrefix` parameter pattern, length, default, and description unchanged
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 3. Add fast unit tests
  - [x] 3.1 Create `tests/test_secrets_read_managed_policy_unit.py` with module tests
    - Define the `LEVELS` data (file, tag key, policy suffix, logical ID, Sid), `EXPECTED_ACTIONS = {"secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"}`, and `EXPECTED_RESOURCE` as in the design Testing Strategy
    - Parametrize over the three levels and load each module with `yaml.safe_load` (which rejects shorthand tags), plus a raw-text regex for `!(Sub|Ref|GetAtt|If|Join|Select)`
    - Module structure test: type is `AWS::IAM::ManagedPolicy`, top-level keys are only `Type` and `Properties`, no `Resources:` text, header comment names `OrgPrefix`, `RolePath`, the tag key, the value format, and "fail closed" (Property 5)
    - Naming test: `ManagedPolicyName`, `Path` equal to `Ref: RolePath`, and `Description` containing "read-only" and the tag key; every statement has a unique non-empty `Sid` (Property 5)
    - Condition test: every Allow statement has `StringEquals` with the exact `aws:ResourceTag/<key>` and `${aws:PrincipalTag/<key>}` value, and `Null: "false"` on both principal and resource keys (Property 1)
    - Single-tag test: the module references exactly one `atlantis:` key, equal to its level's key, and no condition value holds a literal Prefix, ProjectId, or StageId (Property 2)
    - Action test: the union of allowed actions equals `EXPECTED_ACTIONS`, both actions appear together in the same single Allow statement, none contains `*`, and none of `ListSecrets`, `BatchGetSecretValue`, or any create, update, delete, rotate, restore, replicate, tag, untag, or resource-policy action appears (the forbidden-action list does not include `DescribeSecret`) (Property 3)
    - Sid test: each module's single statement has the `Sid` `SecretsRead<Level>ReadSecretTagMatch` (Property 5)
    - Resource test: `Resource` equals `Fn::Sub: EXPECTED_RESOURCE` and has no other entry (Property 4)
    - Keep each test under 1 second and add no `hypothesis` imports
    - **Properties 1, 2, 3, 4, 5**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 5.1, 5.2, 5.3, 5.8, 5.9, 6.1, 6.2, 6.3, 6.4, 6.5, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.10**

  - [x] 3.2 Add template wiring tests to `tests/test_secrets_read_managed_policy_unit.py`
    - Load the account-wide template with `load_template` from `tests/cfn_test_utils.py` and follow how existing tests such as `tests/test_bedrock_invocation_logs_unit.py` handle `Fn::Transform` and `!Sub` tags
    - Wiring test: three unconditional `Fn::Transform` / `AWS::Include` resources with the expected logical IDs and `Location` values ending in the three module paths (Property 6)
    - Outputs test: three ARN outputs with the expected export names and descriptions that contain `SvcRoleIncludeManagedPolicyArns`, and three name outputs equal to the managed policy names with no export (Property 6)
    - Preservation test: the existing CodeBuild and Cognito policy resources, outputs, and export names, plus parameters `OrgPrefix` and `RolePath`, are still present (Property 7)
    - Header test: the `# Version:` line has version `v2.1.0` and a valid ISO date on or after 2026-11-09, and the header comment lists the secrets read managed policies (Property 7)
    - **Properties 6, 7**
    - **Validates: Requirements 1.1, 1.5, 1.6, 5.4, 5.5, 5.6, 5.7, 5.10, 8.7, 8.8, 8.9, 9.1, 9.2, 9.3**

- [x] 4. Checkpoint - Ensure all tests pass
  - Run `tests/test_secrets_read_managed_policy_unit.py` and `tests/test_cfn_templates.py` with the `.venv` interpreter and confirm cfn-lint passes for the account-wide template (Requirement 8.11)
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Update documentation and CHANGELOG (required, final task)
  - [x] 5.1 Update `CHANGELOG.md`
    - The `## v0.0.47 (unreleased)` header already exists above `## v0.0.46`; add an `### Added` entry under it
    - Reference spec `0-0-47-secrets-read-managed-policy` and name the three modules, the three managed policy names, the three export names, and Account: account-wide-infrastructure.yml v2.1.0
    - State that each policy allows exactly `secretsmanager:GetSecretValue` and `secretsmanager:DescribeSecret` in one statement, guarded by the tag-match and tag-presence conditions, and that `ListSecrets` and `BatchGetSecretValue` are not granted
    - Add an update-time note that no pipeline template changed and that roles and secrets must carry the matching `atlantis:*` tags
    - Follow the formatting of the v0.0.46 entries
    - _Requirements: 4.1, 4.2, 4.4, 4.5, 10.1, 10.2, 10.3, 10.7, 7.1_

  - [x] 5.2 Update `docs/templates/v2/account/account-wide-infrastructure-README.md`
    - Read the whole file first and preserve all existing blockquotes and custom sections
    - Update the header version and date, add three Resources sections and six Outputs sections in the documented structure, and extend the table of contents lists
    - In each of the three Resources sections, document the single `ReadSecretTagMatch` statement that allows exactly `secretsmanager:GetSecretValue` and `secretsmanager:DescribeSecret` under the tag-match and tag-presence conditions, and state that `ListSecrets` and `BatchGetSecretValue` are not granted
    - Add the originating answer and the trade-off against name-pattern ARN scoping from the requirements Introduction
    - Add guidance with the tag value format per level, how roles and secrets obtain the tags, and an example passing an exported ARN to `CloudFormationSvcRoleIncludeManagedPolicyArns`, `CodeBuildSvcRoleIncludeManagedPolicyArns`, or `PostDeploySvcRoleIncludeManagedPolicyArns`
    - State that no pipeline template and not `templates/v2/modules/pipeline/cloudformation-svc-role.yml` changed, that untagged roles and secrets get no access, that `kms:Decrypt` for customer managed keys is not granted, that permissions boundaries still apply, and that tag-write permission on secrets and roles must be restricted (for example by a service control policy)
    - Document the design's two assumptions as prerequisites to verify: pipeline role tags come from outside this repository, and CloudFormation `{{resolve:secretsmanager:...}}` identity and tag evaluation needs a one-time manual check
    - Verify every new resource, output, and parameter reference matches the template
    - _Requirements: 4.1, 4.2, 4.4, 4.5, 10.4, 10.7, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

  - [x] 5.3 Update `docs/templates/v2/account/README.md`
    - Add a description of the secrets read managed policies to the account-wide template overview, linking to the template README, and preserve existing content
    - _Requirements: 10.5, 10.6, 10.7_

## Notes

- Test sub-tasks are required, not optional, because Requirement 8 makes them part of the feature and the repository prefers fast unit tests as the primary mechanism
- No property-based tests are planned; the design's Correctness Properties are covered by parametrized example-based tests
- Task 5 is the final task and is required
- Run Python commands through `.venv` (see the `python-virtual-environment` steering file)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1", "3.1"] },
    { "id": 2, "tasks": ["2.2"] },
    { "id": 3, "tasks": ["3.2"] },
    { "id": 4, "tasks": ["5.1", "5.2", "5.3"] }
  ]
}
```
