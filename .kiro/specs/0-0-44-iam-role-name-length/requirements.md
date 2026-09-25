# Requirements Document

**Feature:** IAM RoleName Length Compliance and Naming Length Budget

**Spec:** `0-0-44-iam-role-name-length`
**Repository target version:** v0.0.44 (unreleased)
**Status:** Draft for Review
**Date:** 2026-09-24

---

## Introduction

IAM role names have a hard maximum of **64 characters** (verified against the [AWS IAM quotas reference](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_iam-quotas.html) — the role *name* is limited to 64 characters and the role *path* is a separate value that does not count toward that limit). Several templates in this repository construct `RoleName` values by interpolating the deployment identifiers `${Prefix}`, `${ProjectId}`, and `${StageId}` around a static, descriptive suffix. When a long static suffix is combined with a reasonably sized `ProjectId`, the rendered role name can exceed 64 characters and cause stack creation to fail.

This surfaced with the `promotion-source-event-service-role.yml` module introduced by spec [0-0-40-pipeline-with-promotion-approval](../0-0-40-pipeline-with-promotion-approval/), whose role name `${Prefix}-Worker-${ProjectId}-${StageId}-PromotionSourceEventServiceRole` is long enough that a mid-length `ProjectId` pushes it over the limit.

This feature (1) shortens over-budget role names, (2) audits every `RoleName` in the repository against a documented length budget, and (3) records a reusable naming length budget in the project steering (`AGENTS.md`) so future templates avoid the same problem.

### The length budget (governing rule)

The `Prefix`, `ProjectId`, and `StageId` parameters allow up to 8 / 26 / 8 characters respectively (see `ConstraintDescription` in the pipeline templates). Reserving the absolute maximum (8 + 26 + 8 = 42) for these three tokens leaves too little room for a descriptive resource suffix and is more conservative than real deployments require. Instead this spec adopts a **reasonable assumed footprint**:

- `Prefix` = 6, `ProjectId` = 20, `StageId` = 6 → **32 characters** of variable content.
- Including the two hyphens that join those three tokens → **34 characters reserved**.
- For a 64-character limit, that leaves **30 characters** for all remaining static / descriptive characters (literal words plus their surrounding hyphens).

> **Rule of thumb:** For any resource type with a maximum-length constraint, reserve **34 characters** for `Prefix` + `ProjectId` + `StageId` (with joining hyphens) and keep the remaining static portion of the name within the leftover budget. For IAM role names (limit 64) that leftover budget is **30 characters**.

> **Accepted tradeoff:** The 32-character assumed footprint is smaller than the parameters technically allow (max 42). A deployment that uses the maximum `Prefix`/`ProjectId`/`StageId` values can still exceed 64 characters even for a compliant name. This is a deliberate, documented tradeoff — the parameter `ConstraintDescription` already recommends keeping `Prefix + ProjectId` at or under 28 characters. This spec does not change the parameter `MaxLength` values.

### Worker role pattern

All affected roles use the pattern `${Prefix}-Worker-${ProjectId}-${StageId}-<Suffix>`. For these roles the non-variable content is `Worker` (6) + 4 hyphens + `<Suffix>`. Applying the budget above, the descriptive **static portion** (`Worker` + 2 non-reserved hyphens + `<Suffix>`, i.e. `8 + len(Suffix)`) must be **≤ 30 characters**, which is equivalent to requiring **`len(Suffix) ≤ 22`**.

### Templates and modules affected

**Modules with over-budget or at-limit `RoleName` (candidates for change):**
- `templates/v2/modules/pipeline/promotion-source-event-service-role.yml` — over budget (primary, in-scope)
- `templates/v2/modules/pipeline/source-event-service-role.yml` — at the exact limit (no margin)
- `templates/v2/modules/pipeline/cloudformation-svc-role.yml` and the `CodePipelineServiceRole` inline role — see Requirement 4

**Parent pipeline templates that reference the affected logical IDs (must stay consistent with any rename):**
- `templates/v2/pipeline/template-pipeline.yml`
- `templates/v2/pipeline/template-pipeline-github.yml`
- `templates/v2/pipeline/template-pipeline-build-only.yml`
- `templates/v2/pipeline/template-pipeline-s3-source.yml`

**Steering / documentation:**
- `AGENTS.md` (naming length budget)

---

## RoleName length audit

