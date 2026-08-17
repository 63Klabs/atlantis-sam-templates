# Manual Two-Account Promotion Integration Test

This is a step-by-step manual procedure for validating cross-account promotion
end-to-end. It exists because cross-account behavior (a `PutObject` from one
AWS account's `PromoteServiceRole` landing in another account's S3 bucket,
triggering EventBridge, and starting a pipeline in that second account)
cannot be exercised in CI. Run this procedure whenever you touch the
promotion send/receive path (`template-pipeline.yml`,
`template-pipeline-github.yml`, `template-pipeline-build-only.yml`,
`template-pipeline-promoted-artifact.yml`, `account-wide-infrastructure.yml`,
or any of the `modules/pipeline/promote-*` / `promotion-source-event-*`
modules).

> **Design reference:** this procedure exercises the flow documented in
> [`.kiro/specs/0-0-40-pipeline-with-promotion-approval/design.md`](../../.kiro/specs/0-0-40-pipeline-with-promotion-approval/design.md)
> §2.1 (end-to-end flow), §5 (Promote stage / manifest), §6 (IAM), and §7
> (account-wide bucket changes). Requirements 1-13 of
> [`requirements.md`](../../.kiro/specs/0-0-40-pipeline-with-promotion-approval/requirements.md)
> define the acceptance criteria this procedure verifies.

## What this validates

- A commit built and approved in a **sending** account/stage is handed off as
  `source.zip` + `promote.json` into a **receiving** account/stage's S3
  promotions prefix.
- The receiving pipeline is triggered by EventBridge on arrival of the
  archive, gates on `ApproveRelease` (if enabled), and builds/deploys from
  the promoted source.
- Rollback (re-promoting an older commit / S3 object version) re-triggers the
  receiving pipeline via S3 versioning.
- The same-account path (no second AWS account required) works identically
  minus the cross-account bucket policy.

Naming below follows the repository convention
`Prefix-ProjectId-StageId-Resource` (see [AGENTS.md](../../AGENTS.md)). The
example project uses `Prefix=atl`, `ProjectId=promotest`.

---

## 1. Prerequisites

You need **two AWS accounts** to test the cross-account path (Sections 2-7).
If you only have one account, skip to Section 8 for the same-account
variant, which validates most of the same logic.

Throughout this procedure:
- **SENDING account** = the account/stage the commit is promoted *from*
  (e.g. `test`). Placeholder account ID: `111111111111`.
- **RECEIVING account** = the account/stage the commit is promoted *into*
  (e.g. `beta`). Placeholder account ID: `222222222222`.
- Both accounts use the same region for this walkthrough (e.g. `us-east-1`);
  set `PromoteTargetRegion` on the sender if you also want to validate the
  cross-region path.

1.1. In **both** accounts, deploy (or confirm already deployed) the
   account-wide infrastructure stack from `templates/v2/account/account-wide-infrastructure.yml`,
   including the S3 artifacts bucket (`EnableS3ArtifactsBucket=true`). Note
   each bucket's resolved name (an `S3ArtifactsBucketName` output), e.g.:
   - SENDING: `cf-artifacts-111111111111-us-east-1-an`
   - RECEIVING: `cf-artifacts-222222222222-us-east-1-an`

1.2. In the **RECEIVING** account, update/redeploy `account-wide-infrastructure.yml`
   with:
   - `PromotionSourceAccountIds = 111111111111` (the SENDING account ID)
   - `EnableS3ArtifactsBucketEventBridge = true`

   Confirm after deploy:
   - The bucket policy on the receiving bucket contains the
     `AllowCrossAccountPromotionWrite` statement (check via S3 console or
     `aws s3api get-bucket-policy --bucket cf-artifacts-222222222222-us-east-1-an`),
     scoped to `.../promotions/*` and conditioned on
     `aws:PrincipalArn` LIKE `arn:aws:iam::*:role/*-PromoteServiceRole`.
   - The bucket's `NotificationConfiguration` has `EventBridgeConfiguration`
     enabled (`aws s3api get-bucket-notification-configuration --bucket cf-artifacts-222222222222-us-east-1-an`).

