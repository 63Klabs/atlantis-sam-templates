# Implementation Plan

**Feature:** IAM RoleName Length Compliance and Naming Length Budget

**Spec:** `0-0-44-iam-role-name-length`
**Repository target version:** v0.0.44 (unreleased)

**Requirements:** [requirements.md](./requirements.md) · **Design:** [design.md](./design.md)

> **Version control note:** The only file with resource content changing is the `AWS::Include` module `promotion-source-event-service-role.yml`, which is unversioned (no version header). The parent template `template-pipeline-s3-source.yml` is not modified (the logical ID is preserved). No template version increment or new versioned template file is required, so there is no "increment version" task.

> **Scope note:** `CodePipelineServiceRole` and `SourceEventServiceRole` are intentionally left unchanged (resolved decision in requirements). Do not rename them.

---

- [x] 1. Shorten the promotion source-event service role name
  - Edit `templates/v2/modules/pipeline/promotion-source-event-service-role.yml`.
  - Change the `RoleName` `Fn::Sub` from `${Prefix}-Worker-${ProjectId}-${StageId}-PromotionSourceEventServiceRole` to `${Prefix}-Worker-${ProjectId}-${StageId}-PromoteSrcEventSvcRole`.
  - Leave the inline `PolicyName` (`...-PromotionSourceEventServicePolicy`) unchanged — the fully spelled-out policy name intentionally documents the abbreviated role (128-character policy-name limit, well within budget).
  - Do not change `Type`, `Condition`, `Path`, `Description`, `PermissionsBoundary`, `AssumeRolePolicyDocument`, or the policy statement.
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 2. Confirm no parent-template or sibling-module changes are needed
  - Verify `templates/v2/pipeline/template-pipeline-s3-source.yml` still declares the logical ID `PromotionSourceEventServiceRole` and that no rendered role-name string is hard-coded there.
  - Verify `templates/v2/modules/pipeline/promotion-source-event-rule.yml` references the role via `Fn::GetAtt: [PromotionSourceEventServiceRole, Arn]` (logical ID, not rendered name) and therefore needs no edit.
  - Make no edits in this task; it is a verification gate confirming the change surface is a single module file.
  - _Requirements: 2.3_

- [x] 3. Add the resource name-length budget to steering
  - Edit `AGENTS.md`: add a `#### Resource Name Length Budget` subsection to the "Naming Conventions (Required)" section, immediately after the `#### S3` subsection, using the content drafted in design §3.
  - State the 64-character IAM role name limit (path excluded), the 34-character reservation for `Prefix` + `ProjectId` + `StageId` (+ joining hyphens), the resulting 30-character static budget, and the worker-role suffix limit of 22 characters.
  - Include the blockquote noting the reasonable-footprint assumption vs. the absolute maximums and that parameter `MaxLength` values are unchanged.
  - Preserve all existing `AGENTS.md` content and blockquotes; only add the new subsection.
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 5.1, 5.2, 5.3, 5.4_

- [x] 4. Add a rendered-name length check (unit test)
  - Add a fast unit test that renders the module `RoleName` `Fn::Sub` with the assumed footprint (`Prefix` = 6 chars, `ProjectId` = 20 chars, `StageId` = 6 chars) and asserts the result length is `<= 64` (expected exactly 64).
  - Assert the static/descriptive suffix `PromoteSrcEventSvcRole` is `<= 22` characters as a budget guard.
  - Keep it a concrete unit test (no property-based test) so it runs in well under a second.
  - _Requirements: 1.5, 2.2, 3.1_

- [x] 5. Validate the template still splices and lints cleanly
  - Run the repository cfn-lint step against `templates/v2/pipeline/template-pipeline-s3-source.yml` and confirm no new findings (existing `E6101/W2001/W8001` suppressions already cover `AWS::Include`).
  - Confirm the rendered role name at the assumed footprint is 64 characters and that the abbreviated role and the still-descriptive inline policy name are consistent and readable.
  - _Requirements: 2.2, 3.1_

- [x] 6. Update documentation for the modified module
  - In `docs/templates/v2/pipeline/template-pipeline-s3-source-README.md`, in the `### PromotionSourceEventServiceRole` section, add a line stating the rendered role name `${Prefix}-Worker-${ProjectId}-${StageId}-PromoteSrcEventSvcRole` and that it is abbreviated to stay within the 64-character IAM role name limit.
  - Confirm the heading and anchor `#promotionsourceeventservicerole` (the logical ID) remain unchanged; no table-of-contents edit is needed.
  - Preserve all existing content and any blockquotes in the README.
  - _Requirements: 6.1, 6.3_

- [x] 7. Update CHANGELOG.md
  - Add the **Changed** entry under the existing `## v0.0.44 (unreleased)` section, using the wording from design §5.
  - Reference this spec `[Spec: 0-0-44-iam-role-name-length](.kiro/specs/0-0-44-iam-role-name-length/)`, name the modified module, describe the rendered-name rename with the logical ID unchanged, and note the one-time IAM role replacement and the in-flight-execution caveat.
  - Do not modify existing changelog entries; add only the new entry.
  - _Requirements: 6.2_