All values computed at the **assumed footprint** (`Prefix` 6, `ProjectId` 20, `StageId` 6 = 32) and, for reference, at the **absolute maximum** footprint (`Prefix` 8, `ProjectId` 26, `StageId` 8 = 42). Worker-role total = `10 + len(Suffix)` (static literal) + variable footprint.

### Worker roles — pattern `${Prefix}-Worker-${ProjectId}-${StageId}-<Suffix>`

| Module / role | Suffix | Suffix len | Static (`8+len`) | Total @assumed (42+len) | Total @max (52+len) | Status |
|---|---|---|---|---|---|---|
| promotion-source-event-service-role.yml | `PromotionSourceEventServiceRole` | 31 | 39 | 73 | 83 | ❌ Over budget |
| (inline) CodePipelineServiceRole | `CodePipelineServiceRole` | 23 | 31 | 65 | 75 | ❌ Over budget |
| source-event-service-role.yml | `SourceEventServiceRole` | 22 | 30 | 64 | 74 | ⚠️ At limit (no margin) |
| codedeploy-service-role.yml | `CodeDeployServiceRole` | 21 | 29 | 63 | 73 | ✅ Within budget |
| postdeploy-service-role.yml | `PostDeployServiceRole` | 21 | 29 | 63 | 73 | ✅ Within budget |
| cloudformation-svc-role.yml | `CloudFormationSvcRole` | 21 | 29 | 63 | 73 | ✅ Within budget |
| codebuild-service-role.yml | `CodeBuildServiceRole` | 20 | 28 | 62 | 72 | ✅ Within budget |
| promote-service-role.yml | `PromoteServiceRole` | 18 | 26 | 60 | 70 | ✅ Within budget |

### Prefix-scoped management roles — pattern `${PrefixUpper}-CloudFormation-Service-Role-<...>`

These roles contain no `ProjectId`/`StageId`; they consume only `Prefix` (max 8). Longest static literal is `Network-CloudFront-Mgmt`.

| Module | RoleName template | Total @Prefix=8 | Status |
|---|---|---|---|
| network-cloudfront-mgmt-role.yml | `${PrefixUpper}-CloudFormation-Service-Role-Network-CloudFront-Mgmt` | 60 | ✅ Within limit (reviewed) |
| network-full-mgmt-role.yml | `${PrefixUpper}-CloudFormation-Service-Role-Network-Full-Mgmt` | 54 | ✅ Within limit (reviewed) |
| pipeline-mgmt-role.yml | `${PrefixUpper}-CloudFormation-Service-Role-Pipeline-Management` | 56 | ✅ Within limit (reviewed) |
| storage-mgmt-role.yml | `${PrefixUpper}-CloudFormation-Service-Role-Storage-Management` | 55 | ✅ Within limit (reviewed) |

### Account-wide roles

| Module | RoleName template | Status |
|---|---|---|
| bedrock-cloudwatch-role.yml | `${OrgPrefix}-Bedrock-CloudWatch-Role` | ✅ Within limit (reviewed; `OrgPrefix` is short) |

---

## Update behavior and impact

Changing an `AWS::IAM::Role` `RoleName` is a **replacement** operation in CloudFormation. On the next stack update, CloudFormation creates the new role, updates the in-stack resources that consume it to reference the new ARN, and then deletes the old role. This happens automatically during a normal stack update — there is no manual migration step, so existing deployments simply update.

For the roles in scope this replacement is self-contained, and there are no lingering issues in the normal case, because:

- The affected roles are **worker roles created and consumed within the pipeline stack**. None of them are exported for cross-stack references, so no dependent stack breaks.
- `RolePath` is unchanged, and the pipeline management role grants IAM permissions on the `${Prefix}-Worker-*` wildcard. The renamed role still matches that wildcard, so no permission grant needs to change.
- The new role is created from the same template with **identical inline policies, trust policy, and permissions boundary**, so effective permissions are unchanged.

Operational caveats (worth documenting, but not blockers and not requiring migration):

- The stack update should not be applied while a pipeline execution is in flight, because the pipeline's own service role is replaced during the update.
- Any reference to the exact old role name or ARN that lives **outside** these templates (a manually attached policy, an SCP, a cross-account trust policy, or an externally managed permissions boundary) would need to be updated. No such references exist within this repository.

Because a plain stack update handles the change with no user intervention, the changes are categorized in the changelog under **Changed** with an explicit role-replacement note, rather than under **Breaking Changes**. The one-time role replacement (and the in-flight-execution caveat) is called out so operators can time the update.