1.3. In **both** accounts, confirm the prefix's CloudFormation service role
   and pipeline management role exist (deployed via
   `template-service-role-pipeline.yml` and `prefix-based-infrastructure.yml`)
   so pipeline stacks can be deployed under `Prefix=atl`.

---

## 2. Deploy the origin (sending) pipeline

In the **SENDING** account, deploy `templates/v2/pipeline/template-pipeline.yml`
(or `-github.yml`) with:

| Parameter | Value |
|---|---|
| `Prefix` | `atl` |
| `ProjectId` | `promotest` |
| `StageId` | `test` |
| `PromoteTargetStageId` | `beta` |
| `PromoteApprovalRequired` | `true` |
| `PromoteTargetAccountId` | `222222222222` |
| `PromoteTargetRegion` | *(empty, or explicit region for cross-region test)* |
| `PromoteTargetBucket` | *(leave empty to use the derived name)* |

Deploy via your normal Atlantis `deploy.py` workflow (or `aws cloudformation
deploy`) pointing at a small test repo/branch.

Confirm after deploy:
- `aws codepipeline get-pipeline --name atl-promotest-test-Pipeline` shows a
  `Promote` stage preceded by an `ApproveToPromote` manual-approval stage,
  after `Deploy`/`PostDeploy`.
- The `atl-Worker-promotest-test-PromoteServiceRole` role exists with an
  inline policy scoped to `arn:aws:s3:::cf-artifacts-222222222222-us-east-1-an/promotions/*`.

---

## 3. Deploy the receiving pipeline

In the **RECEIVING** account, deploy
`templates/v2/pipeline/template-pipeline-promoted-artifact.yml` with:

| Parameter | Value |
|---|---|
| `Prefix` | `atl` (must match sender) |
| `ProjectId` | `promotest` (must match sender) |
| `StageId` | `beta` (must equal sender's `PromoteTargetStageId`) |
| `ReleaseApprovalRequired` | `true` |
| `DeployStageEnabled` | `true` |

Confirm after deploy:
- `aws codepipeline get-pipeline --name atl-promotest-beta-Pipeline` shows an
  S3 `Source` action reading `promotions/atl-promotest/beta/source.zip` from
  the receiving account's artifacts bucket, followed by an `ApproveRelease`
  manual-approval stage, then `Build`/`Deploy`.
- The `WatchedPromotionKey` stack output equals
  `promotions/atl-promotest/beta/source.zip` — this must match the key the
  sender's Promote stage writes to (see §5.2 in design.md).
- `aws events list-rules --name-prefix atl-promotest-beta-PromotionSourceEvent`
  shows the rule, targeting `atl-promotest-beta-Pipeline`.

> If you're using the [approval-audit CLI](../admin-ops/) (task 7.3), run it
> now against both accounts to confirm both gates show as **enabled** before
> the test begins — this gives you a clean baseline to compare against after
> Section 9's rollback/gate checks.

---

## 4. Trigger a build and approve the promotion

4.1. Push a commit to the sending pipeline's source (CodeCommit branch or
   GitHub branch, per the template used). Confirm the pipeline execution
   proceeds through `Source → Build → Deploy` (and `PostDeploy` if enabled)
   successfully.

4.2. Confirm the pipeline execution pauses at `ApproveToPromote`. In the
   CodePipeline console (or via the `PipelineNotificationTopic` email if
   subscribed), review the `CustomData` message — it should reference
   `atl-promotest-test` promoting to stage `beta`.

4.3. Approve the action:
   ```
   aws codepipeline put-approval-result \
     --pipeline-name atl-promotest-test-Pipeline \
     --stage-name ApproveToPromote \
     --action-name ApproveToPromote \
     --result summary="approved for integration test",status=Approved \
     --token <token-from-get-pipeline-state>
   ```

4.4. Confirm the `Promote` CodeBuild action runs and succeeds. Check its logs
   (`/aws/codebuild/atl-promotest-test-Promote`) for the upload sequence:
   `promote.json` written first, then `source.zip` (per design §5.1's
   write-ordering invariant).

4.5. In the **RECEIVING** account, confirm both objects landed:
   ```
   aws s3api list-object-versions \
     --bucket cf-artifacts-222222222222-us-east-1-an \
     --prefix promotions/atl-promotest/beta/
   ```
   You should see `source.zip` and `promote.json`, each with a version ID.
   Note the `source.zip` version ID — you'll use it for the rollback check
   in Section 7.

