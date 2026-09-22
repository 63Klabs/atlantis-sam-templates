# Requirements Document

## Introduction

This feature adds account-wide Amazon Bedrock model invocation logging infrastructure to
`templates/v2/account/account-wide-infrastructure.yml`. It provisions the CloudWatch Logs
log group and the IAM role (with a least-privilege inline policy) that Amazon Bedrock
requires in order to publish model invocation logs to CloudWatch Logs.

The feature is modeled after the existing account-wide API Gateway CloudWatch logging
feature (`EnableApiGwCloudWatchLogs`, `apigw-cloudwatch-role.yml`,
`apigw-cloudwatch-account.yml`) and the account-wide S3 access log bucket feature
(`EnableS3AccessLogBucket`, `LogExpirationInDays`). Like both of those, it is a one-time,
per-account, per-region setup assembled from reusable `AWS::Include` module snippets.

**Critical scope constraint.** Unlike API Gateway — which has a native
`AWS::ApiGateway::Account` resource to attach the CloudWatch role account-wide — Amazon
Bedrock has **no native CloudFormation resource type** for the model invocation logging
configuration. That setting is only reachable through the
`PutModelInvocationLoggingConfiguration` API (console, CLI, or SDK); AWS's own reference
CloudFormation pattern uses a Lambda-backed custom resource to call it. This spec
deliberately does **not** introduce a Lambda-backed custom resource. Instead, the template
creates only the CloudFormation-native prerequisites (log group + role/policy), and
activation is a documented post-deployment CLI step — the same "deploy, then complete a
manual step" pattern the template already uses for the GitHub CodeConnections connection.

All changes are additive and backward compatible: new optional parameters (all with
defaults), new conditional resources, and new conditional outputs. No existing parameters,
resources, outputs, or exports are renamed or removed.

### Reference Documentation

- [Monitor model invocation using CloudWatch Logs and Amazon S3](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html) — the required log group, trust policy, and role policy shapes
- [PutModelInvocationLoggingConfiguration API reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_PutModelInvocationLoggingConfiguration.html) — the activation API
- [Configure model invocation logging in Amazon Bedrock by using AWS CloudFormation](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/configure-bedrock-invocation-logging-cloudformation.html) — AWS reference pattern confirming a custom resource is required for activation
- [Encrypt log data in CloudWatch Logs using AWS KMS](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html) — symmetric-key-only constraint and required key policy grant

### Confirmed Design Decisions

These decisions were raised with the maintainer and explicitly confirmed. They are recorded
here so the design document does not revisit them.

| # | Decision | Confirmed outcome |
|---|----------|-------------------|
| 1 | Log group naming | Include `OrgPrefix`; use `/aws/bedrock/${OrgPrefix}-ModelInvocations` (Req 5.4) |
| 2 | Retention parameter | New `BedrockInvocationLogExpirationInDays`, default `180`, but constrained by `AllowedValues` rather than `MinValue`/`MaxValue` because CloudWatch Logs accepts only enumerated retention values (Req 2.3) |
| 3 | Enable switch | New `EnableBedrockInvocationLogs`, default `"true"`, modeled on `EnableS3AccessLogBucket`, all provisioning gated behind conditions (Req 1) |
| 4 | KMS encryption | In scope and optional; bring-your-own symmetric key via `BedrockInvocationLogKmsKeyArn` (Req 3) |
| 5 | IAM trust policy shape | Follow AWS's documented Bedrock trust policy (with `aws:SourceAccount` / `aws:SourceArn` confused-deputy guards) and a least-privilege inline policy, rather than copying the condition-free, managed-policy-based API Gateway role verbatim (Req 6) |
| 6 | Log group deletion policy | `Retain` — deliberate choice for audit durability, diverging from the pipeline log group modules' `Delete` (Req 5.7) |
| 7 | Activation mechanism | Documented post-deployment CLI step; no Lambda-backed custom resource (Req 9, Req 10) |
| 8 | External documentation | Generate `docs/admin-ops/bedrock-model-invocation-logging.md` for manual copy-over into the External_Docs_Repo (Req 10) |
| 9 | Large data delivery to S3 | **Out of scope.** No `largeDataDeliveryS3Config`. This feature targets debugging, not durable capture of oversized or binary payloads. The 100 KB CloudWatch limit is a documented, deliberate limitation (Req 14.4, Req 10.10) |
| 10 | `OrgPrefix` casing in the log group name | Uppercase is correct and **preferred** for account-wide infrastructure; the log group resolves to e.g. `/aws/bedrock/ACME-ModelInvocations` (Req 5.4) |
| 11 | Data delivery modalities | **Text and embedding only.** `imageDataDeliveryEnabled` and `videoDataDeliveryEnabled` are `false` by default, as a deliberate choice documented alongside the 100 KB limitation (Req 8.4, Req 10.5) |

