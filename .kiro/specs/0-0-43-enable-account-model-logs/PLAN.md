# Plan: Account-Wide Bedrock Model Invocation Logging

## Goal

Add an account-wide, opt-in feature to `account-wide-infrastructure.yml` that provisions the
CloudWatch Logs destination and IAM role/policy required for Amazon Bedrock model invocation
logging, modeled directly after the existing account-wide API Gateway CloudWatch logging
feature (`EnableApiGwCloudWatchLogs` / `apigw-cloudwatch-role.yml` / `apigw-cloudwatch-account.yml`).

## Background / AWS Research Findings

Sources: [Bedrock model invocation logging guide](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html),
[AWS Prescriptive Guidance: configure Bedrock invocation logging via CloudFormation](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/configure-bedrock-invocation-logging-cloudformation.html).

- Model invocation logging is **disabled by default**, configured **per account, per Region**
  (same scope as API Gateway's account-level CloudWatch role — a one-time setup).
- To log to CloudWatch, AWS requires two pieces of CloudFormation-native infrastructure,
  which this feature will create:
  1. A **CloudWatch Logs log group** to receive the logs.
  2. An **IAM role** that Bedrock assumes, trusted via `Principal: bedrock.amazonaws.com`
     with `sts:AssumeRole`, scoped with `aws:SourceAccount` and `aws:SourceArn`
     (`arn:aws:bedrock:<region>:<account>:*`) condition keys (tighter than the API Gateway
     role, which has no such conditions — Bedrock's documented trust policy includes them,
     so we follow AWS's documented shape rather than the API Gateway shape verbatim).
  3. An **IAM policy** on that role granting `logs:CreateLogStream` and `logs:PutLogEvents`
     scoped to the log group and the documented log stream name
     `aws/bedrock/modelinvocations`.
- **Key difference from API Gateway**: there is no `AWS::ApiGateway::Account`-equivalent
  native CloudFormation resource type for Bedrock. Turning the setting on account-wide is
  only possible via the `PutModelInvocationLoggingConfiguration` API (console, CLI, SDK) —
  AWS's own reference CFN pattern uses a Lambda-backed custom resource to call that API.
- **Decision (confirmed with user):** do NOT introduce a Lambda-backed custom resource (no
  precedent for Lambda/`Custom::` resources in this module system). Instead:
  - This template creates the log group + IAM role/policy only (pure CFN, matches the
    `AWS::Include` module pattern used everywhere else).
  - The last-mile activation step (`aws bedrock put-model-invocation-logging-configuration`)
    is a **documented manual/CLI post-deployment step**, exactly like the existing GitHub
    CodeConnections flow already requires manual console authorization after deploy.

## Scope Decisions

1. **New module category**: `templates/v2/modules/account-wide/bedrock-cloudwatch-log-group.yml`
   and `templates/v2/modules/account-wide/bedrock-cloudwatch-role.yml`, alongside the existing
   `apigw-cloudwatch-*.yml` siblings.
2. **New account-wide parameters** (mirroring `EnableApiGwCloudWatchLogs`):
   - `EnableBedrockModelInvocationLogs` (String, `true`/`false`, default `"true"` — this repo's
     current convention per CHANGELOG v0.0.41 is account-wide logging enabled by default).
   - `BedrockLogGroupRetentionInDays` (Number) — retention for the new log group, following
     the existing `LogExpirationInDays` pattern used by the S3 access-log bucket.
3. **No standalone service-role template** — API Gateway logging has no standalone
   `template-service-role-api-gateway-cloudwatch.yml` counterpart either; it only exists
   inside `account-wide-infrastructure.yml`. Bedrock logging will follow the same
   account-wide-only precedent, not introduce a new standalone template.
4. **Outputs**: export the log group name/ARN and role ARN following the existing
   `${OrgPrefix}-ApiGateway-CloudWatch-Role-Arn` export convention, e.g.
   `${OrgPrefix}-Bedrock-CloudWatch-Role-Arn`, `${OrgPrefix}-Bedrock-CloudWatch-LogGroup-Name`.
5. **Manual activation step documentation** (per user's latest instruction):
   - Add a comment block at the top of `account-wide-infrastructure.yml` (near the existing
     header) documenting the required post-deploy `aws bedrock
     put-model-invocation-logging-configuration` CLI call, referencing the role ARN and log
     group name outputs by name.
   - Generate a comprehensive, standalone Markdown document (deliverable of this spec, not
     merely a code comment) written for copy-over into the separate `atlantis-platform-admin`
     documentation repository referenced from `docs/admin-ops/account-management.md`. This
     doc must cover: prerequisites, the exact CLI command with placeholders, how to verify
     the configuration (`get-model-invocation-logging-configuration`), how to disable, and
     cost/retention considerations.
   - This generated doc will be saved under `docs/admin-ops/` in this repo as review output,
     with an explicit task instructing the maintainer to manually copy the relevant content
     into the `atlantis-platform-admin` repo (this repo cannot write to that external repo).

## Versioning

- CHANGELOG: new `v0.0.43 - unreleased` section added (done).
- Spec directory renamed: `0-0-41-enable-account-model-logs` → `0-0-43-enable-account-model-logs` (done).
- `account-wide-infrastructure.yml` is currently `v2.0.1/2026-08-20`, PATCH > 0 → auto-increment
  PATCH to `v2.0.2` as the first implementation task (non-breaking: new optional
  parameters/resources/outputs only).

## Next Steps

Proceed to formal spec-driven workflow:
1. `requirements.md` — EARS-style acceptance criteria covering parameters, conditions,
   modules, outputs, header documentation comment, and the generated admin-ops markdown doc.
2. `design.md` — resource definitions (log group, IAM role, IAM policy statement),
   parameter/condition tables, module contract comments, architecture diagram, error handling
   (e.g., what happens if a user runs the CLI activation command before the stack exists).
3. `tasks.md` — ordered implementation tasks: version bump, module creation, parent template
   wiring, outputs, header comment, admin-ops markdown generation, docs/templates/v2 README
   update (per `documentation-end-user-cfn-templates` steering), unit tests (fast, concrete;
   no new property-based tests per testing guidelines), cfn-lint validation, CHANGELOG entry.

## Resolved Decisions (user-confirmed)

1. **Log group name** includes `OrgPrefix`. Chosen convention:
   `/aws/bedrock/${OrgPrefix}-ModelInvocations` — combines the AWS `/aws/<service>/` log group
   path convention already used by this repo's log group modules
   (`/aws/codebuild/${Prefix}-${ProjectId}-${StageId}-Promote`) with the account-wide
   `OrgPrefix` naming convention and a Pascal-case resource identifier per `AGENTS.md`.
2. **Parameters** (final names):
   - `EnableBedrockInvocationLogs` — default `"true"`, modeled after `EnableS3AccessLogBucket`.
   - `BedrockInvocationLogExpirationInDays` — default `180`, same format as
     `LogExpirationInDays`, but constrained to the enumerated values that
     `AWS::Logs::LogGroup` `RetentionInDays` accepts (CloudWatch Logs does not accept
     arbitrary day counts the way an S3 lifecycle rule does).
   - All provisioning gated behind conditions.
   - New metadata parameter group: `"Bedrock Model Invocation Logs"`.
3. **KMS encryption is in scope and optional** — new `BedrockInvocationLogKmsKeyArn`
   parameter (default `""`, bring-your-own existing symmetric key). The template does not
   create or modify the key or its policy; the required
   `logs.<region>.amazonaws.com` key-policy grant is documented as an operator prerequisite.

## Status

- [x] PLAN.md
- [x] requirements.md — 15 requirements, 11 confirmed design decisions recorded,
      all open questions resolved; awaiting maintainer approval
- [x] design.md — requirements approved 2026-09-22; design written with concrete YAML for both
      modules, 6 recorded deliberate divergences, 12 correctness properties, and error handling
- [x] tasks.md — design approved 2026-09-22; 10 task groups, dependency graph in 8 waves,
      mapped to all 15 requirements; awaiting approval to begin implementation
