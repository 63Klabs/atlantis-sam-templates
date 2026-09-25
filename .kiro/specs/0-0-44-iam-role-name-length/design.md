# Design Document

**Feature:** IAM RoleName Length Compliance and Naming Length Budget

**Spec:** `0-0-44-iam-role-name-length`
**Repository target version:** v0.0.44 (unreleased)
**Status:** Draft for Review
**Date:** 2026-09-24

**Requirements:** [requirements.md](./requirements.md)

---

## Overview

This design implements the requirements in the narrowest way that solves the problem: it shortens the single over-budget IAM role name (`PromotionSourceEventServiceRole` → `PromoteSrcEventSvcRole`), records a reusable name-length budget in project steering, and updates supporting documentation and the changelog. Per the resolved decisions in the requirements, the logical resource ID is kept unchanged and the two long-standing roles that are only marginally over/at the limit (`CodePipelineServiceRole`, `SourceEventServiceRole`) are intentionally left as-is.

The change surface is deliberately small:

- **One module file** changes: `templates/v2/modules/pipeline/promotion-source-event-service-role.yml`.
- **No parent template changes** are required, because the logical ID `PromotionSourceEventServiceRole` is preserved and the sibling EventBridge rule references the role by that logical ID (`Fn::GetAtt`), not by its rendered name.
- **Steering** (`AGENTS.md`) gains a name-length budget subsection.
- **Documentation and changelog** are updated to reflect the rename and its one-time role-replacement behavior.

### Why the parent template and the event rule need no change

The role is consumed as an `AWS::Include` module under the logical ID `PromotionSourceEventServiceRole` in `templates/v2/pipeline/template-pipeline-s3-source.yml`. The sibling module `promotion-source-event-rule.yml` obtains the role's ARN with:

```yaml
RoleArn:
  Fn::GetAtt:
    - PromotionSourceEventServiceRole   # logical ID (unchanged)
    - Arn
```

`Fn::GetAtt` resolves the logical ID to the role's ARN at deploy time. Because we change only the rendered `RoleName` string and keep the logical ID, this reference — and every other reference in the parent — continues to resolve correctly with no edit. This is the key reason the "keep the logical ID" decision keeps the blast radius to a single module file.

---

## Detailed Design

### 1. Module change: `promotion-source-event-service-role.yml`

Two `Fn::Sub` strings in the module carry the long descriptive suffix: the `RoleName` (64-character limit) and the inline `Policies[0].PolicyName` (128-character limit).

#### 1.1 RoleName (required)

**Before:**

```yaml
  RoleName:
    Fn::Sub: "${Prefix}-Worker-${ProjectId}-${StageId}-PromotionSourceEventServiceRole"
```

**After:**

```yaml
  RoleName:
    Fn::Sub: "${Prefix}-Worker-${ProjectId}-${StageId}-PromoteSrcEventSvcRole"
```

#### 1.2 Inline PolicyName (intentionally unchanged)

The inline policy name is left as `${Prefix}-Worker-${ProjectId}-${StageId}-PromotionSourceEventServicePolicy`. Policy names allow 128 characters, so the long form is well within its limit, and keeping the fully-spelled-out `PromotionSourceEventService` stem serves as an in-template description of what the now-abbreviated role (`PromoteSrcEventSvcRole`) is for. This is a deliberate decision, not an oversight.

`RoleName` is therefore the **only** line that changes in the module. The `Type`, `Condition`, `Path`, `Description`, `PermissionsBoundary`, `AssumeRolePolicyDocument`, the inline `PolicyName`, and the policy statement are all untouched, so trust, permissions boundary, and the granted `codepipeline:StartPipelineExecution` action are unchanged.

### 2. Length verification

The new suffix `PromoteSrcEventSvcRole` is 22 characters. For the worker-role pattern the non-variable (static) content is:

| Static segment | Chars |
|---|---|
| `-Worker-` | 8 |
| `-` (after `ProjectId`) | 1 |
| `-` (before suffix) | 1 |
| `PromoteSrcEventSvcRole` | 22 |
| **Static total** | **32** |

Combined with the assumed variable footprint (`Prefix` 6 + `ProjectId` 20 + `StageId` 6 = 32):

- **Total at assumed footprint = 32 + 32 = 64** — within the 64-character limit (exactly at the boundary).
- The name fits whenever `len(Prefix) + len(ProjectId) + len(StageId) ≤ 32`.
- **At the absolute maximum footprint** (`Prefix` 8 + `ProjectId` 26 + `StageId` 8 = 42) the name would be 74 characters — this is the documented, accepted tradeoff (see requirements "Update behavior and impact"); the parameter `ConstraintDescription` already recommends `Prefix + ProjectId ≤ 28`.

