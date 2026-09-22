# Implementation Plan

## Overview

This plan adds account-wide Amazon Bedrock model invocation logging infrastructure to
`templates/v2/account/account-wide-infrastructure.yml`: two new `AWS::Include` modules (a
CloudWatch log group and an IAM role with a least-privilege inline policy), three new optional
parameters, two conditions, a metadata group, five conditional outputs, and a header comment
documenting the required manual activation step. It also generates an admin-ops Markdown document
for copy-over into the external `atlantis-platform-admin` repository, updates the end-user README,
adds fast unit tests, validates with `cfn-lint`, and records the change in the changelog.

The work is additive and backward compatible: no existing parameters, resources, outputs, or
exports are renamed or removed. Activation of Bedrock logging is intentionally a documented manual
CLI step (no Lambda-backed custom resource).

## Tasks

- [x] 1. Version management (first, per version-control rules; PATCH > 0 so auto-increment)
  - [x] 1.1 Increment `account-wide-infrastructure.yml` header version from `v2.0.1/2026-08-20` to `v2.0.2/2026-09-22`
    - Update only the `# Version:` line; leave all other existing header content unchanged (header feature-list and activation-block additions are handled in task 5)
    - _Requirements: 12.1, 12.2, 12.3_

- [x] 2. Create the log group module
  - [x] 2.1 Create `templates/v2/modules/account-wide/bedrock-cloudwatch-log-group.yml`
    - Single `AWS::Logs::LogGroup` resource body (no logical ID, no `Resources:` wrapper), per design §4
    - `Condition: EnableBedrockInvocationLogs`; `DeletionPolicy: Retain`; `UpdateReplacePolicy: Retain`
    - `LogGroupName: Fn::Sub "/aws/bedrock/${OrgPrefix}-ModelInvocations"`
    - `RetentionInDays: Ref BedrockInvocationLogExpirationInDays`
    - `KmsKeyId: Fn::If [HasBedrockInvocationLogKmsKey, Ref BedrockInvocationLogKmsKeyArn, Ref "AWS::NoValue"]`
    - Long-form intrinsics only; contract comment block declaring required parent params (`OrgPrefix`, `BedrockInvocationLogExpirationInDays`, `BedrockInvocationLogKmsKeyArn`) and conditions (`EnableBedrockInvocationLogs`, `HasBedrockInvocationLogKmsKey`), the KEEP IN SYNC note, the Retain rationale, and the AWS docs URL
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9_

- [x] 3. Create the IAM role module
  - [x] 3.1 Create `templates/v2/modules/account-wide/bedrock-cloudwatch-role.yml`
    - Single `AWS::IAM::Role` resource body (no logical ID, no `Resources:` wrapper), per design §5
    - `Condition: EnableBedrockInvocationLogs`; `RoleName: Fn::Sub "${OrgPrefix}-Bedrock-CloudWatch-Role"`; `Path: Ref RolePath`
    - Trust policy: `bedrock.amazonaws.com` / `sts:AssumeRole` with `StringEquals aws:SourceAccount = ${AWS::AccountId}` and `ArnLike aws:SourceArn = arn:${AWS::Partition}:bedrock:${AWS::Region}:${AWS::AccountId}:*`
    - Inline policy `BedrockModelInvocationLogsWrite`: actions exactly `logs:CreateLogStream`, `logs:PutLogEvents`; `Resource` a constructed `Fn::Sub` ARN ending `:log-stream:aws/bedrock/modelinvocations` using `${AWS::Partition}` (per design "why the ARN is constructed")
    - No `ManagedPolicyArns`, no `logs:*`, no `Resource: "*"`
    - Long-form intrinsics only; contract comment block declaring required parent params (`OrgPrefix`, `RolePath`) and condition (`EnableBedrockInvocationLogs`), the KEEP IN SYNC note, the constructed-ARN/no-DependsOn rationale, and the AWS docs URL
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 6.11, 6.12_