## Glossary

- **Account_Wide_Template**: The parent template at `templates/v2/account/account-wide-infrastructure.yml` (currently `v2.0.1/2026-08-20`).
- **Module**: A YAML snippet under `templates/v2/modules/` defining a single resource body (no logical ID, no `Resources:` wrapper), spliced into a parent via `Fn::Transform: AWS::Include`. Modules must use long-form intrinsics only.
- **Bedrock_Log_Group_Module**: The new module at `templates/v2/modules/account-wide/bedrock-cloudwatch-log-group.yml`.
- **Bedrock_Role_Module**: The new module at `templates/v2/modules/account-wide/bedrock-cloudwatch-role.yml`.
- **Model_Invocation_Logging**: The per-account, per-region Amazon Bedrock feature that publishes request/response/metadata for `Converse`, `ConverseStream`, `InvokeModel`, and `InvokeModelWithResponseStream` calls made through the `bedrock-runtime` endpoint.
- **Activation_Command**: The post-deployment `aws bedrock put-model-invocation-logging-configuration` CLI call that turns Model_Invocation_Logging on using the log group and role created by this feature.
- **Bedrock_Log_Stream_Name**: The fixed log stream name Amazon Bedrock writes to within the log group: `aws/bedrock/modelinvocations`.
- **Admin_Ops_Doc**: The new comprehensive Markdown document generated by this spec at `docs/admin-ops/bedrock-model-invocation-logging.md`, intended for manual copy-over into the external `atlantis-platform-admin` documentation repository.
- **External_Docs_Repo**: The separate documentation repository at https://github.com/63Klabs/atlantis-platform-admin, referenced from `docs/admin-ops/account-management.md`. This repository cannot write to it; content must be copied manually by the maintainer.
- **OrgPrefix**: The existing required account-wide parameter used to name and export account-wide resources (e.g. `${OrgPrefix}-ApiGateway-CloudWatch-Role-Arn`).

## Requirements

### Requirement 1: Add the `EnableBedrockInvocationLogs` parameter

**User Story:** As a platform administrator, I want a single switch that provisions the Bedrock model invocation logging prerequisites, so that I can enable or opt out of the feature per account and region.

#### Acceptance Criteria

1. THE Account_Wide_Template SHALL add an `EnableBedrockInvocationLogs` parameter of type String.
2. THE `EnableBedrockInvocationLogs` parameter SHALL use `Default: "true"`, `AllowedValues: ["true", "false"]`, and `ConstraintDescription: "Must be 'true' or 'false'."`, matching the definition style of `EnableS3AccessLogBucket`.
3. THE `EnableBedrockInvocationLogs` parameter `Description` SHALL state that it creates the CloudWatch Logs log group and IAM role required for Amazon Bedrock model invocation logging, that this is a one-time per-account per-region setup, AND that a post-deployment CLI step is required to activate logging.
4. THE Account_Wide_Template SHALL define a condition named `EnableBedrockInvocationLogs` equal to `!Equals [!Ref EnableBedrockInvocationLogs, "true"]`, following the existing convention where the condition name matches the parameter name (as with `EnableS3ArtifactsBucket` and `EnableS3AccessLogBucket`).
5. WHEN `EnableBedrockInvocationLogs` is `"false"`, THE template SHALL create no Bedrock logging resources and SHALL emit no Bedrock logging outputs, and deployment SHALL succeed without error.

### Requirement 2: Add the `BedrockInvocationLogExpirationInDays` parameter

**User Story:** As a platform administrator, I want to control how long model invocation logs are retained, so that I can balance auditability against CloudWatch Logs storage cost.