---

## 5. Verify the EventBridge trigger and Approve-Release gate

5.1. In the **RECEIVING** account, confirm a new execution started on
   `atl-promotest-beta-Pipeline` shortly after the `source.zip` write (check
   `aws codepipeline list-pipeline-executions --pipeline-name atl-promotest-beta-Pipeline`).
   If no execution started, see the Troubleshooting table below.

5.2. Confirm the execution pauses at `ApproveRelease` (between `Source` and
   `Build`). Approve it:
   ```
   aws codepipeline put-approval-result \
     --pipeline-name atl-promotest-beta-Pipeline \
     --stage-name ApproveRelease \
     --action-name ApproveRelease \
     --result summary="approved for integration test",status=Approved \
     --token <token-from-get-pipeline-state>
   ```

5.3. Confirm `Build` and `Deploy` (and `PostDeploy` if enabled) complete
   successfully in the receiving account, deploying the promoted application
   stack under `Prefix-ProjectId-StageId` = `atl-promotest-beta`.

---

## 6. Verify the audit manifest

Fetch `promote.json` and confirm its contents match the schema in design.md
§5.4:

```
aws s3 cp s3://cf-artifacts-222222222222-us-east-1-an/promotions/atl-promotest/beta/promote.json -
```

Check for all of:
- `project` = `promotest`, `prefix` = `atl`
- `git_sha` (40-char) and `git_sha_short` (7-char) match the commit you pushed
  in step 4.1 (`git log -1 --format=%H` / `%h` on that commit)
- `source_archive_key` = `promotions/atl-promotest/beta/source.zip`
- `promoted_from_stage` = `test`, `target_stage` = `beta`
- `promoted_at` is a plausible ISO-8601 UTC timestamp for when you approved
  the promotion
- `source_account_id` = `111111111111`, `target_account_id` = `222222222222`,
  `target_region` matches, `target_bucket` = `cf-artifacts-222222222222-us-east-1-an`
- `source_pipeline_execution_id` matches the SENDING pipeline's execution ID
  from step 4.1
- `post_deploy_passed` is present (meaningful only if PostDeploy ran on the
  sending side)
- `target_deploy_env` and `promoted_by` are **absent** (intentionally
  omitted per Req 10.2 / 11.5 — do not treat their absence as a bug)

---

## 7. Rollback verification

7.1. Push a second commit to the sending pipeline and repeat Section 4
   (build → approve → Promote) so a **second** version of `source.zip`
   exists at the same key.

7.2. Confirm the receiving pipeline auto-triggered and ran against the
   second commit's SHA (check the new `promote.json`'s `git_sha`).

7.3. Now roll back: re-copy the **first** version's `source.zip` onto the
   stable key using its noted version ID from step 4.5:
   ```
   aws s3api get-object \
     --bucket cf-artifacts-222222222222-us-east-1-an \
     --key promotions/atl-promotest/beta/source.zip \
     --version-id <first-version-id> \
     rollback-source.zip

   aws s3 cp rollback-source.zip \
     s3://cf-artifacts-222222222222-us-east-1-an/promotions/atl-promotest/beta/source.zip
   ```
   This creates a **new** object version with the **old** commit's content.

7.4. Confirm this write produces a new `Object Created` event and a new
   receiving-pipeline execution starts (EventBridge fires on any write to
   the watched key, regardless of content — Req 1.5 / 8.4). Approve
   `ApproveRelease` again and confirm the build/deploy uses the rolled-back
   commit (check the built artifact or a deploy-time marker specific to your
   test app).

> Note: rolling back this way does not update `promote.json` (you only
> re-wrote `source.zip`). This is expected — `promote.json` is a rolling,
> write-only audit file tied to the *last Promote stage run*, not to
> whichever `source.zip` version happens to be current. If you need the
> manifest to reflect the rollback, re-run Section 4 against the older
> commit from the sending pipeline instead of manually copying the S3
> object version.

---

## 8. Same-account variant (single AWS account, no second account needed)

Repeat Sections 2-7 within **one** account, using two stages (e.g. `test` and
`beta`) instead of two accounts:

