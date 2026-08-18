# Verification Findings

Pre-flight and review findings for spec `0-0-40-pipeline-with-promotion-approval`.
Each task appends its own distinct section below; do not clobber prior sections.

---

## Task 0.2 — `Atlantis=pipeline-infrastructure` tag is queryable

**Date:** 2026-08-15
**Type:** Read-only investigation / documentation
**Requirements:** 14.5, 14.6
**Status:** Verified by repo inspection (with a gap flagged — see Risk below). Live AWS verification not performed (no valid credentials in this environment: `aws sts get-caller-identity` returned `ExpiredToken`).

### What was inspected

- `templates/v2/pipeline/template-pipeline.yml`, `-github.yml`, `-build-only.yml` (pipeline resource + tag usage)
- All `templates/v2/**` for tag keys/values (`Atlantis`, `pipeline-infrastructure`, `Tags:`)
- `scripts/`, `examples/`, `docs/` for any deploy-time stack-tag configuration
- design.md §10 (Admin-ops approval-audit CLI) and requirements.md §14.5/§14.6

### Findings

1. **The literal tag `Atlantis=pipeline-infrastructure` is not defined anywhere in this repository.** No template, module, script, or example sets a tag with key `Atlantis` and value `pipeline-infrastructure`.

2. **The pipeline templates define no `Tags:` property on any resource.** A search for `Tags:` in `templates/v2/pipeline/*.yml` returned no matches. The `AWS::CodePipeline::Pipeline` resource (`ProjectPipeline`) carries no template-authored tags.

3. **Templates only apply lowercase, namespaced ABAC tags at the resource level**, and only on select resources (e.g., the CloudFront distribution in the network template): `atlantis:Application`, `atlantis:ApplicationDeploymentId`, `atlantis:Prefix`. These are used for ABAC scoping (`aws:ResourceTag/atlantis:ApplicationDeploymentId`), not for pipeline enumeration, and they differ in both **key casing** and **value** from `Atlantis=pipeline-infrastructure`.

4. **The `Atlantis=pipeline-infrastructure` tag is a deploy-time stack tag, not a template tag.** Both requirements.md §14.5 and design.md §10 state it is "applied to all deployed Atlantis pipelines via stack-tag propagation." CloudFormation stack-level tags automatically propagate to taggable resources such as `AWS::CodePipeline::Pipeline`. Per requirements Assumption 4 and `docs/end-user/README.md`, deployment (and therefore stack tagging) is performed by the external Atlantis tooling — `config.py` / `deploy.py` in the separate `atlantis-sam-config-scripts` repo — which is out of scope for this repository. That external tooling is where the tag is expected to be set.

### Risk / gap (flag for Task 7.3 and maintainers)

- The audit CLI in Task 7.3 depends on every Atlantis pipeline actually carrying `Atlantis=pipeline-infrastructure`. This repo does **not** guarantee that tag; it relies entirely on the external deploy tooling applying it as a stack tag. If a pipeline is deployed without that stack tag, the audit queries will silently miss it (false negative), which is a governance blind spot.
- Tag matching is **case-sensitive**. The audit queries must use exactly `Key=Atlantis` / `Values=pipeline-infrastructure` (capital `A`), not the lowercase namespaced `atlantis:*` tags used for ABAC.
- **Recommendation:** confirm with the `atlantis-sam-config-scripts` deploy tooling / samconfig that the `Atlantis=pipeline-infrastructure` stack tag is applied on pipeline stacks, and re-run the live verification queries below once valid credentials are available. Consider documenting the tag as a deploy-tooling requirement.

### Exact CLI query (for Task 7.3)

Primary — enumerate Atlantis pipeline ARNs by tag using the Resource Groups Tagging API:

```bash
aws resourcegroupstaggingapi get-resources \
  --resource-type-filters codepipeline \
  --tag-filters Key=Atlantis,Values=pipeline-infrastructure \
  --query 'ResourceTagMappingList[].ResourceARN' \
  --output text
```

Alternative / confirmation — check tags on a specific pipeline (accepts the pipeline ARN or name as `--resource-arn`):