#### Acceptance Criteria

1. THE Account_Wide_Template SHALL add a `BedrockInvocationLogExpirationInDays` parameter of type Number.
2. THE `BedrockInvocationLogExpirationInDays` parameter SHALL use `Default: 180`, following the same definition format as the existing `LogExpirationInDays` parameter.
3. THE `BedrockInvocationLogExpirationInDays` parameter SHALL use `AllowedValues` restricted to the enumerated set accepted by the `AWS::Logs::LogGroup` `RetentionInDays` property: `[1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653]`.
   - Rationale (user-confirmed): this is a deliberate divergence from `LogExpirationInDays`, which uses `MinValue: 1` / `MaxValue: 365` because it drives an S3 lifecycle rule that accepts any day count. CloudWatch Logs accepts only the enumerated values above, so `MinValue`/`MaxValue` would permit values that fail at deploy time.
   - THE default of `180` SHALL be a member of the `AllowedValues` set.
4. THE `BedrockInvocationLogExpirationInDays` parameter `Description` SHALL explain that it sets the CloudWatch Logs retention for the model invocation log group, SHALL note that it only applies when `EnableBedrockInvocationLogs` is `"true"`, AND SHALL note the cost implication of longer retention.
5. THE `BedrockInvocationLogExpirationInDays` parameter `ConstraintDescription` SHALL state that the value must be one of the permitted CloudWatch Logs retention values.

### Requirement 3: Add optional KMS encryption for the log group

**User Story:** As a platform administrator with compliance obligations, I want to encrypt model invocation logs with my own KMS key, so that prompt and response content is protected by a key I control.

#### Acceptance Criteria

1. THE Account_Wide_Template SHALL add a `BedrockInvocationLogKmsKeyArn` parameter of type String with `Default: ""` so that KMS encryption is optional and off by default.
2. THE `BedrockInvocationLogKmsKeyArn` parameter SHALL use an `AllowedPattern` that accepts either an empty string or a KMS key ARN.
3. THE Account_Wide_Template SHALL define a condition named `HasBedrockInvocationLogKmsKey` equal to `!Not [!Equals [!Ref BedrockInvocationLogKmsKeyArn, ""]]`.
4. WHEN `BedrockInvocationLogKmsKeyArn` is non-empty, THE Bedrock_Log_Group_Module SHALL set the log group's `KmsKeyId` property to that value.
5. WHEN `BedrockInvocationLogKmsKeyArn` is empty, THE Bedrock_Log_Group_Module SHALL omit `KmsKeyId` entirely using `Ref: "AWS::NoValue"`, so the log group uses CloudWatch Logs default encryption.
6. THE `BedrockInvocationLogKmsKeyArn` parameter `Description` SHALL state that the key must be a **symmetric** KMS key in the same region, AND that the key policy must grant the `logs.<region>.amazonaws.com` service principal `kms:Encrypt`, `kms:Decrypt`, `kms:ReEncrypt*`, `kms:GenerateDataKey*`, and `kms:Describe*`.
7. THE template SHALL NOT create or modify a KMS key or key policy; the key is supplied by the operator as an existing resource (bring-your-own-key).

### Requirement 4: Parameter grouping and metadata

**User Story:** As a platform administrator filling out stack parameters in the console, I want the Bedrock logging parameters grouped together, so that the related settings are obvious.

#### Acceptance Criteria

1. THE Account_Wide_Template `AWS::CloudFormation::Interface` metadata SHALL add a new parameter group with the label `"Bedrock Model Invocation Logs"`.
2. THE new parameter group SHALL list `EnableBedrockInvocationLogs`, `BedrockInvocationLogExpirationInDays`, and `BedrockInvocationLogKmsKeyArn`, in that order.
3. THE new parameter group SHALL be positioned after the `"S3 Access Log Bucket"` group and before the `"Promotion"` group, keeping logging-related groups adjacent.
4. All three new parameters SHALL appear in exactly one parameter group.

### Requirement 5: Create the Bedrock CloudWatch log group module

**User Story:** As a platform administrator, I want a dedicated log group for model invocation logs, so that Bedrock has a destination to publish to and I can apply retention and metric filters to it.

#### Acceptance Criteria