- [x] 4. Update the parent template body (parameters, conditions, metadata, resources, outputs)
  - [x] 4.1 Add the three parameters under a new `# Bedrock Model Invocation Logs` subsection comment, after `AllowLegacyCloudFrontLogs`
    - `EnableBedrockInvocationLogs`, `BedrockInvocationLogExpirationInDays`, `BedrockInvocationLogKmsKeyArn` exactly as specified in design §1
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.6, 3.7_
  - [x] 4.2 Add the two conditions per design §2
    - `EnableBedrockInvocationLogs: !Equals [!Ref EnableBedrockInvocationLogs, "true"]`
    - `HasBedrockInvocationLogKmsKey: !Not [!Equals [!Ref BedrockInvocationLogKmsKeyArn, ""]]`
    - _Requirements: 1.4, 3.3_
  - [x] 4.3 Add the `"Bedrock Model Invocation Logs"` metadata parameter group between `"S3 Access Log Bucket"` and `"Promotion"`, listing the three params in order
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  - [x] 4.4 Add the two `AWS::Include` resources (`BedrockModelInvocationLogGroup`, `BedrockCloudWatchLogsRole`) after `ApiGatewayAccount`, with the `# -- ... (Conditional) --` comments and the no-`DependsOn` note, per design §6
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  - [x] 4.5 Add the five conditional outputs after the API Gateway CloudWatch output, per design §7
    - `BedrockModelInvocationLogGroupName` (export `${OrgPrefix}-Bedrock-CloudWatch-LogGroup-Name`), `BedrockModelInvocationLogGroupArn` (export `-LogGroup-Arn`), `BedrockCloudWatchLogsRoleArn` (export `-Role-Arn`), `BedrockModelInvocationLoggingEnableCommand` (JSON payload, text+embedding true / image+video false, not exported), `BedrockModelInvocationLogGroupConsole` (deep link, not exported)
    - All carry `Condition: EnableBedrockInvocationLogs`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [x] 5. Update the parent template header comment (manual activation documentation)
  - [x] 5.1 Append the Bedrock feature line to the header feature list and add the "BEDROCK MODEL INVOCATION LOGGING - MANUAL ACTIVATION REQUIRED" block per design §8
    - State that deploy does not enable logging; explain why (no native resource, no Lambda by choice); include the CLI command referencing the output names; note per-region; note text+embedding vs image+video; link to the admin-ops doc and AWS docs
    - Preserve all other existing header content
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

- [x] 6. Validation (after template and modules are complete)
  - [x] 6.1 Run the repository `cfn-lint` flow over `account-wide-infrastructure.yml`
    - Expect existing suppressions (E3001, E3005, E6101, W2001, W8001) to suffice; add no new suppression unless a specific finding requires it, and justify any that is added
    - _Requirements: 15.1_

- [x] 7. Unit tests (fast, concrete; no property-based tests per testing guidelines)
  - [x] 7.1 Create `tests/test_bedrock_invocation_logs_unit.py` covering the parent template
    - Parameters (types, defaults, `AllowedValues`/`AllowedPattern`, `MaxLength`, absence of `MinLength`/`MinValue`/`MaxValue` as specified), both conditions, metadata group label + membership + position, both `AWS::Include` resources and their module paths, the five outputs with conditions and export names, the enable-command JSON toggles, and the `v2.0.2` version line and header activation text
    - _Requirements: 15.2, 15.3, 15.7, 15.8_
  - [x] 7.2 Extend the test file to cover the log group module
    - Single resource body/no `Resources` wrapper; type; condition; `Retain` policies; `LogGroupName` sub; `RetentionInDays` ref; conditional `KmsKeyId` with `AWS::NoValue` false branch
    - _Requirements: 15.4, 15.6_
  - [x] 7.3 Extend the test file to cover the role module
    - Single resource body; type; condition; trust principal + both source conditions; exactly the two `logs:` actions; constructed log-stream-scoped `Resource` with `${AWS::Partition}`; negative assertions (no `logs:*`, no `Action "*"`, no `Resource "*"`, no `ManagedPolicyArns`); `Path`/`RoleName`
    - _Requirements: 15.5, 15.6_
  - [x] 7.4 Add the cross-module consistency test (guards Correctness Property 5)
    - Assert the log group path from the log group module's `LogGroupName` equals the log-group segment of the role module's policy `Resource` ARN
    - _Requirements: 5.4, 6.8_
  - [x] 7.5 Add module hygiene assertions for both modules
    - Raw text contains no shorthand intrinsic tags; header comments declare required params/conditions and contain the AWS docs URL
    - _Requirements: 5.8, 5.9, 6.10, 6.11, 6.12_
  - [x] 7.6 Run the full test suite; fix any regression in existing tests that assert on the account-wide template's parameter/group/output counts
    - _Requirements: 15.9, 15.10_

