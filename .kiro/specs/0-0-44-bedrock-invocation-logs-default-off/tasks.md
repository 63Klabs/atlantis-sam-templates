# Implementation Plan

Tasks — v0.0.44 Bedrock Invocation Logs Default Off

## Overview

Implementation task list for `design.md`. This is a single-value default change on `templates/v2/account/account-wide-infrastructure.yml` plus documentation follow-through. The change is applied in place per the beta in-place convention shared with the sibling `0-0-44-bedrock-media-and-log-prefix-segmentation` spec.

Legend: each task notes the requirement(s) it satisfies. Tasks are ordered so the template change lands first, verification follows, and documentation (required, not optional) is last.

## Tasks

### 1. Template change

- [x] 1.1 In `account-wide-infrastructure.yml`, change the `EnableBedrockInvocationLogs` parameter `Default` from `"true"` to `"false"`; leave `Type`, `AllowedValues`, and `ConstraintDescription` unchanged _(R1.1, R1.2)_
- [x] 1.2 Add "Disabled by default." to the `EnableBedrockInvocationLogs` description so the parameter stays self-describing _(R2.1)_
- [x] 1.3 Verify the "BEDROCK MODEL INVOCATION LOGGING - MANUAL ACTIVATION REQUIRED" header comment block makes no "on by default" claim; correct it only if such a claim exists (none expected) _(R2.2)_
- [x] 1.4 Confirm no other parameter default, description, or constraint is modified _(R2.3)_

### 2. Verification

- [x] 2.1 Run the repository `cfn-lint` check on `account-wide-infrastructure.yml`; confirm no new findings _(R1.5)_
- [x] 2.2 Resolve/synthesize the template with `EnableBedrockInvocationLogs` unset; confirm the Bedrock log group, IAM role, and the five Bedrock-conditional outputs are ABSENT _(R1.3)_
- [x] 2.3 Resolve/synthesize with `EnableBedrockInvocationLogs="true"`; confirm the log group, IAM role, and outputs are present exactly as in v0.0.43 _(R1.4)_
- [x] 2.4 Confirm sibling-rule compatibility: `EnableBedrockLargeObjectLogging="true"` with default `EnableBedrockInvocationLogs="false"` fails the existing `Rules` assertion with its descriptive message; setting `EnableBedrockInvocationLogs="true"` clears it _(R1.5)_

### 3. Version and changelog governance

- [x] 3.1 Reconcile the header `Version:` with the sibling media spec: fold into `v2.1.0` if released together, else bump to `v2.1.1/<date>` (patch) _(R3.1)_
- [x] 3.2 Add a `### Changed` entry under `## v0.0.44 (unreleased)` in `CHANGELOG.md` referencing this spec, with the reconciled template version and the update-time role-deletion note; do not modify existing changelog text _(R3.2, R3.3)_

### 4. Documentation updates (required)

- [x] 4.1 In `docs/templates/v2/account/account-wide-infrastructure-README.md`, change the `EnableBedrockInvocationLogs` parameter table `Default` row from `true` to `false`; preserve the following `> **Important:**` blockquote and its `="true"` enablement example _(R4.1, R4.4, R4.5)_
- [x] 4.2 In `docs/templates/v2/account/README.md`, confirm the "All optional resources are disabled by default" statement is now accurate for `EnableBedrockInvocationLogs`; edit only if a residual inconsistency remains _(R4.2)_
- [x] 4.3 In `docs/admin-ops/bedrock-model-invocation-logging.md`, add an additive opt-in/default-`"false"` note (e.g., an Overview blockquote); preserve existing "true"-behavior descriptions, the prerequisites list, and the teardown section _(R4.3, R4.4, R4.5)_
- [x] 4.4 Grep the affected docs to confirm no remaining `Default | true` for this parameter and no "enabled by default" assertion for Bedrock invocation logging _(R4.1, R4.2, R4.3)_