1. THE Bedrock_Log_Group_Module SHALL be created at `templates/v2/modules/account-wide/bedrock-cloudwatch-log-group.yml`.
2. THE Bedrock_Log_Group_Module SHALL define a single `AWS::Logs::LogGroup` resource body with no logical ID and no `Resources:` wrapper.
3. THE Bedrock_Log_Group_Module SHALL carry `Condition: EnableBedrockInvocationLogs`.
4. THE log group `LogGroupName` SHALL be `Fn::Sub: "/aws/bedrock/${OrgPrefix}-ModelInvocations"`, which combines the AWS `/aws/<service>/` log group path convention (consistent with the existing `/aws/codebuild/...` log group modules) with the account-wide `OrgPrefix` naming convention and a Pascal-case resource identifier.
   - Note (user-confirmed): because `OrgPrefix` is constrained to UPPER CASE, the resolved name contains an uppercase segment (e.g. `/aws/bedrock/ACME-ModelInvocations`). This is valid for CloudWatch Logs and is the **preferred** form for account-wide infrastructure.
5. THE log group `RetentionInDays` SHALL be `Ref: BedrockInvocationLogExpirationInDays`.
6. THE log group `KmsKeyId` SHALL be conditional per Requirement 3.4 and 3.5.
7. THE Bedrock_Log_Group_Module SHALL set `DeletionPolicy: Retain` and `UpdateReplacePolicy: Retain`, so that audit log data is not destroyed when the feature is disabled or the stack is deleted.
   - Rationale (user-confirmed): this is a **deliberate choice for audit durability** and a deliberate divergence from the pipeline log group modules (`promote-log-group.yml`, `codebuild-log-group.yml`, `postdeploy-log-group.yml`), which use `DeletionPolicy: Delete` because build logs are transient. Model invocation logs are audit records containing prompt and response content and SHALL survive stack deletion or feature disablement.
   - THE consequence SHALL be documented: because the log group is retained, re-enabling the feature (or redeploying after deletion) against the same `OrgPrefix` and region will encounter an already-existing log group, which CloudFormation will report as a create conflict. Operators must either delete the retained log group manually or import it.
8. THE Bedrock_Log_Group_Module SHALL use long-form intrinsic functions only (`Fn::Sub`, `Ref`, `Fn::If`).
9. THE Bedrock_Log_Group_Module SHALL open with a contract comment block declaring the required parent parameters (`OrgPrefix`, `BedrockInvocationLogExpirationInDays`, `BedrockInvocationLogKmsKeyArn`) and required parent conditions (`EnableBedrockInvocationLogs`, `HasBedrockInvocationLogKmsKey`), and noting that `AWS::Include` does not support YAML shorthand tags.

### Requirement 6: Create the Bedrock CloudWatch IAM role module

**User Story:** As a platform administrator, I want a least-privilege IAM role that only Amazon Bedrock in my own account can assume, so that Bedrock can write invocation logs without granting broader access.

#### Acceptance Criteria

1. THE Bedrock_Role_Module SHALL be created at `templates/v2/modules/account-wide/bedrock-cloudwatch-role.yml`.
2. THE Bedrock_Role_Module SHALL define a single `AWS::IAM::Role` resource body with no logical ID and no `Resources:` wrapper.
3. THE Bedrock_Role_Module SHALL carry `Condition: EnableBedrockInvocationLogs`.
4. THE role trust policy SHALL allow `sts:AssumeRole` for `Principal.Service: bedrock.amazonaws.com`.
5. THE role trust policy SHALL include a confused-deputy guard: a `StringEquals` condition on `aws:SourceAccount` equal to `${AWS::AccountId}`, AND an `ArnLike` condition on `aws:SourceArn` equal to `arn:${AWS::Partition}:bedrock:${AWS::Region}:${AWS::AccountId}:*`, per the AWS-documented Bedrock logging trust policy.
6. THE role SHALL use `Path: !Ref RolePath` to honor the template's existing IAM path convention.
7. THE role SHALL grant permissions via an **inline** policy (not an AWS managed policy), because no AWS managed policy exists for Bedrock invocation logging; the inline policy SHALL grant exactly `logs:CreateLogStream` and `logs:PutLogEvents`.
8. THE inline policy `Resource` SHALL be scoped to the created log group and the Bedrock_Log_Stream_Name, resolving to `arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/bedrock/${OrgPrefix}-ModelInvocations:log-stream:aws/bedrock/modelinvocations`.
9. THE inline policy SHALL NOT use wildcard actions (`logs:*`) or a wildcard resource (`"*"`).
10. THE Bedrock_Role_Module SHALL use long-form intrinsic functions only.
11. THE Bedrock_Role_Module SHALL open with a contract comment block declaring the required parent parameters (`OrgPrefix`, `RolePath`) and required parent condition (`EnableBedrockInvocationLogs`), naming any sibling logical ID it depends on, and noting the `AWS::Include` shorthand restriction.
12. THE Bedrock_Role_Module contract comment SHALL reference the AWS documentation URL for Bedrock model invocation logging.