- [x] 8. Generate the admin-ops documentation (for copy-over to atlantis-platform-admin)
  - [x] 8.1 Create `docs/admin-ops/bedrock-model-invocation-logging.md` following the 12-section outline in design §9
    - Copy-over note naming the `atlantis-platform-admin` repo; overview; what the stack creates vs does not do; prerequisites (stack enabled, caller IAM incl. `iam:PassRole`, optional KMS requirements); activation command with placeholders and fixed toggles; verification (`get-...` + sample response); disabling (`delete-...`, log group retained); per-region; cost/data-sensitivity; deliberate limitations (bedrock-runtime only, 100 KB ceiling, image/video off + how to opt in with caveat); troubleshooting (`ValidationException`, `AccessDeniedException`, logs not appearing, bad KMS key, retained-log-group re-create conflict); attributed AWS doc links
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 10.10, 10.11, 10.12_
  - [x] 8.2 Update `docs/admin-ops/account-management.md` to link to the new doc, preserving existing content
    - _Requirements: 10.13_

- [x] 9. Update end-user template documentation (preserve existing blockquotes)
  - [x] 9.1 Update `docs/templates/v2/account/account-wide-infrastructure-README.md` per the end-user docs steering structure
    - Document the `"Bedrock Model Invocation Logs"` group and all three parameters (attribute tables); the two new resources (types + conditions); all five outputs + export names; a blockquote warning that deploy alone does not activate logging (link to admin-ops doc); data-sensitivity and cost notes
    - Preserve all existing blockquotes and custom content
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_
  - [x] 9.2 Update `docs/templates/v2/account/README.md` category README only if its template descriptions or parameter summaries are affected
    - _Requirements: 11.7_
  - [x] 9.3 Add the two new modules to `templates/v2/modules/README.md` inventory
    - _Requirements: (module standards; design Components table)_

- [x] 10. Update `CHANGELOG.md`
  - [x] 10.1 Add an entry under `v0.0.43 - unreleased` in `### Added`
    - Reference `[Spec: 0-0-43-enable-account-model-logs](.kiro/specs/0-0-43-enable-account-model-logs/)`; list `account-wide-infrastructure.yml v2.0.2` with the two new modules as sub-bullets; mention the required post-deployment activation step; do not modify existing changelog text
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "3.1"] },
    { "id": 2, "tasks": ["4.1", "4.2", "4.3", "4.4", "4.5", "5.1"] },
    { "id": 3, "tasks": ["6.1"] },
    { "id": 4, "tasks": ["7.1", "7.2", "7.3", "7.4", "7.5"] },
    { "id": 5, "tasks": ["7.6"] },
    { "id": 6, "tasks": ["8.1", "8.2", "9.1", "9.2", "9.3"] },
    { "id": 7, "tasks": ["10.1"] }
  ]
}
```

- Task 1 (version bump) is first per version-control rules.
- Tasks 2 and 3 (modules) are independent of each other and can be created in parallel.
- Task 4 wires the parent to the modules and task 5 documents activation in the header; both
  depend on the module contracts from tasks 2 and 3.
- Task 6 (`cfn-lint`) depends on the completed template and module edits.
- Task 7 (unit tests) depends on tasks 2-5; 7.6 (full suite) runs after 7.1-7.5.
- Tasks 8 and 9 (documentation) depend on the finalized parameters, resources, and outputs.
- Task 10 (changelog) is the final finalization step.

## Notes

- Follow `AGENTS.md` naming and least-privilege IAM rules; all ARNs use `${AWS::Partition}`.
- Modules use long-form intrinsics only (`Fn::Sub`, `Ref`, `Fn::If`); no `!`-tag shorthand.
- Per the testing guidelines, prioritize fast unit tests; no new property-based tests.
- The change is additive and backward compatible: no parameters, resources, outputs, or exports
  removed or renamed.
- The log group carries `DeletionPolicy: Retain` and `UpdateReplacePolicy: Retain` by design
  (audit durability); the retained-log-group re-create conflict is documented, not "fixed".
- Preserve existing blockquotes when updating documentation; only touch READMEs for what changed.