```bash
aws codepipeline list-tags-for-resource \
  --resource-arn arn:aws:codepipeline:<region>:<account-id>:<pipeline-name> \
  --query "tags[?key=='Atlantis']"
```

Notes for Task 7.3:
- The tagging API returns full ARNs; extract the pipeline **name** (last colon-delimited segment) before calling `aws codepipeline get-pipeline --name <name>`.
- Region/account scoping applies — the tagging API is regional, so run per target region.

---

## Task 1.4 — `account-wide-infrastructure.yml` stays `v0.0.0`; new receiving template starts at `v0.0.0`

**Date:** 2026-08-15
**Type:** Read-only verification / confirmation (no template versions modified)
**Requirements:** 17.2, 17.3, 17.4
**Status:** Confirmed. No changes made to any template version.

### What was inspected

- Header comment block of `templates/v2/account/account-wide-infrastructure.yml` (lines 1–24).
- Requirement 17 acceptance criteria (17.2, 17.3, 17.4) in `requirements.md`.

### Findings

1. **`account-wide-infrastructure.yml` is at `v0.0.0`.** The header comment block declares:

   ```
   # Version: v0.0.0/2026-04-28
   ```

   This is a `PATCH=0` version, which is **development mode**. Per the version-control rule, no auto-increment applies to a development-mode (`v0.0.0`) template — subsequent changes stay at `v0.0.0` until the maintainer promotes it to a released version. The version was **not** changed by this task. This satisfies Requirement 17.3 (keep `account-wide-infrastructure.yml` at `v0.0.0`, development mode, PATCH=0, no auto-increment).

2. **New receiving template will start at `v0.0.0`.** The new `templates/v2/pipeline/template-pipeline-s3-source.yml` (created later in Task 5.1) will start at `v0.0.0` (development mode), per Requirement 17.2. This is consistent with Task 5.1's stated `(v0.0.0)` and Requirement 3.1 (template provided at v0.0.0). The file does not exist yet; confirmation recorded here for when it is authored.

3. **Additive / default-off (17.4).** All spec changes are additive and default-off; no breaking changes and no new versioned template files (e.g., `-v2-1.yml`). Keeping the account-wide template at `v0.0.0` is consistent with the additive lifecycle change noted in Requirement 12.5.

### Confirmed version

- `templates/v2/account/account-wide-infrastructure.yml`: **`v0.0.0/2026-04-28`** — unchanged (development mode).
- `templates/v2/pipeline/template-pipeline-s3-source.yml`: will start at **`v0.0.0`** (to be created in Task 5.1).
---

## Task 4.5 — Backward compatibility of the three origin templates

