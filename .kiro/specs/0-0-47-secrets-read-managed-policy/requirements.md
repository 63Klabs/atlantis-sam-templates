# Requirements Document

## Introduction

Pipeline stage service roles (the CloudFormation, CodeBuild, and PostDeploy service roles created by the pipeline templates) sometimes need to read Secrets Manager secrets. Examples are resolving `{{resolve:secretsmanager:...}}` dynamic references during a CloudFormation deployment, or fetching a token during a build or post-deployment step. Today the only way to grant this is a hand-written customer managed policy per application.

This feature adds three account-wide, read-only, ABAC-scoped IAM managed policies to `templates/v2/account/account-wide-infrastructure.yml`. Each policy is built from its own module in `templates/v2/modules/pipeline-policies/`, follows the pattern of the existing `codebuild-crud.yml` and `cognito-crud.yml` modules, and is exported so that administrators can pass its ARN to a pipeline template through the existing `CloudFormationSvcRoleIncludeManagedPolicyArns`, `CodeBuildSvcRoleIncludeManagedPolicyArns`, and `PostDeploySvcRoleIncludeManagedPolicyArns` parameters.

Each policy compares a tag on the secret with the same tag on the calling role (`aws:ResourceTag/atlantis:<Key>` equals `${aws:PrincipalTag/atlantis:<Key>}`). The three policies differ only in which tag key they compare, which sets the breadth of access:

| Level | Tag key | Tag value format | Reach |
|-------|---------|------------------|-------|
| Deployment | `atlantis:ApplicationDeploymentId` | `<Prefix>-<ProjectId>-<StageId>` | One deployment (one stage of one application) |
| Application | `atlantis:Application` | `<Prefix>-<ProjectId>` | All stages of one application |
| Prefix | `atlantis:Prefix` | `<Prefix>` | All applications under one prefix |

### Answer to the originating question

Yes. All three scoping levels (deployment, application, prefix) can be offered while remaining least privilege, because each level is a separate opt-in managed policy. An administrator attaches only the narrowest policy that a given pipeline role needs, and no policy grants more than read access to secrets whose tag value equals the calling role's own tag value.

Trade-off against name-pattern ARN scoping (for example `secret:<Prefix>-<ProjectId>-<StageId>-*`):

- Tag matching lets a single shared account-wide policy serve every deployment, because the value to match comes from the calling role (`${aws:PrincipalTag/...}`) and is not hard-coded in the policy. Name patterns need a policy per deployment or a broad wildcard.
- Tag matching does not depend on the secret name, so it works with secrets whose names do not follow the `Prefix-ProjectId-StageId-Resource` convention, and it avoids ambiguity between hyphenated names (a pattern such as `acme-pay-*` also matches `acme-pay-ments-prod-*`) and the random six-character suffix that Secrets Manager appends to secret ARNs.
- Name patterns cannot be changed by re-tagging, whereas tag matching is only as strong as control over who can set `atlantis:*` tags on secrets and on roles. The policies therefore require both tags to be present (fail closed), and the documentation states that tag-write permission on secrets and roles must be restricted.
- Tag matching requires secrets and roles to be tagged. Untagged secrets and untagged roles get no access, which is the intended failure mode.

Name-pattern scoping is not the control in this feature. A name pattern MAY be added by the design only as an additional, optional narrowing condition that never widens access.

## Glossary

- **Account_Wide_Template**: The CloudFormation template `templates/v2/account/account-wide-infrastructure.yml`.
- **Secrets_Read_Module**: One of the three module files in `templates/v2/modules/pipeline-policies/` that describes a single `AWS::IAM::ManagedPolicy` resource body for secrets read access.
- **Deployment_Policy**: The managed policy built from the Secrets_Read_Module that compares the `atlantis:ApplicationDeploymentId` tag.
- **Application_Policy**: The managed policy built from the Secrets_Read_Module that compares the `atlantis:Application` tag.
- **Prefix_Policy**: The managed policy built from the Secrets_Read_Module that compares the `atlantis:Prefix` tag.
- **Secrets_Read_Policy**: Any one of the Deployment_Policy, Application_Policy, or Prefix_Policy.
- **Pipeline_Stage_Role**: The CloudFormation service role, CodeBuild service role, or PostDeploy service role created by a pipeline template.
- **Scope_Tag_Key**: The tag key a Secrets_Read_Policy compares, which is `atlantis:ApplicationDeploymentId`, `atlantis:Application`, or `atlantis:Prefix`.
- **Principal_Tag**: A tag on the IAM role making the request, referenced as `aws:PrincipalTag/<Scope_Tag_Key>`.
- **Resource_Tag**: A tag on the Secrets Manager secret being read, referenced as `aws:ResourceTag/<Scope_Tag_Key>`.
- **OrgPrefix**: The Account_Wide_Template parameter that prefixes managed policy names and export names.
- **Test_Suite**: The fast unit tests under `tests/` that parse module and template YAML.
- **Documentation_Set**: The files `docs/templates/v2/account/account-wide-infrastructure-README.md`, `docs/templates/v2/account/README.md`, and `CHANGELOG.md`.