### Requirement 7: Wire the modules into the Account_Wide_Template

**User Story:** As a platform administrator, I want the new modules assembled by the account-wide template, so that one stack deployment provisions everything.

#### Acceptance Criteria

1. THE Account_Wide_Template SHALL add a resource with logical ID `BedrockModelInvocationLogGroup` that consumes the Bedrock_Log_Group_Module via `Fn::Transform: AWS::Include`.
2. THE Account_Wide_Template SHALL add a resource with logical ID `BedrockCloudWatchLogsRole` that consumes the Bedrock_Role_Module via `Fn::Transform: AWS::Include`.
3. Both new resources SHALL load their module from `!Sub "s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/account-wide/<module-file>"`, matching the existing module reference pattern.
4. Both new resources SHALL be placed in the `Resources` section adjacent to the existing API Gateway CloudWatch resources, each preceded by a `# -- ... (Conditional) --` comment consistent with the surrounding style.
5. IF the role's inline policy references the log group only by constructed ARN string (not `Fn::GetAtt`), THEN no `DependsOn` between the two resources is required; otherwise the parent SHALL declare the appropriate `DependsOn`.

### Requirement 8: Outputs and exports

**User Story:** As a platform administrator, I want the log group name and role ARN surfaced as outputs, so that I can paste them into the activation command and reference them from other stacks.

#### Acceptance Criteria

1. THE Account_Wide_Template SHALL add an output for the log group name, conditional on `EnableBedrockInvocationLogs`, exported as `${OrgPrefix}-Bedrock-CloudWatch-LogGroup-Name`.
2. THE Account_Wide_Template SHALL add an output for the log group ARN, conditional on `EnableBedrockInvocationLogs`, exported as `${OrgPrefix}-Bedrock-CloudWatch-LogGroup-Arn`.
3. THE Account_Wide_Template SHALL add an output for the role ARN, conditional on `EnableBedrockInvocationLogs`, exported as `${OrgPrefix}-Bedrock-CloudWatch-Role-Arn`, following the existing `${OrgPrefix}-ApiGateway-CloudWatch-Role-Arn` export convention.
4. THE Account_Wide_Template SHALL add a non-exported output, conditional on `EnableBedrockInvocationLogs`, containing the ready-to-run Activation_Command with the log group name and role ARN already substituted, so the administrator can copy and run it directly.
   - THE embedded logging configuration SHALL set `textDataDeliveryEnabled: true` and `embeddingDataDeliveryEnabled: true`.
   - THE embedded logging configuration SHALL set `imageDataDeliveryEnabled: false` and `videoDataDeliveryEnabled: false`.
   - Rationale (user-confirmed): text and embedding delivery is the **deliberate default posture**. Image and video payloads are typically binary and therefore cannot be carried by a CloudWatch Logs destination at all without the out-of-scope `largeDataDeliveryS3Config` (see Req 14.4), so enabling them would imply coverage the feature does not provide.
   - THE output `Description` SHALL state that the toggles are deliberate defaults and that an administrator may enable additional modalities by editing the command.
5. THE Account_Wide_Template SHALL add a non-exported output, conditional on `EnableBedrockInvocationLogs`, containing a CloudWatch console deep link to the created log group, consistent with the template's existing console-link outputs.
6. All new outputs SHALL include a `Description` explaining the value and how it is used.

### Requirement 9: Document the manual activation step in the template header