**Scope-cost note:** Renaming `PromotionSourceEventServiceRole` affects only the promotion module introduced in `0-0-40` (low adoption, single template). Renaming `CodePipelineServiceRole` and `SourceEventServiceRole` would replace a role on **every existing pipeline stack** across the four core templates on its next update — broad churn for names that are only over by 1 / exactly at the limit and that stay within budget whenever `ProjectId ≤ 20`. See Requirement 4 for the recommended deferral.

---

## Requirements

### Requirement 1: Documented IAM RoleName length budget

**User Story:** As a template maintainer, I want a single documented length budget for role names, so that I can tell at authoring time whether a new role name will fit within the 64-character IAM limit.

#### Acceptance Criteria

1. WHEN the naming budget is documented THEN it SHALL state that IAM role names have a maximum of 64 characters and that the role path does not count toward that limit.
2. THE budget SHALL define the assumed footprint as `Prefix` 6 + `ProjectId` 20 + `StageId` 6 = 32 characters, plus 2 joining hyphens = 34 characters reserved.
3. THE budget SHALL state that the remaining static/descriptive portion of an IAM role name SHALL NOT exceed 30 characters.
4. THE budget SHALL note the accepted tradeoff that deployments using the maximum allowed `Prefix`/`ProjectId`/`StageId` values may still exceed 64 characters, and that parameter `MaxLength` values are intentionally left unchanged.
5. WHERE the worker-role pattern `${Prefix}-Worker-${ProjectId}-${StageId}-<Suffix>` is used THE budget SHALL make clear the descriptive suffix SHALL NOT exceed 22 characters.

### Requirement 2: Shorten the promotion source-event service role name (primary)

**User Story:** As a release engineer deploying a receiving (promotion) pipeline, I want the promotion source-event service role name to fit within 64 characters at the assumed footprint, so that stack creation does not fail on a role-name length error.

#### Acceptance Criteria

1. THE `RoleName` in `templates/v2/modules/pipeline/promotion-source-event-service-role.yml` SHALL be shortened from `${Prefix}-Worker-${ProjectId}-${StageId}-PromotionSourceEventServiceRole` to `${Prefix}-Worker-${ProjectId}-${StageId}-PromoteSrcEventSvcRole`.
2. THE shortened suffix `PromoteSrcEventSvcRole` (22 characters) SHALL satisfy the length budget from Requirement 1 (static portion = 30, total = 64 at the assumed footprint).
3. THE logical resource ID `PromotionSourceEventServiceRole` used by the parent template and the sibling `promotion-source-event-rule.yml` (via `Fn::GetAtt`) SHALL remain unchanged; only the rendered `RoleName` string SHALL change. (Decision: keep the logical ID.)
4. WHEN the module is changed THEN the update SHALL be characterized as an in-stack IAM role replacement (see the Update behavior and impact section): CloudFormation creates the new role, repoints the in-stack consumers to the new ARN, and deletes the old role on the next stack update, with no manual migration step required.

### Requirement 3: Every RoleName conforms to the length budget

**User Story:** As a template maintainer, I want every `AWS::IAM::Role` `RoleName` in the repository audited against the budget, so that no other role name is silently over the limit.

#### Acceptance Criteria

1. THE audit table in this document SHALL be treated as the authoritative inventory of `RoleName` values and their computed lengths at the assumed and maximum footprints.
2. WHEN a `RoleName` static portion exceeds 30 characters (worker-role suffix exceeds 22) THEN it SHALL be listed as over budget and a compliant replacement SHALL be proposed.
3. THE prefix-scoped management roles and account-wide roles SHALL be confirmed within the 64-character limit and marked as reviewed (no change required).
4. THE audit SHALL cover only `AWS::IAM::Role` `RoleName` values; output export names and other identifiers are out of scope for this spec.

### Requirement 4: Decision on the two additional over/at-limit worker roles

**User Story:** As a maintainer, I want an explicit decision on the two long-standing worker roles that are over or exactly at the budget, so that the fix scope and its fleet-wide replacement impact are intentional rather than accidental.

#### Acceptance Criteria