**Date:** 2026-08-15
**Type:** Read-only verification / conditional reasoning (no template changes)
**Requirements:** 10.3, 10.4, 10.5, 13.5 (task-list citation: 3.7, NFR #1)
**Templates:** `templates/v2/pipeline/template-pipeline.yml` (v2.0.23), `template-pipeline-github.yml` (v2.0.5), `template-pipeline-build-only.yml` (v2.0.7)
**Design refs:** §3.4 (conditions), §4.1 (origin stage composition), §13 (backward-compat summary)
**Conclusion:** **Backward compatible: YES.** With all new promotion parameters at their defaults, each origin pipeline renders structurally identical to its pre-feature form.

### Default parameter values (verified in all three templates)

| Parameter | Default | Effect |
|---|---|---|
| `PromoteTargetStageId` | `""` (empty) | `IsPromoteEnabled = false` |
| `PromoteApprovalRequired` | `"true"` | `IsPromoteApprovalRequired = true` (irrelevant while promotion disabled) |
| `PromoteTargetAccountId` | `""` | `HasPromoteTargetAccount = false` (same-account) — Req 10.3 |
| `PromoteTargetRegion` | `""` | `HasPromoteTargetRegion = false` (current region) — Req 10.4 |
| `PromoteTargetBucket` | `""` | `HasPromoteTargetBucket = false` (derive if ever enabled) — Req 10.5 |

### Conditional reasoning (why nothing new renders at defaults)

All promotion conditions are defined identically in the three templates (verified):

- `IsPromoteEnabled: !Not [!Equals [!Ref PromoteTargetStageId, ""]]` → with the empty default, `!Equals` is **true**, so `IsPromoteEnabled = FALSE`.
- `IsPromoteApprovalRequired: !Equals [!Ref PromoteApprovalRequired, "true"]` → `TRUE` at default, but only ever consumed via the `And` below.
- `IsPromoteEnabledAndApprovalRequired: !And [IsPromoteEnabled, IsPromoteApprovalRequired]` → `FALSE AND TRUE = FALSE`.
- `IsPromoteEnabledAndNotDev: !And [IsNotDevelopment, IsPromoteEnabled]` → `(…) AND FALSE = FALSE` regardless of `DeployEnvironment`.

Because `IsPromoteEnabled` is the base term of every promotion condition, an empty `PromoteTargetStageId` forces all of them false. Consequently:

1. **Module resources are NOT created.** `PromoteServiceRole`, `PromoteProject`, and `PromoteLogGroup` are included via `AWS::Include`, and each module body carries `Condition: IsPromoteEnabledAndNotDev` (verified in `promote-service-role.yml`, `promote-project.yml`, `promote-log-group.yml`). With that condition false, CloudFormation omits all three resources — no IAM role, no CodeBuild project, no log group.
2. **The `ApproveToPromote` stage resolves to `AWS::NoValue`.** The inline stage is wrapped `!If [IsPromoteEnabledAndApprovalRequired, {stage}, !Ref 'AWS::NoValue']`; the condition is false, so the stage element disappears from the `Stages` list.
3. **The `Promote` stage resolves to `AWS::NoValue`.** Wrapped `!If [IsPromoteEnabled, {stage}, !Ref 'AWS::NoValue']`; the condition is false, so the stage element disappears.

Net effect: the rendered `ProjectPipeline` stage list is exactly the pre-feature sequence —
- `template-pipeline.yml` / `-github.yml`: `Source → Build → [Deploy] → [PostDeploy]` (existing optional stages unchanged).
- `template-pipeline-build-only.yml`: `Source → Build → [PostDeploy]`.
No `ApproveToPromote` or `Promote` stage appears, and no promotion resources are created. Structurally identical to before this feature.

### CodePipelineServiceRole `BuildPhase` Promote ARN is additive-only

In all three templates the `BuildPhase` statement of the pipeline service role now lists a third CodeBuild resource ARN:

```yaml
- Sid: BuildPhase
  Action: [ codebuild:* ]
  Effect: Allow
  Resource:
    - arn:aws:codebuild:${AWS::Region}:${AWS::AccountId}:project/${Prefix}-${ProjectId}-${StageId}-Build
    - arn:aws:codebuild:${AWS::Region}:${AWS::AccountId}:project/${Prefix}-${ProjectId}-${StageId}-PostDeploy
    - arn:aws:codebuild:${AWS::Region}:${AWS::AccountId}:project/${Prefix}-${ProjectId}-${StageId}-Promote   # <-- added
```

This is a **pure additive allow-scope entry**: it grants the pipeline role permission to start a `*-Promote` CodeBuild project that, at defaults, does not exist and is never invoked (no Promote stage). Adding an unused resource ARN to an `Allow` statement does not remove or restrict any existing permission and does not alter pipeline behavior. The entry is unconditional (not gated), which is acceptable because an IAM allow on a non-existent resource is inert; it simply avoids a conditional inside the role policy. When the Promote stage is absent, this line has zero behavioral effect. Per the version-control rules this is a non-breaking (PATCH) additive change, consistent with the version bumps applied in Task 1.

### Validation

- `cfn-lint` run on all three templates: **exit 0, no findings.**
  ```
  cfn-lint templates/v2/pipeline/template-pipeline.yml \
           templates/v2/pipeline/template-pipeline-github.yml \
           templates/v2/pipeline/template-pipeline-build-only.yml
  # EXIT=0
  ```

### Requirement mapping

- **10.3 / 10.4 / 10.5** — empty `PromoteTargetAccountId` / `PromoteTargetRegion` / `PromoteTargetBucket` defaults make `HasPromoteTarget*` false; combined with `IsPromoteEnabled=false`, no target resolution occurs and no promotion path is active. Defaults confirmed in all three templates.
- **13.5 (approval notifications, rejection semantics)** — moot at defaults: the `ApproveToPromote` action is not rendered, so no approval notification path exists and no promotion archive/manifest can be written until promotion is explicitly enabled. The default-on `PromoteApprovalRequired="true"` means that when promotion IS later enabled, the manual gate is present by default (fail-safe).
- **3.7 / NFR #1 (task-list citation)** — satisfied: default-off promotion yields a structurally unchanged pipeline.

### Conclusion

**Backward compatible: YES.** All three origin templates are additive and default-off. With promotion parameters at defaults, `IsPromoteEnabled`, `IsPromoteEnabledAndApprovalRequired`, and `IsPromoteEnabledAndNotDev` are all false; the promote modules are not created, and both new stages resolve to `AWS::NoValue`. The only unconditional addition (the `-Promote` ARN in the pipeline service role's `BuildPhase`) is an inert extra allow-scope entry with no behavioral impact when the Promote stage is absent. Existing deployments render identically after this change. cfn-lint validates all three templates clean.

---

## Task 7.3 — Approval-audit CLI documented in `docs/admin-ops/`

**Date:** 2026-08-16
**Type:** Documentation
**Requirements:** 14.1, 14.2, 14.3, 14.4, 14.5
**Status:** Complete.

### What was done

- No existing file for this content was found in `docs/admin-ops/` (only `README.md` and `account-management.md` existed). Created `docs/admin-ops/approval-audit-cli.md` and linked it from `docs/admin-ops/README.md`.
- Used the exact `resourcegroupstaggingapi get-resources` query recorded in Task 0.2's findings above as the enumeration mechanism (Req 14.6), scoped to `Atlantis=pipeline-infrastructure` (Req 14.5).
- Wrote three copy-paste one-liners chaining tag enumeration → `aws codepipeline get-pipeline` → `jq` structure inspection (Req 14.3):
  1. Has a `Promote` stage but no `ApproveToPromote` action (Req 14.2.1).
  2. Has an S3-provider `Source` action but no `ApproveRelease` action (Req 14.2.2).
  3. Union of the above (Req 14.2.3).
- Each command only flags pipelines that actually contain the relevant stage/action type, so non-participating pipelines are never flagged (Req 14.4) — verified against sample data including a plain pipeline with no promotion at all.
- Included the risk/gap note from Task 0.2 (external deploy tooling owns the tag; case-sensitivity) directly in the new doc so operators see the caveat where they'll use the commands.

### Verification performed (no live AWS credentials available)

- Installed `jq` locally and validated filter syntax against hand-built sample JSON shaped to match the real `aws codepipeline get-pipeline` response envelope (`{"pipeline": {"name", "stages": [{"name", "actions": [{"name", "actionTypeId": {"category","owner","provider","version"}}]}]}, "metadata": {...}}`), confirmed via the `codepipeline` botocore service model (`PipelineDeclaration` / `StageDeclaration` / `ActionDeclaration` / `ActionTypeId` shapes).
- Test fixtures: a plain origin pipeline (Promote, no ApproveToPromote), a fully-gated origin pipeline (Promote + ApproveToPromote), a non-promoting pipeline (no Promote stage), a receiving pipeline (S3 source, no ApproveRelease), and a fully-gated receiving pipeline (S3 source + ApproveRelease).
- Ran all three jq filters directly against the fixtures: command 1 matched only the ungated origin pipeline; command 2 matched only the ungated receiving pipeline; command 3 matched the union of both. The non-promoting and fully-gated pipelines were correctly excluded from all three.
- Additionally dry-ran the full bash one-liners (tag enumeration → per-pipeline `get-pipeline` → `jq`) end-to-end using a local shell stand-in for the `aws` CLI that returned the same fixtures, confirming the `awk -F: '{print $NF}'` ARN-to-name extraction and the `tr '\t' '\n'` splitting of the tagging API's `--output text` result work as intended.
- Cleaned up all temporary fixture files after verification.

### Files changed

- `docs/admin-ops/approval-audit-cli.md` (new)
- `docs/admin-ops/README.md` (added link)