**User Story:** As a platform administrator reading the template, I want the required post-deployment step stated in the template itself, so that I do not assume logging is active after a successful deploy.

#### Acceptance Criteria

1. THE Account_Wide_Template header comment area SHALL be updated to document the Bedrock model invocation logging feature and its required manual activation step.
2. THE header comment SHALL state explicitly that deploying this stack does **not** by itself enable model invocation logging, and that logging remains disabled until the Activation_Command is run.
3. THE header comment SHALL explain why the manual step exists: Amazon Bedrock exposes no native CloudFormation resource for the logging configuration, and this template intentionally avoids a Lambda-backed custom resource.
4. THE header comment SHALL include the Activation_Command in copy-adaptable form, referencing the output names that supply the log group name and role ARN.
5. THE header comment SHALL note that the setting is per-account and per-region, and that it must be re-run in each region where Bedrock is used.
6. THE header comment SHALL point to the Admin_Ops_Doc and to the AWS documentation URL for fuller detail.
7. THE existing header comment content (author, version line format, GitHub links, existing feature descriptions) SHALL be preserved; only additive content SHALL be introduced, except for the version line which is governed by Requirement 12.

### Requirement 10: Generate the Admin_Ops_Doc for the External_Docs_Repo

**User Story:** As the platform maintainer, I want a complete, standalone Markdown write-up of this feature, so that I can copy it into the separate administration documentation repository without rewriting it.

#### Acceptance Criteria

1. THE spec SHALL produce a new Markdown document at `docs/admin-ops/bedrock-model-invocation-logging.md`.
2. THE Admin_Ops_Doc SHALL open with a note stating that it is authored for copy-over into the External_Docs_Repo, and identifying that repository by URL.
3. THE Admin_Ops_Doc SHALL document the prerequisites: the account-wide stack deployed with `EnableBedrockInvocationLogs` set to `"true"`, required caller IAM permissions for the Activation_Command, and the optional KMS key requirements from Requirement 3.6.
4. THE Admin_Ops_Doc SHALL document what the stack creates (log group, role, inline policy) and explicitly what it does not do (activate logging).
5. THE Admin_Ops_Doc SHALL provide the complete Activation_Command with clearly marked placeholders, covering the `cloudWatchConfig` `logGroupName` and `roleArn` fields and all four data delivery toggles.
   - THE documented command SHALL use `textDataDeliveryEnabled: true`, `embeddingDataDeliveryEnabled: true`, `imageDataDeliveryEnabled: false`, and `videoDataDeliveryEnabled: false`, matching the stack output from Req 8.4.
   - THE Admin_Ops_Doc SHALL explain that this posture is **deliberate**, not an oversight, and SHALL explain the reasoning (binary image/video payloads cannot be delivered to CloudWatch Logs without the out-of-scope S3 large data delivery configuration).
   - THE Admin_Ops_Doc SHALL explain how an administrator may opt into image or video delivery, and SHALL warn that doing so without an S3 large data delivery target will not produce the expected payloads.
6. THE Admin_Ops_Doc SHALL document how to verify the configuration using `aws bedrock get-model-invocation-logging-configuration`, including what a correct response looks like.
7. THE Admin_Ops_Doc SHALL document how to disable logging using `aws bedrock delete-model-invocation-logging-configuration`, and SHALL note that the log group is retained (per Requirement 5.7) so previously collected logs survive.
8. THE Admin_Ops_Doc SHALL document the per-account, per-region scope, including the need to repeat activation per region.
9. THE Admin_Ops_Doc SHALL document cost and data-sensitivity considerations: invocation logs contain full prompt and response content, CloudWatch Logs ingestion and storage are billable, and retention is controlled by `BedrockInvocationLogExpirationInDays`.
10. THE Admin_Ops_Doc SHALL document the known limitations, and SHALL frame them as deliberate scope choices rather than defects:
    - Only calls through the `bedrock-runtime` endpoint are captured.
    - A CloudWatch Logs destination carries invocation metadata plus input/output JSON bodies **only up to 100 KB**; binary data and bodies larger than 100 KB are supported only via an Amazon S3 destination, which is out of scope for this feature (Req 14.4).
    - Consequently this feature is intended for **debugging and audit of text and embedding invocations**, not for durable capture of oversized or binary payloads.