1. THE `CodePipelineServiceRole` inline role (suffix `CodePipelineServiceRole`, static 31, total 65 at assumed footprint) SHALL be identified as over budget by 1 character. A compliant replacement `CodePipelineSvcRole` (static 27, total 61) SHALL be proposed, consistent with the existing `CloudFormationSvcRole` `Svc` abbreviation.
2. THE `SourceEventServiceRole` module role (suffix `SourceEventServiceRole`, static 30, total 64 at assumed footprint) SHALL be identified as sitting at the exact limit with no margin. A compliant replacement `SourceEventSvcRole` (static 26, total 60) SHALL be proposed.
3. WHERE renaming these roles is chosen THE change SHALL be applied consistently across all four parent pipeline templates that reference `CodePipelineServiceRole` (`template-pipeline.yml`, `template-pipeline-github.yml`, `template-pipeline-build-only.yml`, `template-pipeline-s3-source.yml`) and all three that reference `SourceEventServiceRole` (`template-pipeline.yml`, `template-pipeline-github.yml`, `template-pipeline-build-only.yml`), keeping logical IDs and the actual role name in sync.
4. WHERE renaming these roles is chosen THE change SHALL be characterized as an in-stack role replacement per the Update behavior and impact section, applied on every existing pipeline stack's next update, with the caveat that any external reference to the old role name or ARN must be updated.
5. **Recommended default (deferral):** `CodePipelineServiceRole` and `SourceEventServiceRole` SHOULD NOT be renamed in this spec. Both stay within the 64-character limit whenever `ProjectId ≤ 20`, and renaming them forces a role replacement on every existing pipeline stack across four core templates — broad churn for a 1-character overage / zero-margin case. THE deferral, its rationale, and the `ProjectId ≤ 20` assumption SHALL be documented (in the length budget and the parameter guidance) instead.
6. IF the maintainer instead chooses to rename them THEN criteria 1–4 apply and the renames SHALL be delivered as a coordinated version bump across all affected templates.

### Requirement 5: Record the naming length budget in steering

**User Story:** As a contributor authoring a new template, I want the naming length budget in the always-loaded project steering, so that role names (and other length-limited names) are created within budget by default.

#### Acceptance Criteria

1. THE `AGENTS.md` naming-conventions section SHALL be updated to include the length budget: for any resource whose name has a maximum length, reserve 34 characters for `Prefix` + `ProjectId` + `StageId` (including joining hyphens).
2. THE steering SHALL state the IAM role name limit of 64 characters and the resulting 30-character budget for the static/descriptive portion of a role name.
3. THE steering SHALL note the worker-role pattern `${Prefix}-Worker-${ProjectId}-${StageId}-<Suffix>` and that its suffix SHALL NOT exceed 22 characters.
4. THE steering update SHALL preserve all existing content and blockquotes in `AGENTS.md` and only add the new budget guidance.

### Requirement 6: Documentation and changelog

**User Story:** As a maintainer, I want the affected template documentation and the changelog updated, so that the rename and its one-time role-replacement behavior are discoverable by end users.

#### Acceptance Criteria

1. WHEN a module `RoleName` is changed THEN the corresponding template README under `docs/templates/v2/` SHALL be updated to reflect the new role name.
2. THE `CHANGELOG.md` `v0.0.44 (unreleased)` section SHALL record the role-name change under the **Changed** category, referencing this spec, listing the affected module and template with its version bump, and noting the one-time IAM role replacement and the in-flight-execution caveat.
3. THE documentation update SHALL be the final task and SHALL apply only to templates actually modified.

---

## Out of Scope

- Changing the `MaxLength` of the `Prefix`, `ProjectId`, or `StageId` parameters.
- Renaming logical resource IDs where only the rendered `RoleName` string needs to change (unless a maintainer chooses to for clarity).
- Auditing non-role identifiers (output export names, bucket names, log group names) — bucket-name length is already governed by the existing parameter `ConstraintDescription` guidance.
- Any functional change to IAM policies, trust relationships, or permissions attached to the affected roles.

## Resolved Decisions

1. **Logical ID (Requirement 2):** Keep the logical ID `PromotionSourceEventServiceRole` unchanged; only the rendered `RoleName` string changes.
2. **Impact classification:** Renaming a `RoleName` is an automatic in-stack IAM role replacement, not a migration-required breaking change. It is recorded in the changelog under **Changed** with a role-replacement note (see Update behavior and impact).
3. **Requirement 4 (deferral confirmed):** `CodePipelineServiceRole` and `SourceEventServiceRole` are left unchanged in this spec. Both stay within the 64-character limit whenever `ProjectId ≤ 20`; the `ProjectId ≤ 20` assumption is documented in the length budget. Only `PromotionSourceEventServiceRole` is renamed.
