# Design — v0.0.44 Bedrock Invocation Logs Default Off

## 1. Overview

This is a single-value behavioral change with documentation follow-through. The `EnableBedrockInvocationLogs` parameter on `templates/v2/account/account-wide-infrastructure.yml` changes its `Default` from `"true"` to `"false"`, making Bedrock model invocation logging fully opt-in. No resources, conditions, outputs, or IAM policies change shape; only the default value of one parameter and the documentation that describes it.

The design deliberately keeps the blast radius minimal:

- The `EnableBedrockInvocationLogs` condition already gates the log group, the IAM role, and all Bedrock-conditional outputs. Because only the default changes, that gating logic is untouched — the difference is solely what value the parameter resolves to when a deployer does not supply one.
- The template already documents itself around the "true" behavior (create resources) and a manual activation step. Those statements remain correct; the only inaccurate statements are default-value claims, which live in the docs, not the template body.

### 1.1 Why a default flip is the whole change

CloudFormation resolves an unspecified parameter to its template default on every create and update. So the entire functional effect of this spec is: "when the deployer says nothing, resolve to `false` instead of `true`." Everything downstream (`Conditions`, `Resources`, `Outputs`, the sibling spec's `Rules` assertion) reads the resolved value and already behaves correctly for `false`.

### 1.2 Interaction with the sibling v0.0.44 spec

`0-0-44-bedrock-media-and-log-prefix-segmentation` adds `EnableBedrockLargeObjectLogging` (default `"false"`) plus a `Rules` assertion that requires `EnableBedrockInvocationLogs == "true"` when large-object logging is enabled. Lowering the base default is compatible: with both toggles defaulting off, the assertion is vacuously satisfied by default, and a deployer who enables media logging must still explicitly set `EnableBedrockInvocationLogs="true"`, which satisfies the assertion. No change to the assertion is required by this spec.

---

## 2. Template change: `account-wide-infrastructure.yml`

### 2.1 Parameter default

The only template edit is the `Default` line of the parameter.

Before:

```yaml
  EnableBedrockInvocationLogs:
    Type: String
    Description: "Set to 'true' to create the CloudWatch Logs log group and IAM role required for Amazon Bedrock model invocation logging. This is a one-time, per-account, per-region setup. IMPORTANT: Creating these resources does NOT enable logging. After deployment you must run the AWS CLI command provided in the BedrockModelInvocationLoggingEnableCommand stack output to activate logging, because Amazon Bedrock provides no CloudFormation resource for the logging configuration."
    Default: "true"
    AllowedValues: ["true", "false"]
    ConstraintDescription: "Must be 'true' or 'false'."
```

After:

```yaml
  EnableBedrockInvocationLogs:
    Type: String
    Description: "Set to 'true' to create the CloudWatch Logs log group and IAM role required for Amazon Bedrock model invocation logging. This is a one-time, per-account, per-region setup. Disabled by default. IMPORTANT: Creating these resources does NOT enable logging. After deployment you must run the AWS CLI command provided in the BedrockModelInvocationLoggingEnableCommand stack output to activate logging, because Amazon Bedrock provides no CloudFormation resource for the logging configuration."
    Default: "false"
    AllowedValues: ["true", "false"]
    ConstraintDescription: "Must be 'true' or 'false'."
```

Rationale for the description tweak: adding "Disabled by default." keeps the parameter self-describing (Req 2.1). `Type`, `AllowedValues`, and `ConstraintDescription` are byte-for-byte unchanged (Req 1.2).

### 2.2 What is explicitly NOT touched

- `Conditions.EnableBedrockInvocationLogs` (`!Equals [!Ref EnableBedrockInvocationLogs, "true"]`) — unchanged.
- The Bedrock log group and IAM role `AWS::Include` resources — unchanged.
- The five Bedrock-conditional outputs — unchanged.
- The `EnableBedrockLargeObjectLogging` `Rules` assertion — unchanged.
- The "BEDROCK MODEL INVOCATION LOGGING - MANUAL ACTIVATION REQUIRED" header comment block — verified to make no "on by default" claim, so it stays as-is (Req 2.2). If a later read finds such a claim, it is corrected there; none exists today.

### 2.3 Header version bump and reconciliation

The file header currently reads `Version: v2.1.0/2026-09-23`. That `v2.1.0` minor bump belongs to the sibling media/log-prefix spec, which is the larger concurrent v0.0.44 change on this file. This spec's change is a small behavioral tweak on the same file, so version handling depends on merge order:

- **If this change is applied and released together with the media spec** (single v0.0.44 release of the file), fold it into the `v2.1.0` bump — no separate header change; the media spec's date stands or is refreshed to the release date.
- **If this change is applied on top of an already-released `v2.1.0`**, bump the header to `v2.1.1/<date>` (patch: behavior default change, no interface change).

Either way the file carries a single coherent header version at release (Req 3.1, and the reconciliation constraint in requirements §Constraints).

---

## 3. Documentation changes

All edits follow the documentation and markdown steering: preserve existing blockquotes, notes, and `="true"` enablement examples; only correct default-value statements; no hard-wrapping of prose.

### 3.1 `docs/templates/v2/account/account-wide-infrastructure-README.md`

The `EnableBedrockInvocationLogs` parameter table's `Default` row changes from `true` to `false`.

Before:

```markdown
| Type | String |
| Default | true |
| Allowed Values | true, false |
```

After:

```markdown
| Type | String |
| Default | false |
| Allowed Values | true, false |
```

The following `> **Important:**` blockquote (which uses `EnableBedrockInvocationLogs="true"` as the enablement example) is preserved verbatim — it is correct guidance for turning the feature on (Req 4.4, 4.5).

### 3.2 `docs/templates/v2/account/README.md`

The "Conditional Resources" section already reads "All optional resources are disabled by default" and lists `EnableBedrockInvocationLogs`. With the new default this statement becomes accurate, so the line requires no caveat and no edit beyond confirming consistency (Req 4.2). No text change is planned here unless review finds a residual inconsistency.

### 3.3 `docs/admin-ops/bedrock-model-invocation-logging.md`

Add a short, explicit statement that the feature is disabled by default (opt-in) near the top ("Overview" / "What is provisioned" area), so a reader knows the prerequisite is to set the parameter to `"true"`. The existing "when `EnableBedrockInvocationLogs` is `\"true\"`" descriptions, the prerequisites list, and the teardown section (already documents setting `"false"`) stay as-is (Req 4.3, 4.4).

Planned insertion (wording finalized at implementation time), for example under the Overview:

```markdown
> **Default:** `EnableBedrockInvocationLogs` defaults to `"false"`. Bedrock model invocation logging infrastructure is opt-in — set the parameter to `"true"` to provision the log group and IAM role, then run the manual activation command below.
```

This is additive and preserves all existing content.

---

## 4. CHANGELOG entry

Add under the existing `## v0.0.44 (unreleased)` section, in a `### Changed` block, without modifying any existing text (changelog steering):

```markdown
### Changed
- **Account: account-wide-infrastructure.yml** - Changed the `EnableBedrockInvocationLogs` parameter default from `"true"` to `"false"`, making Bedrock model invocation logging infrastructure opt-in [Spec: 0-0-44-bedrock-invocation-logs-default-off](.kiro/specs/0-0-44-bedrock-invocation-logs-default-off/). The feature already required a manual, per-region activation command to actually log, and invocation logs capture full prompt/response content, so it should be enabled by explicit choice. **Update-time note:** a stack that relied on the previous default (never set the parameter) will resolve to `"false"` on its next update, deleting the `${OrgPrefix}-Bedrock-CloudWatch-Role` IAM role; the log group is retained via `DeletionPolicy: Retain`. Set `EnableBedrockInvocationLogs="true"` to keep the infrastructure.
```

The template version token in the bullet is filled in per the §2.3 reconciliation (`v2.1.0` if folded into the media release, `v2.1.1` if applied afterward). The design intentionally leaves the exact version to the release-time merge so the two v0.0.44 specs stay consistent.

---

## 5. Testing and verification

Per the testing steering, unit-level checks are the priority; no property-based tests are warranted for a single default change.

1. **Lint:** run the repository's `cfn-lint` check over `account-wide-infrastructure.yml` and confirm no new findings.
2. **Default resolution (disabled path):** synthesize/deploy the template with no `EnableBedrockInvocationLogs` value supplied and confirm the Bedrock log group, IAM role, and Bedrock-conditional outputs are absent from the resolved template/stack.
3. **Explicit-true path unchanged:** set `EnableBedrockInvocationLogs="true"` and confirm the log group, IAM role, and outputs are present exactly as in v0.0.43.
4. **Sibling-rule compatibility:** confirm `EnableBedrockLargeObjectLogging="true"` with the (now default) `EnableBedrockInvocationLogs="false"` fails the existing `Rules` assertion with its descriptive message, and that setting `EnableBedrockInvocationLogs="true"` clears it.
5. **Docs consistency check:** grep the affected docs to confirm no remaining `Default | true` (for this parameter) or "enabled by default" assertions for Bedrock invocation logging.

---

## 6. Design decisions

| Decision | Choice | Reasoning |
|---|---|---|
| Scope of template edit | Change only the `Default` (plus a "Disabled by default." phrase in the description) | Smallest change that satisfies the requirement; keeps condition/resource/output logic untouched |
| Version handling | Fold into `v2.1.0` if released with the media spec, else `v2.1.1` | Two v0.0.44 specs share the file; avoids a version conflict at release |
| Category README | Confirm-only (no forced edit) | The "disabled by default" statement becomes accurate; editing it would risk churn on correct text |
| Admin-ops guide | Additive blockquote, preserve existing "true"-behavior text | Documentation steering requires preserving blockquotes/notes and existing enablement examples |
| Breaking-change classification | `Changed` with an update-time note, not `Breaking Changes` | Beta feature introduced in the immediately prior version (v0.0.43); no interface removed/renamed, log data retained |

## 7. Requirements coverage

| Requirement | Addressed by |
|---|---|
| 1 (default to disabled) | §2.1, §2.2 |
| 2 (accurate parameter/comment text) | §2.1 description tweak, §2.2 header verification |
| 3 (version & change governance) | §2.3, §4 |
| 4 (update v0.0.43 documentation) | §3.1, §3.2, §3.3 |