11. THE Admin_Ops_Doc SHALL include a troubleshooting section covering at minimum: `ValidationException` when the role or log group is wrong or missing, `AccessDeniedException` on the Activation_Command, and logs not appearing after successful activation.
12. THE Admin_Ops_Doc SHALL attribute AWS documentation sources with inline links.
13. THE `docs/admin-ops/account-management.md` file SHALL be updated to link to the Admin_Ops_Doc, preserving its existing content.

### Requirement 11: Update end-user template documentation

**User Story:** As a user of the account-wide template, I want the generated documentation to describe the new parameters, resources, and outputs, so that the README matches the template.

#### Acceptance Criteria

1. THE `docs/templates/v2/account/account-wide-infrastructure-README.md` file SHALL be updated to document the new `"Bedrock Model Invocation Logs"` parameter group and all three new parameters, following the established structure (group heading, parameter table of contents, per-parameter attribute tables).
2. THE README SHALL document the two new resources (`BedrockModelInvocationLogGroup`, `BedrockCloudWatchLogsRole`) including their types and conditions.
3. THE README SHALL document all new outputs and their export names.
4. THE README SHALL include a blockquote warning that deployment alone does not activate logging and that the Activation_Command is required, linking to the Admin_Ops_Doc.
5. THE README SHALL note the data-sensitivity and cost considerations for invocation logs.
6. All existing blockquotes and custom content in the README SHALL be preserved.
7. THE `docs/templates/v2/account/README.md` category README SHALL be updated only if its template descriptions or parameter summaries are affected by this change.

### Requirement 12: Versioning

**User Story:** As a maintainer, I want the template version incremented per the repository version-control rules, so that the change is traceable.

#### Acceptance Criteria

1. THE Account_Wide_Template version SHALL be incremented from `v2.0.1` to `v2.0.2` with the current date, since PATCH > 0 and the change is additive and non-breaking.
2. THE version increment SHALL be performed as the first implementation task, before other template edits.
3. Only the `# Version:` line SHALL change as part of the version increment; other header content changes are governed by Requirement 9.
4. THE new modules SHALL NOT carry individual version numbers, consistent with existing modules.

### Requirement 13: Changelog

**User Story:** As a user of these templates, I want the changelog to record this feature, so that I know which release introduced it.

#### Acceptance Criteria

1. THE `CHANGELOG.md` SHALL add an entry under the `v0.0.43 - unreleased` section in the `### Added` category.
2. THE entry SHALL reference this spec directory as `[Spec: 0-0-43-enable-account-model-logs](.kiro/specs/0-0-43-enable-account-model-logs/)`.
3. THE entry SHALL list the modified Account_Wide_Template with its new version (`v2.0.2`) and the two new modules as sub-bullets.
4. THE entry SHALL mention the required post-deployment activation step, since it affects end users.
5. Existing changelog text SHALL NOT be modified.

### Requirement 14: Deployment behavior, non-goals, and error handling

**User Story:** As a platform administrator, I want predictable behavior in edge cases and a clear statement of what this feature does not cover, so that I am not surprised after deployment.

#### Acceptance Criteria

1. WHEN `EnableBedrockInvocationLogs` is `"true"` in a region where Amazon Bedrock is not available, THE stack deployment SHALL still succeed, because the created resources (`AWS::Logs::LogGroup`, `AWS::IAM::Role`) are not Bedrock-service resources and require no Bedrock API call at deploy time. THE Admin_Ops_Doc SHALL note that the Activation_Command will fail in such a region.
2. WHEN an existing account-wide stack is updated and `EnableBedrockInvocationLogs` retains its `"true"` default, THE update SHALL create the log group and role even if the account does not use Bedrock. THE documentation SHALL note that an empty log group and an unused IAM role incur no charges, and that operators who want neither may set the parameter to `"false"`.
3. WHEN `EnableBedrockInvocationLogs` is changed from `"true"` to `"false"` on an existing stack, THE role SHALL be deleted and THE log group SHALL be retained per Requirement 5.7, and THE stack update SHALL succeed.
4. THE following SHALL be explicitly out of scope for this spec and SHALL be stated as non-goals in the design document:
   - Any Lambda-backed custom resource or other mechanism that calls `PutModelInvocationLoggingConfiguration` from within CloudFormation.
   - An Amazon S3 logging destination for model invocation logs (`s3Config`), including the associated bucket policy granting `bedrock.amazonaws.com` write access.
   - Large data delivery to Amazon S3 (`cloudWatchConfig.largeDataDeliveryS3Config`) and the `s3:PutObject` role permission it would require. Confirmed with the maintainer: this feature is for debugging, so storing oversized or binary payloads is not a goal. The resulting 100 KB ceiling SHALL be documented per Req 10.10.
   - ABAC-scoped managed policies granting project pipelines permission to create or invoke Bedrock resources (this feature concerns account-wide logging infrastructure only).
   - Creation or modification of a KMS key or key policy (Req 3.7).
   - CloudWatch metric filters, alarms, or dashboards over the invocation log group.