## Requirements

### Requirement 1: Three Separate Managed Policies

**User Story:** As an account administrator, I want three separate secrets-read managed policies, one per tag level, so that I can grant each pipeline role only the breadth of secrets access it needs.

#### Acceptance Criteria

1. THE Account_Wide_Template SHALL create exactly three new `AWS::IAM::ManagedPolicy` resources named Deployment_Policy, Application_Policy, and Prefix_Policy, each created through `AWS::Include` from its own Secrets_Read_Module.
2. THE Secrets_Read_Module for the Deployment_Policy SHALL be the file `templates/v2/modules/pipeline-policies/secrets-read-deployment.yml`.
3. THE Secrets_Read_Module for the Application_Policy SHALL be the file `templates/v2/modules/pipeline-policies/secrets-read-application.yml`.
4. THE Secrets_Read_Module for the Prefix_Policy SHALL be the file `templates/v2/modules/pipeline-policies/secrets-read-prefix.yml`.
5. THE Account_Wide_Template SHALL create the three Secrets_Read_Policy resources unconditionally.
6. THE Account_Wide_Template SHALL assign the Deployment_Policy, Application_Policy, and Prefix_Policy each a distinct logical ID defined in the design document.

### Requirement 2: Tag-Match Scoping by Level

**User Story:** As an account administrator, I want each policy to match a tag on the secret against the same tag on the calling role, so that access follows the Prefix/ProjectId/StageId hierarchy without hard-coding names.

#### Acceptance Criteria

1. THE Deployment_Policy SHALL allow access only WHEN the Resource_Tag `atlantis:ApplicationDeploymentId` equals the Principal_Tag `atlantis:ApplicationDeploymentId`.
2. THE Application_Policy SHALL allow access only WHEN the Resource_Tag `atlantis:Application` equals the Principal_Tag `atlantis:Application`.
3. THE Prefix_Policy SHALL allow access only WHEN the Resource_Tag `atlantis:Prefix` equals the Principal_Tag `atlantis:Prefix`.
4. THE Secrets_Read_Module SHALL express the tag comparison as a `StringEquals` condition whose left side is `aws:ResourceTag/<Scope_Tag_Key>` and whose right side is the policy variable `${aws:PrincipalTag/<Scope_Tag_Key>}`.
5. THE Secrets_Read_Module SHALL NOT embed a literal Prefix, ProjectId, or StageId value in the tag comparison.
6. THE Secrets_Read_Module SHALL compare exactly one Scope_Tag_Key per policy, so that a role needing broader access is granted a second policy and is not granted a widened first policy.

### Requirement 3: Fail Closed on Missing Tags

**User Story:** As a security reviewer, I want the policies to fail closed when tags are missing, so that an untagged role or an untagged secret never receives access.

#### Acceptance Criteria

1. IF the Principal_Tag for the Scope_Tag_Key is absent from the calling role, THEN THE Secrets_Read_Policy SHALL NOT allow any action.
2. IF the Resource_Tag for the Scope_Tag_Key is absent from the secret, THEN THE Secrets_Read_Policy SHALL NOT allow any action.
3. THE Secrets_Read_Module SHALL include an explicit `Null` condition with the value `"false"` on `aws:PrincipalTag/<Scope_Tag_Key>` in each Allow statement, so that the tag-presence guard does not rely only on policy-variable resolution behavior.
4. THE Secrets_Read_Module SHALL include an explicit `Null` condition with the value `"false"` on `aws:ResourceTag/<Scope_Tag_Key>` in each Allow statement.
5. THE Secrets_Read_Module SHALL contain no Allow statement without the tag-match condition and the tag-presence conditions.

### Requirement 4: Read-Only Least-Privilege Actions

**User Story:** As a security reviewer, I want the granted actions limited to reading secret values and describing secrets, so that pipeline roles cannot create, change, or delete secrets through these policies.

#### Acceptance Criteria

