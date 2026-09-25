# Requirements Document

**Spec:** v0.0.44 Bedrock Invocation Logs Default Off

## Introduction

The `EnableBedrockInvocationLogs` parameter was introduced in v0.0.43 on `templates/v2/account/account-wide-infrastructure.yml` with a default of `"true"`. This spec changes that default to `"false"` and updates the documentation introduced in v0.0.43 to match.

Two things motivate the change. First, Bedrock model invocation logging is inherently opt-in even when the parameter is `"true"`: the stack only provisions the CloudWatch Logs log group and the IAM role, and logging does not actually start until an administrator runs the manual, per-account, per-region `aws bedrock put-model-invocation-logging-configuration` command surfaced by the `BedrockModelInvocationLoggingEnableCommand` output. A default of `"true"` therefore creates a log group and IAM role in every account that most deployments will never activate, providing no working logging in exchange for the extra resources. Second, model invocation logs capture full prompt and response content, which is frequently sensitive; a service that records that content should be enabled by deliberate choice rather than by default.

This also reconciles the template with its own documentation: the account category README already states that "All optional resources are disabled by default" and lists `EnableBedrockInvocationLogs`, which is currently inaccurate because the parameter defaults to `"true"`.

This is a beta/limited-release product. The default change is applied in place (a version/date bump on the same file) rather than via a new versioned template file, consistent with the sibling v0.0.44 spec `0-0-44-bedrock-media-and-log-prefix-segmentation`.

## Relationship to other v0.0.44 work

The sibling spec `0-0-44-bedrock-media-and-log-prefix-segmentation` adds `EnableBedrockLargeObjectLogging` (default `"false"`) and a CloudFormation `Rules` assertion requiring `EnableBedrockInvocationLogs` to be `"true"` whenever large-object logging is enabled. Changing the base default to `"false"` is compatible with that rule: both Bedrock toggles then default off, and enabling media logging continues to require the administrator to also set `EnableBedrockInvocationLogs="true"`. The net effect is that all Bedrock invocation logging is fully opt-in.

---

## Requirements

### Requirement 1: Default the parameter to disabled

**User Story:** As an account administrator, I want Bedrock model invocation logging infrastructure to be off unless I explicitly enable it, so that I do not provision unused resources or capture sensitive prompt/response content by default.

#### Acceptance Criteria

1. THE `EnableBedrockInvocationLogs` parameter in `templates/v2/account/account-wide-infrastructure.yml` SHALL have `Default: "false"`.
2. THE parameter's `Type` (`String`), `AllowedValues` (`["true", "false"]`), and `ConstraintDescription` SHALL remain unchanged.
3. WHERE `EnableBedrockInvocationLogs` is left at its default, THE stack SHALL NOT create the Bedrock CloudWatch Logs log group, the Bedrock IAM role, or any of the Bedrock-conditional outputs.
4. THE behavior when `EnableBedrockInvocationLogs` is explicitly set to `"true"` SHALL remain identical to v0.0.43 (log group, IAM role, and outputs created; activation still a manual CLI step).
5. THE `EnableBedrockInvocationLogs` condition and every resource, output, and `Rules` assertion that references it SHALL continue to function unchanged; only the parameter default changes.

### Requirement 2: Keep parameter and comment text accurate

**User Story:** As a template reader, I want the parameter description and any in-template guidance to reflect that the feature is opt-in, so that the template is self-consistent.

#### Acceptance Criteria

1. THE `EnableBedrockInvocationLogs` parameter description SHALL remain accurate for a default-off feature (it already reads "Set to 'true' to create..."); IF any in-template comment or the description asserts or implies the feature is enabled by default, THEN it SHALL be corrected to state the feature is opt-in / disabled by default.
2. THE "BEDROCK MODEL INVOCATION LOGGING - MANUAL ACTIVATION REQUIRED" header comment block SHALL remain accurate and SHALL NOT imply the feature is on by default.
3. NO other parameter defaults, descriptions, or constraints in the template SHALL be changed by this spec.

### Requirement 3: Version and change governance

**User Story:** As a maintainer, I want the default change recorded with a proper version bump and changelog entry, so that the change is traceable.

#### Acceptance Criteria

1. THE `account-wide-infrastructure.yml` header `Version:` and date SHALL be incremented per its current semantics when this change is applied.
2. THE change SHALL be recorded under the `v0.0.44 (unreleased)` section of `CHANGELOG.md`, in the `Changed` category, referencing this spec and including the template version number. Existing changelog text SHALL NOT be modified.
3. THE changelog entry SHALL note the update-time behavior: an existing deployment that relied on the previous default of `"true"` (by not specifying the parameter) will, on its next stack update, resolve `EnableBedrockInvocationLogs` to `"false"`, which deletes the Bedrock IAM role while the log group is retained (per its `DeletionPolicy: Retain`). Administrators who want to keep the infrastructure MUST set `EnableBedrockInvocationLogs="true"` explicitly.

### Requirement 4: Update v0.0.43 documentation

**User Story:** As an end user, I want the documentation introduced in v0.0.43 to state the correct default, so that I am not misled about the template's behavior.

#### Acceptance Criteria

1. THE `docs/templates/v2/account/account-wide-infrastructure-README.md` `EnableBedrockInvocationLogs` parameter table SHALL show `| Default | false |`.
2. THE account category README `docs/templates/v2/account/README.md` SHALL remain consistent with the new default; its "All optional resources are disabled by default" statement, which already lists `EnableBedrockInvocationLogs`, SHALL now be accurate and SHALL NOT require a caveat for this parameter.
3. THE admin-ops guide `docs/admin-ops/bedrock-model-invocation-logging.md` SHALL state that the feature is disabled by default (opt-in) and that provisioning requires setting `EnableBedrockInvocationLogs="true"`, without contradicting the existing "true"-behavior descriptions.
4. WHERE existing documentation uses `EnableBedrockInvocationLogs="true"` as an example of enabling the feature or as a prerequisite, THOSE references SHALL be preserved (they remain correct as enablement guidance).
5. EXISTING blockquotes, notes, and custom content in the affected documentation SHALL be preserved per the documentation steering rules; only default-value statements SHALL be corrected.

## Non-goals / out of scope

1. Changing any parameter other than the default of `EnableBedrockInvocationLogs`.
2. Changing the resources, conditions, outputs, or IAM policies created when the feature is enabled.
3. Automating Bedrock model invocation logging activation (it remains a manual CLI step).
4. Any change to `EnableBedrockLargeObjectLogging` or the media/log-prefix work owned by the sibling `0-0-44-bedrock-media-and-log-prefix-segmentation` spec.
5. Migrating or deleting log groups/roles in already-deployed accounts (update-time behavior is documented, not automated).

## Constraints and assumptions

1. CloudFormation resolves an unspecified parameter to its template default on every create and update, so lowering the default alters update behavior for stacks that never set the parameter explicitly (see Requirement 3.3).
2. The Bedrock log group uses `DeletionPolicy: Retain`, so lowering the default (or explicitly setting `"false"`) removes the IAM role but preserves previously ingested logs.
3. This spec shares `account-wide-infrastructure.yml` with the sibling v0.0.44 spec; the version bump and CHANGELOG entries for both specs must be reconciled at release time so the file carries a single coherent header version.