- Deploy the origin pipeline with `PromoteTargetAccountId` **empty** (and
  `PromoteTargetRegion` empty) — this is same-account/same-region promotion.
- Skip step 1.2's cross-account bucket policy setup entirely; `PromotionSourceAccountIds`
  can stay empty. `EnableS3ArtifactsBucketEventBridge=true` is still required.
- Deploy the receiving pipeline (`StageId=beta`) in the same account.
- Everything else (Sections 4-7) is identical — the sending pipeline's
  `PromoteServiceRole` writes to the same account's own artifacts bucket
  rather than a cross-account one.

This variant is useful for a quick sanity check of the trigger/manifest/
approval-gate logic without provisioning a second account, but it does
**not** exercise the cross-account bucket policy statement or cross-account
`PutObject` — run Sections 1-7 at least once against two real accounts
before relying on this feature in production.

---

## 9. Cleanup

After the test, remove the test-only resources so they don't linger:

9.1. Delete both pipeline stacks:
   - SENDING account: delete the `atl-promotest-test-*` pipeline stack.
   - RECEIVING account: delete the `atl-promotest-beta-*` pipeline stack.

9.2. Remove the test promotion objects and their versions from the
   receiving bucket (versioned buckets require deleting each version):
   ```
   aws s3api list-object-versions \
     --bucket cf-artifacts-222222222222-us-east-1-an \
     --prefix promotions/atl-promotest/ \
     --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' \
     > /tmp/promotest-versions.json

   aws s3api delete-objects \
     --bucket cf-artifacts-222222222222-us-east-1-an \
     --delete file:///tmp/promotest-versions.json
   ```
   Also delete any `DeleteMarkers` the same way if present.

9.3. If you changed `PromotionSourceAccountIds` / `EnableS3ArtifactsBucketEventBridge`
   on the receiving account's `account-wide-infrastructure.yml` solely for
   this test and don't want them left enabled, redeploy with the prior
   values (or leave enabled if you intend to use promotion going forward —
   these are opt-in, additive settings and safe to leave on).

9.4. Delete any test source repository branches/commits created for this
   procedure.

---

## Troubleshooting

| Symptom | Likely cause | Resolution |
|---|---|---|
| `Promote` CodeBuild action fails with `AccessDenied` on `PutObject` | `PromotionSourceAccountIds` on the receiving account doesn't include the sending account, or the writer role doesn't match `*-PromoteServiceRole` | Re-check §1.2; confirm the bucket policy statement and the sending role name |
| `source.zip`/`promote.json` land in the receiving bucket, but the receiving pipeline never starts | `EnableS3ArtifactsBucketEventBridge` is `false`, or the EventBridge rule's key pattern doesn't match | Confirm §1.2 and the rule's `detail.object.key` equals `promotions/atl-promotest/beta/source.zip` exactly |
| Receiving pipeline starts but its `Source` action fails / pulls stale content | `S3ObjectKey` on the receiving Source action doesn't match the sender's write key (mismatched `Prefix`/`ProjectId`/`StageId`) | Confirm sender's `PromoteTargetStageId` equals receiver's `StageId`, and `Prefix`/`ProjectId` match on both sides (design §5.2) |
| `ApproveToPromote` / `ApproveRelease` never appears | Approval parameter was left/set to `false` | Confirm `PromoteApprovalRequired`/`ReleaseApprovalRequired` are `true` on the relevant template, or use the [approval-audit CLI](../admin-ops/) to check the deployed pipeline structure |
| Rollback write doesn't re-trigger the pipeline | You overwrote the key with identical bytes and no new version was created, or EventBridge notifications got disabled between tests | Confirm `aws s3api list-object-versions` shows a new version ID after the rollback copy; re-check EventBridge is still enabled |

---

## Related documentation

- [Approval-audit CLI](../admin-ops/) — copy-paste commands to check
  `ApproveToPromote`/`ApproveRelease` gate state across deployed pipelines
  before and after this test.
- [`template-pipeline-promoted-artifact-README.md`](../templates/v2/pipeline/template-pipeline-promoted-artifact-README.md) —
  end-user parameter/resource/output reference for the receiving template.
- [design.md](../../.kiro/specs/0-0-40-pipeline-with-promotion-approval/design.md) —
  full architecture, IAM, and data model reference for this feature.