1. THE Secrets_Read_Module SHALL allow exactly the actions `secretsmanager:GetSecretValue` and `secretsmanager:DescribeSecret`.
2. THE Secrets_Read_Module SHALL list `secretsmanager:GetSecretValue` and `secretsmanager:DescribeSecret` together in the same single Allow statement, under the same `StringEquals` tag-match condition and both `Null` tag-presence conditions.
3. THE Secrets_Read_Module SHALL NOT allow any Secrets Manager action that creates, updates, deletes, rotates, restores, replicates, tags, untags, or sets a resource policy on a secret.
4. THE Secrets_Read_Module SHALL NOT allow `secretsmanager:ListSecrets`, because that action does not support resource-level conditions.
5. THE Secrets_Read_Module SHALL NOT allow `secretsmanager:BatchGetSecretValue`.
6. THE Secrets_Read_Module SHALL limit the `Resource` element to Secrets Manager secret ARNs in the account that owns the Account_Wide_Template stack, in the form `arn:<partition>:secretsmanager:*:<AccountId>:secret:*`.
7. THE Secrets_Read_Module SHALL NOT use `Action: "secretsmanager:*"` or `Action: "*"` in any statement.

### Requirement 5: Names, Exports, and Outputs

**User Story:** As an account administrator, I want consistent policy names, exports, and outputs, so that pipeline stacks can attach the policies the same way they attach the existing CodeBuild and Cognito policies.

#### Acceptance Criteria

1. THE Deployment_Policy SHALL have the managed policy name `${OrgPrefix}-ManagedPolicyForPipeline-SecretsReadDeployment`.
2. THE Application_Policy SHALL have the managed policy name `${OrgPrefix}-ManagedPolicyForPipeline-SecretsReadApplication`.
3. THE Prefix_Policy SHALL have the managed policy name `${OrgPrefix}-ManagedPolicyForPipeline-SecretsReadPrefix`.
4. THE Account_Wide_Template SHALL export the Deployment_Policy ARN under the name `${OrgPrefix}-ProjectPipeline-SecretsReadDeployment-Arn`.
5. THE Account_Wide_Template SHALL export the Application_Policy ARN under the name `${OrgPrefix}-ProjectPipeline-SecretsReadApplication-Arn`.
6. THE Account_Wide_Template SHALL export the Prefix_Policy ARN under the name `${OrgPrefix}-ProjectPipeline-SecretsReadPrefix-Arn`.
7. THE Account_Wide_Template SHALL define, for each Secrets_Read_Policy, an ARN output with a description that tells the reader to pass the value through a `*SvcRoleIncludeManagedPolicyArns` parameter, and a name output that matches the managed policy name.
8. THE Secrets_Read_Module SHALL set `Path` from the `RolePath` parameter, consistent with `codebuild-crud.yml` and `cognito-crud.yml`.
9. THE Secrets_Read_Module SHALL set a `Description` that states the policy is read-only and names the Scope_Tag_Key.
10. THE Account_Wide_Template SHALL NOT rename or remove any existing parameter, resource logical ID, output, or export.

### Requirement 6: Module Standards Compliance

**User Story:** As a module maintainer, I want the new modules to follow the repository module standards, so that they work with `AWS::Include` and stay maintainable.

#### Acceptance Criteria

1. THE Secrets_Read_Module SHALL describe a single resource body that starts at `Type: AWS::IAM::ManagedPolicy` and SHALL NOT contain a logical ID or a `Resources:` block.
2. THE Secrets_Read_Module SHALL use long-form intrinsic functions (`Fn::Sub`, `Ref`) and SHALL NOT use YAML shorthand tags.
3. THE Secrets_Read_Module SHALL open with a comment block stating the parent template must define the parameters `OrgPrefix` and `RolePath`.
4. THE Secrets_Read_Module SHALL give every statement a `Sid` that is unique within the module and that describes the statement.
5. THE Secrets_Read_Module SHALL document in comments the tag key compared, the expected tag value format, and the fail-closed behavior.

### Requirement 7: Role Tagging Guidance

**User Story:** As an account administrator, I want clear guidance on how roles obtain the principal tags, so that I can use the policies without changing any pipeline template.

#### Acceptance Criteria

1. THE Documentation_Set SHALL state that this feature changes no pipeline template and does not change the module `templates/v2/modules/pipeline/cloudformation-svc-role.yml`.
2. THE Documentation_Set SHALL state that the Pipeline_Stage_Role must carry the Scope_Tag_Key tag of each Secrets_Read_Policy attached to the Pipeline_Stage_Role, and SHALL give the tag value format for each level.
3. THE Documentation_Set SHALL state that the secret must carry the same Scope_Tag_Key tag, and SHALL state that an untagged role or secret receives no access.
4. THE Documentation_Set SHALL show how to attach a Secrets_Read_Policy by passing its exported ARN to the `CloudFormationSvcRoleIncludeManagedPolicyArns`, `CodeBuildSvcRoleIncludeManagedPolicyArns`, or `PostDeploySvcRoleIncludeManagedPolicyArns` parameter.
5. THE Documentation_Set SHALL state that a secret encrypted with a customer managed KMS key also requires `kms:Decrypt` on that key, which these policies do not grant.
6. THE Documentation_Set SHALL state that tag matching is only as strong as control over who may set `atlantis:*` tags on secrets and roles, and SHALL recommend restricting tag-write permission accordingly.
7. THE Documentation_Set SHALL include the answer to the originating question and the trade-off against name-pattern ARN scoping given in the Introduction of this document.