> **Design note (boundary):** `PromoteSrcEventSvcRole` lands exactly at 64 at the assumed footprint, so there is zero slack when `Prefix`=6 / `ProjectId`=20 / `StageId`=6. This matches the name the maintainer selected and satisfies the budget. If additional margin is desired later, the suffix can be shortened further (each character removed buys one character of `ProjectId` headroom); no other name in the repository depends on this string.

### 3. Steering: `AGENTS.md` name-length budget

Add a new subsection to the "Naming Conventions (Required)" section of `AGENTS.md`, immediately after the `#### S3` subsection, preserving all existing content. Proposed content:

```markdown
#### Resource Name Length Budget

Some AWS resource names have a maximum length. IAM role names, for example, are limited to **64 characters** (the role *path* is a separate value and does not count toward that limit).

For any length-limited name built as `Prefix-ProjectId-StageId-Resource`, reserve **34 characters** for `Prefix` + `ProjectId` + `StageId` and the two hyphens that join them (assuming a reasonable footprint of `Prefix` 6, `ProjectId` 20, `StageId` 6 = 32, plus 2 hyphens). Budget the remaining characters for the static/descriptive portion of the name.

For IAM role names (64-character limit) the static/descriptive portion must therefore not exceed **30 characters**.

Worker roles follow the pattern `${Prefix}-Worker-${ProjectId}-${StageId}-<Suffix>`; keep `<Suffix>` to **22 characters or fewer** (the literal `Worker` plus hyphens consume the rest of the 30-character static budget).

> **Note:** The 34-character reservation assumes `Prefix`/`ProjectId`/`StageId` stay within the reasonable footprint above, not their absolute maximums (8/26/8). Deployments that use the maximum-length values can still exceed a name's limit; keep `Prefix + ProjectId` at or under 28 characters (as the parameter `ConstraintDescription` recommends). Parameter `MaxLength` values are intentionally left unchanged.
```

This satisfies Requirement 5 (all four acceptance criteria) and preserves existing `AGENTS.md` content and structure.

### 4. Documentation

`docs/templates/v2/pipeline/template-pipeline-s3-source-README.md` documents the role under the heading `### PromotionSourceEventServiceRole` (the logical ID, which is unchanged) and identifies it by module path. It does not print the rendered role name, so the heading and anchor remain valid.

To keep the documentation accurate and helpful, add one clarifying line to that section stating the rendered role name and why it is abbreviated:

```markdown
Rendered role name: `${Prefix}-Worker-${ProjectId}-${StageId}-PromoteSrcEventSvcRole` (abbreviated to stay within the 64-character IAM role name limit).
```

No table-of-contents entry, anchor, or other README section changes are needed because the logical ID is unchanged. The `promotion-source-event-rule.yml` documentation and the modules inventory reference the role by logical ID only and need no change.

### 5. Changelog

Add an entry under the existing `## v0.0.44 (unreleased)` section, in the **Changed** category (not Breaking Changes — see the requirements "Update behavior and impact" for the classification rationale), referencing this spec:

```markdown
### Changed
- **IAM RoleName Length Compliance** [Spec: 0-0-44-iam-role-name-length](.kiro/specs/0-0-44-iam-role-name-length/) - Shortened the promotion source-event service role name to fit the 64-character IAM role name limit at the recommended naming footprint
  - Modules: promotion-source-event-service-role.yml - Renamed the rendered `RoleName` from `${Prefix}-Worker-${ProjectId}-${StageId}-PromotionSourceEventServiceRole` to `${Prefix}-Worker-${ProjectId}-${StageId}-PromoteSrcEventSvcRole`; the logical ID `PromotionSourceEventServiceRole` and the inline policy name are unchanged. **One-time effect:** updating an existing receiving-pipeline stack replaces this EventBridge-invoked IAM role (new name, new ARN); apply the update when no promotion pipeline execution is in flight.
```

> The changelog entry documents the one-time IAM role replacement and the in-flight-execution caveat so operators can time the update, consistent with Requirement 6.

---

## Change Inventory

| File | Change | Versioned? |
|---|---|---|
| `templates/v2/modules/pipeline/promotion-source-event-service-role.yml` | `RoleName` suffix shortened (inline `PolicyName` intentionally unchanged) | Module (unversioned) — no version header |
| `templates/v2/pipeline/template-pipeline-s3-source.yml` | **No change** (logical ID preserved) | n/a |
| `templates/v2/modules/pipeline/promotion-source-event-rule.yml` | **No change** (references role by logical ID) | n/a |
| `AGENTS.md` | Add "Resource Name Length Budget" subsection | n/a |
| `docs/templates/v2/pipeline/template-pipeline-s3-source-README.md` | Add rendered-role-name clarification line | n/a |
| `CHANGELOG.md` | Add **Changed** entry under `v0.0.44 (unreleased)` | n/a |