5. THE design document SHALL state that this feature creates only CloudFormation-native resources and introduces no new resource types beyond `AWS::Logs::LogGroup` and `AWS::IAM::Role`.

### Requirement 15: Validation and testing

**User Story:** As a maintainer, I want fast automated checks on the new template and modules, so that I have confidence the change is structurally valid.

#### Acceptance Criteria

1. THE modified Account_Wide_Template SHALL pass `cfn-lint` using the repository's existing linter configuration and existing ignore checks (E3001, E3005, E6101, W2001, W8001); no new suppressions SHALL be added unless a specific finding requires it.
2. THE repository SHALL add fast unit tests asserting the new parameter definitions (type, default, allowed values/pattern, constraint description) and the new conditions.
3. THE unit tests SHALL assert the new metadata parameter group label, its membership, and its position relative to the `"S3 Access Log Bucket"` and `"Promotion"` groups.
4. THE unit tests SHALL assert the Bedrock_Log_Group_Module structure: single resource body, type, condition, log group name pattern, retention `Ref`, conditional `KmsKeyId` with `AWS::NoValue` fallback, and `Retain` policies.
5. THE unit tests SHALL assert the Bedrock_Role_Module structure: single resource body, type, condition, `bedrock.amazonaws.com` trust principal, presence of both `aws:SourceAccount` and `aws:SourceArn` conditions, exactly the two permitted `logs:` actions, absence of wildcard action and wildcard resource, and the log-stream-scoped resource ARN.
6. THE unit tests SHALL assert that both new modules contain no YAML shorthand intrinsic tags and no `Resources:` wrapper or logical ID.
7. THE unit tests SHALL assert the new outputs exist with the expected export names and conditions.
8. THE unit tests SHALL assert the incremented version line in the Account_Wide_Template header.
9. Per the repository testing guidelines, tests SHALL be fast, concrete unit tests; no new property-based tests SHALL be added for this change.
10. THE full existing test suite SHALL continue to pass.

## Resolved Questions

All questions raised during requirements review have been answered by the maintainer. No open
questions remain.

### Q1. Large data delivery to S3 — in scope or explicit non-goal? — RESOLVED: non-goal

Per the [AWS logging destinations documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html),
a CloudWatch Logs destination carries invocation metadata plus input/output JSON bodies only up
to 100 KB; binary data and larger bodies require an Amazon S3 destination via
`cloudWatchConfig.largeDataDeliveryS3Config`.

**Decision:** out of scope. This feature exists primarily for **debugging**, so durable capture
of oversized or binary payloads is not a goal. Recorded in Req 14.4; the resulting limitation is
documented per Req 10.10.

### Q2. Log group name — `OrgPrefix` casing — RESOLVED: uppercase, preferred

**Decision:** the uppercase `OrgPrefix` segment is correct and is the **preferred** convention
for account-wide infrastructure. The log group resolves to e.g.
`/aws/bedrock/ACME-ModelInvocations`. Recorded in Req 5.4.

### Q3. Activation command data delivery toggles — RESOLVED: text and embedding only

**Decision:** `textDataDeliveryEnabled: true` and `embeddingDataDeliveryEnabled: true`;
`imageDataDeliveryEnabled: false` and `videoDataDeliveryEnabled: false`. This is a deliberate
choice and SHALL be documented as such, together with the 100 KB / binary limitation that
motivates it. Recorded in Req 8.4 and Req 10.5.