### Requirement 8: Unit Tests

**User Story:** As a maintainer, I want fast unit tests for the new modules and template wiring, so that regressions in the IAM statements are caught during development.

#### Acceptance Criteria

1. THE Test_Suite SHALL include a unit test file `tests/test_secrets_read_managed_policy_unit.py` that parses each Secrets_Read_Module as YAML.
2. THE Test_Suite SHALL verify for each Secrets_Read_Module that the resource type is `AWS::IAM::ManagedPolicy` and that the file contains no logical ID, no `Resources:` block, and no shorthand intrinsic tags.
3. THE Test_Suite SHALL verify for each Secrets_Read_Module that the managed policy name, the Scope_Tag_Key, and the `Description` match Requirements 2 and 5.
4. THE Test_Suite SHALL verify for each Secrets_Read_Module that every Allow statement carries the `StringEquals` tag-match condition and both `Null` tag-presence conditions defined in Requirements 2 and 3.
5. THE Test_Suite SHALL verify for each Secrets_Read_Module that the set of allowed actions equals exactly {`secretsmanager:GetSecretValue`, `secretsmanager:DescribeSecret`}, that both actions appear in the same single Allow statement, and that no action prohibited by Requirement 4 is present.
6. THE Test_Suite SHALL verify for each Secrets_Read_Module that the `Resource` element matches the account-scoped secret ARN form in Requirement 4.
7. THE Test_Suite SHALL verify that the Account_Wide_Template contains three `AWS::Include` resources that reference the three Secrets_Read_Module files, and three ARN outputs with the export names in Requirement 5.
8. THE Test_Suite SHALL verify that the Account_Wide_Template still contains the existing CodeBuild and Cognito resources, outputs, and exports unchanged.
9. THE Test_Suite SHALL verify that the Account_Wide_Template header version and date match Requirement 9.
10. THE Test_Suite SHALL complete in under 1 second per test and SHALL use unit tests as the primary mechanism, with no property-based tests required.
11. WHEN the repository CloudFormation lint test runs, THE Account_Wide_Template SHALL continue to pass cfn-lint.

### Requirement 9: Template Version and Date

**User Story:** As a maintainer, I want the template version and date updated, so that consumers can see the template changed.

#### Acceptance Criteria

1. WHEN the three Secrets_Read_Policy resources are added, THE Account_Wide_Template SHALL update the `# Version:` header date to the date of the change.
2. THE Account_Wide_Template SHALL keep its version number unchanged at `v2.1.0` while its PATCH component is 0, in accordance with the development-mode rule in `.kiro/steering/template-version-control.md`, and SHALL otherwise apply that rule's version increment for a non-breaking change.
3. THE Account_Wide_Template SHALL update its header comment to list the secrets read managed policies among the resources it assembles.
4. THE Account_Wide_Template SHALL update the `OrgPrefix` parameter description examples only if needed to remain accurate, and SHALL NOT change the parameter pattern, length, or default.

### Requirement 10: Changelog and Documentation

**User Story:** As a maintainer, I want the changelog and end-user documentation updated as the final task, so that the release notes and the template documentation match the change.

#### Acceptance Criteria

1. THE CHANGELOG SHALL contain the header `## v0.0.47 (unreleased)` above the `## v0.0.46 (2026-11-09)` header, and the header SHALL be created if absent.
2. THE CHANGELOG SHALL contain, under the `v0.0.47 (unreleased)` header, an `Added` entry that references the spec `0-0-47-secrets-read-managed-policy`, names the three new modules, the three managed policy names, the three export names, and the Account_Wide_Template version.
3. THE CHANGELOG SHALL contain an update-time note that no pipeline template changed and that roles and secrets must carry the matching `atlantis:*` tags.
4. THE `account-wide-infrastructure-README.md` SHALL document the three new resources in its Resources section, the six new outputs in its Outputs section, the updated version and date, and the security considerations in Requirement 7.
5. THE `docs/templates/v2/account/README.md` SHALL describe the secrets read managed policies in its overview of the account-wide template.
6. THE documentation update SHALL be the final task in the task list and SHALL be marked required.
7. WHEN the documentation files are edited, THE Documentation_Set SHALL preserve all existing blockquotes and custom sections.