**Not changed (per resolved decisions):**
- `templates/v2/modules/pipeline/source-event-service-role.yml` (`SourceEventServiceRole`, at limit — left as-is)
- The inline `CodePipelineServiceRole` in the four pipeline templates (over by 1 — left as-is)

---

## Version Control Assessment

Per the template version-control steering, versioning applies to **templates**, not `AWS::Include` module snippets (modules carry no version header and are loaded in place from S3). The only file with resource content changing is a module, so no template version increment or new versioned file is created.

The parent template `template-pipeline-s3-source.yml` is unchanged and remains at its current development version (`v0.0.0`, `PATCH = 0`); even if it were touched, development-mode templates take no automatic PATCH increment. No new versioned template file is required because this is not a template-level breaking change — it is an in-module rename with an automatic in-stack role replacement.

---

## Impact and Rollout

The behavioral impact is exactly as characterized in the requirements "Update behavior and impact" section:

- Changing `RoleName` causes CloudFormation to **replace** the IAM role on the next stack update: create the new role → repoint the in-stack EventBridge rule target to the new ARN → delete the old role. Fully automatic; no manual migration.
- The role is created only in TEST/PROD (`Condition: IsNotDevelopment`), lives entirely within the receiving-pipeline stack, and is not exported, so no dependent stack is affected.
- `RolePath` is unchanged and the pipeline management role grants IAM permissions on the `${Prefix}-Worker-*` wildcard, so the renamed role remains covered with no permission change.
- **Operational caveat:** apply the update when no promotion pipeline execution is in flight, since the EventBridge-invoke role is momentarily replaced.

Because the module ships from S3 and is spliced at deploy time, the fix reaches consumers as soon as the updated module is published to the module bucket(s); each receiving-pipeline stack picks it up on its next update.

---

## Testing and Validation

Per the project testing guidelines, favor fast, concrete checks over property-based tests.

1. **Rendered-name length check (unit):** Render the module `RoleName` `Fn::Sub` with the assumed footprint (`Prefix`=`abcdef` 6, `ProjectId`=`abcdefghijklmnopqrst` 20, `StageId`=`abcdef` 6) and assert the result is `≤ 64` characters (expected exactly 64). Optionally assert the suffix `PromoteSrcEventSvcRole` is `≤ 22` characters as a guard for the budget.
2. **Static-audit guard (unit, optional):** A small test that scans `templates/v2/**/*.yml` for `RoleName: Fn::Sub` values, extracts the static (non-`${...}`) portion, and asserts it is `≤ 30` characters — with `source-event-service-role.yml` (30, at limit) and the inline `CodePipelineServiceRole` (31, intentionally deferred) recorded as known, accepted exceptions so the guard documents the decision rather than failing the build. (Include only if it runs quickly and adds value beyond the single rendered-name check.)
3. **cfn-lint:** Run the repository's cfn-lint step against `template-pipeline-s3-source.yml` to confirm the module still splices cleanly (the existing `E6101/W2001/W8001` suppressions already cover `AWS::Include`); expect no new findings.
4. **Docs/link check:** Confirm the README anchor `#promotionsourceeventservicerole` still resolves (unchanged) and the added rendered-name line is accurate.

---

## Design Decisions and Rationale

1. **Keep the logical ID (`PromotionSourceEventServiceRole`).** Preserving it confines the change to one module file and avoids editing the parent template and the sibling event-rule `Fn::GetAtt`. Renaming the logical ID would itself force role replacement (same end effect) while adding edit surface and churn for no benefit.
2. **Shorten only the promotion role.** It is the only name that exceeds the budget under the reasonable footprint. `SourceEventServiceRole` (exactly 30 static) and `CodePipelineServiceRole` (31 static) are long-standing across the core pipeline templates; renaming them would replace a role on every existing pipeline stack for a zero-margin / 1-character case that stays within budget whenever `ProjectId ≤ 20`. Deferral is recorded in the requirements.
3. **Keep the inline policy name fully spelled out.** The policy name has a 128-character limit and is nowhere near it, so there is no reason to abbreviate it. Retaining `PromotionSourceEventServicePolicy` lets the inline policy name act as an in-template description of the abbreviated role (`PromoteSrcEventSvcRole`), which improves readability rather than hurting it.
4. **Classify as Changed, not Breaking.** A plain stack update performs the replacement with no user intervention or migration procedure, so per the changelog steering this is a Changed entry with an explicit role-replacement note rather than a Breaking Change requiring a migration guide.
5. **Record the budget in steering, not just the fix.** Putting the 34/30/22 budget in `AGENTS.md` prevents recurrence: future role names are authored within budget by default, which is the systemic root-cause fix behind this one-off rename.
