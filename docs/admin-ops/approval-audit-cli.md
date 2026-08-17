# Approval-Audit CLI: Finding Ungated Promotion Pipelines

The promotion feature (spec `0-0-40-pipeline-with-promotion-approval`) adds two independent, default-on manual approval gates:

- **`ApproveToPromote`** — on the *sending* (origin) pipeline, gated by the `PromoteApprovalRequired` parameter. When disabled (`false`), a completed build is promoted to the next stage with no human review.
- **`ApproveRelease`** — on the *receiving* (promoted-artifact) pipeline, gated by the `ReleaseApprovalRequired` parameter. When disabled (`false`), every incoming promotion is built and deployed automatically with no human review.

If both gates are disabled on a chained pair of pipelines, a commit can flow from one stage into another — potentially into a PROD stage — with **zero human approval at any point**. Because both parameters default to `true`, an operator must deliberately opt out of each gate; these commands let an administrator audit an account/region for pipelines where that opt-out has happened, so ungated promotion paths are a known, reviewed condition rather than a silent one.

All three commands below are **read-only / non-destructive**. They only call `list-tags-for-resource` (via the Resource Groups Tagging API) and `get-pipeline` — no pipeline, stage, or approval state is created, modified, or deleted.

## How detection works

Each command:

1. Enumerates candidate pipelines using the AWS Resource Groups Tagging API, restricted to resources tagged `Atlantis=pipeline-infrastructure` (this tag is applied at deploy time by the Atlantis config/deploy tooling as a propagated stack tag — see the note below). This keeps the audit scoped to Atlantis-managed pipelines and avoids false positives from unrelated CodePipeline pipelines in the same account.
2. Calls `aws codepipeline get-pipeline --name <pipeline>` for each candidate and inspects the returned `stages[].actions[]` structure with `jq` — the same "detection method A" (structure inspection) used elsewhere in this design, keying on the fixed action names `ApproveToPromote` and `ApproveRelease`.
3. Flags a pipeline only if it actually participates in the relevant flow (has a `Promote` stage for command 1, or an S3-provider `Source` action for command 2) — pipelines that don't promote or don't receive promotions at all are never flagged.

> **Note on the `Atlantis=pipeline-infrastructure` tag:** this repository's templates do not themselves set this tag — it is a deploy-time stack tag applied by the external Atlantis config/deploy tooling (`config.py`/`deploy.py`), which then propagates to the `AWS::CodePipeline::Pipeline` resource. If a pipeline was deployed without that stack tag, these commands will silently miss it (a false negative), so treat a clean result as "no ungated pipelines *found*," not an absolute guarantee. Confirm with your deploy tooling that the tag is applied to every pipeline stack before relying on these commands for compliance reporting. Tag matching is case-sensitive: use exactly `Key=Atlantis`, `Values=pipeline-infrastructure` (capital `A`) — this differs from the lowercase, namespaced `atlantis:*` resource tags (e.g. `atlantis:Application`) used elsewhere for ABAC scoping, which are unrelated to this audit.

Run each command with credentials for the account/region you want to audit; the Resource Groups Tagging API is regional, so repeat per region as needed.

---

## Command 1 — Promote stage with no `ApproveToPromote` gate

Flags origin pipelines where `PromoteTargetStageId` is set (a `Promote` stage exists) but `PromoteApprovalRequired=false` is in effect (no `ApproveToPromote` action precedes it). **Consequence:** a successful build on this pipeline is promoted to the next stage automatically, with no human review of what is being sent forward.

```bash
aws resourcegroupstaggingapi get-resources --resource-type-filters codepipeline --tag-filters Key=Atlantis,Values=pipeline-infrastructure --query 'ResourceTagMappingList[].ResourceARN' --output text | tr '\t' '\n' | awk -F: '{print $NF}' | while read -r p; do aws codepipeline get-pipeline --name "$p" | jq -r 'select(.pipeline.stages | any(.name=="Promote")) | select([.pipeline.stages[].actions[]?.name] | index("ApproveToPromote") | not) | .pipeline.name'; done
```

## Command 2 — S3-sourced (promoted-artifact) pipeline with no `ApproveRelease` gate

Flags receiving pipelines (built from `template-pipeline-promoted-artifact.yml`, identifiable by an S3-provider `Source` action) where `ReleaseApprovalRequired=false` is in effect (no `ApproveRelease` action between Source and Build). **Consequence:** every incoming promotion archive is built and deployed into this stage automatically, with no review of what arrived before it goes live.

```bash
aws resourcegroupstaggingapi get-resources --resource-type-filters codepipeline --tag-filters Key=Atlantis,Values=pipeline-infrastructure --query 'ResourceTagMappingList[].ResourceARN' --output text | tr '\t' '\n' | awk -F: '{print $NF}' | while read -r p; do aws codepipeline get-pipeline --name "$p" | jq -r 'select([.pipeline.stages[].actions[]?.actionTypeId.provider] | index("S3")) | select([.pipeline.stages[].actions[]?.name] | index("ApproveRelease") | not) | .pipeline.name'; done
```

## Command 3 — Either condition (combined)

Union of commands 1 and 2: any Atlantis pipeline with at least one disabled promotion/release gate. Use this as the primary sweep; use commands 1 and 2 individually when you need to know *which* gate is missing.

```bash
aws resourcegroupstaggingapi get-resources --resource-type-filters codepipeline --tag-filters Key=Atlantis,Values=pipeline-infrastructure --query 'ResourceTagMappingList[].ResourceARN' --output text | tr '\t' '\n' | awk -F: '{print $NF}' | while read -r p; do aws codepipeline get-pipeline --name "$p" | jq -r '([.pipeline.stages[].actions[]?.name]) as $a | ([.pipeline.stages[].actions[]?.actionTypeId.provider] ) as $pr | select(((.pipeline.stages | any(.name=="Promote")) and ($a | index("ApproveToPromote") | not)) or (($pr | index("S3")) and ($a | index("ApproveRelease") | not))) | .pipeline.name'; done
```

---

## Notes

- **Read-only:** these commands only call `resourcegroupstaggingapi get-resources` and `codepipeline get-pipeline`. Neither mutates any resource, so they are safe to run against production accounts at any time.
- **No output = no findings.** An empty result from any command means no Atlantis-tagged pipeline in the current account/region matched that condition (subject to the tagging caveat above).
- **`awk -F: '{print $NF}'`** extracts the pipeline name from the full ARN returned by the tagging API (`arn:aws:codepipeline:<region>:<account-id>:<pipeline-name>`), since `get-pipeline` takes a bare name, not an ARN.
- **Chained promotion:** a single stage can be both a receiving pipeline (for the stage before it) and a sending pipeline (for the stage after it) — for example a `beta` stage built from `template-pipeline-promoted-artifact.yml`. Such a pipeline can appear in the results of command 1 (if its own `Promote` gate is off), command 2 (if its own `ApproveRelease` gate is off), or both.
- **jq required.** These one-liners depend on `jq` being installed on the machine running them (`apt install jq`, `brew install jq`, etc.).
