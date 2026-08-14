# Cross-Account Serverless CI/CD Promotion
## Requirements Document

**Status:** Draft for Architect/Engineer Review  
**Prepared for:** Kiro IDE Implementation Planning  
**Date:** 2025-07-30  

---

## 1. Overview

This document defines the requirements for extending the existing Atlantis CI/CD framework to support cross-account artifact promotion across a DEV/TEST/PROD account structure. The goal is to enable a serverless project built and validated in the TEST account to be promoted through PROD account stages (beta → prod) using a controlled, auditable, and repeatable process — without redesigning the existing Atlantis pipeline model.

---

## 2. Background & Constraints

### 2.1 Existing Atlantis Model

Atlantis is a branch-based, serverless CI/CD framework built on AWS CodePipeline and CodeBuild. Key characteristics:

- Pipelines are named and deployed using strict naming conventions driven by prefix (often a team identifier such as "finc"), project, and stage identifiers (e.g., `finc-export-payroll-test-pipeline`)
- Deployed application stacks follow the same convention (e.g., `finc-export-payroll-test-application`)
- Pipeline behavior is heavily driven by CodeBuild environment variables (`DEPLOY_ENV`, `STAGE_ID`, `PROJECT_NAME`, `PREFIX`, etc.)
- Each pipeline consists of: **Source → Build (CodeBuild) → Deploy (CFN Changeset) → Post Deploy (optional CodeBuild)**
- `buildspec.yml`, `template.yaml`, and all supporting scripts live alongside the application source code in the repository
- CloudFormation conditions are parameter-driven; parameters are resolved at build time into a `template-configuration.json` file
- Lambda functions are environment-agnostic: they rely entirely on Lambda Environment Variables defined in the CFN template and always run as `NODE_ENV=production`
- Node.js dependencies are managed with `npm ci` against a committed lockfile, ensuring deterministic builds
- Pre-deploy steps may include CDK deployments, SSM parameter writes, S3 static file copies, or SDK/CLI scripts
- Post-deploy steps may include API Gateway spec extraction, OpenAPI documentation site deployment, integration tests, or smoke tests
- Static file assets differ between builds/stages and must always be generated from source

### 2.2 Account Structure

| Account | Purpose | Notes |
|---|---|---|
| **TEST** | Source of truth for code, build, and initial deployment | DEV account is optional; if absent, TEST serves as the origin account |
| **PROD** | Hosts beta and prod stages | Both are PROD environments with production-level alarms, logging, and configuration |

### 2.3 Stage & Environment Mapping

| Branch | Stage ID | Deploy Env | Account | Stack Example |
|---|---|---|---|---|
| `test` | `test` | `TEST` | TEST | `finc-export-payroll-test-application` |
| `beta` | `beta` | `PROD` | PROD | `finc-export-payroll-beta-application` |
| `main` | `prod` | `PROD` | PROD | `finc-export-payroll-prod-application` |

> **Note:** `beta` and `prod` are both PROD environments, enabling a production-like blue/green or QA promotion path between them.

---

## 3. Goals

1. Enable a tested, SHA-pinned commit to be promoted from the TEST account to PROD account stages without manual re-triggering from source control
2. Ensure each stage performs a full build from source using the correct environment variables and stage context — preserving all existing build, pre-deploy, and post-deploy behaviors
3. Maintain a clear, auditable record of what was promoted, by whom, and when
4. Introduce a manual approval gate before promotion from `test` to `beta` and from `beta` to `prod`
5. Reuse a single new Atlantis pipeline template for both `beta` and `prod` stages, differentiated only by configuration
6. Avoid redesigning or refactoring existing buildspecs, scripts, or CloudFormation templates

---

## 4. Core Design Decision: Promote the Commit (S3 Source Archive)

Rather than promoting compiled artifacts or Lambda zip packages, the system promotes a **pinned git commit** by archiving the full repository at the validated SHA and storing it in S3. Downstream pipelines check out this archive rather than pulling from CodeCommit directly.

### Rationale

- Builds are deterministic (`npm ci` on lockfile) — rebuilding from the same SHA produces equivalent outputs
- Static assets, pre-deploy scripts, and post-deploy scripts differ per environment and must always execute in the target account context
- `buildspec.yml`, `template.yaml`, and all scripts are co-located with source — they must travel with the commit
- This approach requires no refactoring of existing build logic and no management of intermediate build artifacts
- Rollback is trivial: resubmit a promotion manifest pointing at a previous SHA

---

## 5. Cross-Account Handoff Mechanism

### 5.1 S3 Promotion Bucket

A bucket in the receiving account with cross-account write permissions from the sending account serves as the handoff point between accounts. This bucket holds two artifacts per promotion event:

**Source Archive**
- A zip of the full repository at the promoted git SHA
- Keyed by prefix and project and SHA to enable reuse across stages
- Example path: `{prefix}-{project}/{sha}/source.zip`

**Promotion Manifest**
- A JSON file written to a known S3 path that triggers the downstream pipeline via S3 event
- Contains all metadata required for the downstream pipeline to execute correctly
- Example path: `{prefix}-{project}/{sha}/promote-to-{target_stage}.json`

### 5.2 Promotion Manifest Schema

```json
{
  "project": "export-payroll",
  "prefix": "finc",
  "git_sha": "a3f9c2e",
  "source_archive_key": "finc-export-payroll/a3f9c2e/source.zip",
  "promoted_from_stage": "test",
  "target_stage": "beta",
  "target_deploy_env": "PROD",
  "promoted_by": "jane.doe@example.com",
  "promoted_at": "2025-01-15T16:00:00Z",
  "source_pipeline_execution_id": "abc-123",
  "post_deploy_passed": true
}
```

### 5.3 Pipeline Trigger

The downstream pipeline is triggered by the arrival of the promotion manifest JSON file in the S3 bucket. The pipeline reads the manifest to determine the source archive location and all environment variable values required for the build.

---

## 6. Pipeline Requirements

### 6.1 Existing Pipeline (TEST Account)

The existing Atlantis pipelines (template-pipeline-build-only, template-pipeline-github, template-pipeline) for the `test` stage requires two additions:

**Manual Approval Stage** — inserted after the Post Deploy stage. A human must approve promotion before any cross-account handoff occurs. On rejection, the pipeline stops and no source archive or promotion manifest is written.

**Promote Stage** — executes only after Manual Approval is granted. Responsibilities:
- Archive the repository at the current git SHA and write `source.zip` to the cross-account S3 bucket
- Write the promotion manifest JSON to the cross-account S3 bucket, triggering the `beta` pipeline

All other stages (Source, Build, Deploy, Post Deploy) remain unchanged.

The Manual Approval and Promote Stages are optional but both are included if "enabled". To enable these stages, the pipeline must accept a set of parameters needed to promote (such as destination bucket, target stage, etc. to be determined before requirements are complete.)

### 6.2 New Atlantis Pipeline Template: `pipeline-promoted-artifact`

A new Atlantis pipeline template is required to support promotion-triggered deployments. This template is used for both `beta` and `prod` stages. The two instances are differentiated entirely by their configuration parameters.

#### 6.2.1 Pipeline Stages

| Stage | Required | Description |
|---|---|---|
| **Source** | Yes | S3 event trigger on promotion manifest arrival. Reads manifest to resolve all downstream parameters. |
| **Build** | Yes | Full CodeBuild execution from source archive. Identical behavior to existing build stage. Runs with target stage environment variables. |
| **Deploy** | Yes | CFN changeset creation and execution. Identical to existing deploy stage. |
| **Post Deploy** | Conditional | CodeBuild execution of post-deploy scripts. Present only if the project defines a post-deploy buildspec. Identical behavior to existing post-deploy stage. |
| **Manual Approval** | Yes | Human approval gate. Present on both `beta` and `prod` pipelines. Blocks promotion to the next stage until approved. |
| **Promote** | Conditional | Writes promotion manifest and source archive reference to next stage's S3 trigger path. Present on `beta` pipeline only. Absent on `prod` pipeline. |

#### 6.2.2 Build Stage Behavior in Promotion Pipeline

The Build stage in the promotion pipeline executes identically to the existing full build, with the following differences:

- Source is the S3 archive rather than a CodeCommit branch
- `StageId` and `DeployEnvironment` are injected from the pipeline configuration (not derived from branch name)
- All pre-deploy scripts (CDK, SSM, S3 copies, SDK/CLI) execute normally in the target account context

---

## 7. Manual Approval Requirements

- A Manual Approval gate is present in **two of the three pipelines**: `test` and `beta`
- In the `test` pipeline, the approval gate appears after Post Deploy and before the Promote stage
- In the `beta` pipeline, the approval gate appears after Post Deploy and before the Promote stage
- In the `prod` pipeline there is no subsequent Promote stage
- Approval must be actionable from the AWS Console (CodePipeline native approval)
- The approval notification should include: project name, prefix, stage, git SHA, pipeline execution ID, and a link to the pipeline execution
- Approval or rejection is recorded as part of the pipeline execution history
- On rejection, the pipeline stops and no promotion manifest is written

---

## 8. IAM & Cross-Account Access Requirements

### 8.1 TEST Account — CodeBuild Execution Role (Promote Stage)

Must be granted:
- `s3:PutObject` on the cross-account promotion S3 bucket
- `s3:GetObject` on the source CodeCommit repository (for archive generation)

### 8.2 PROD Account — CodeBuild Execution Role (Build Stage)

Must be granted:
- `s3:GetObject` on the cross-account promotion S3 bucket (to retrieve `source.zip` and the promotion manifest)

### 8.3 Cross-Account S3 Bucket Policy

The S3 promotion bucket must allow:
- **Write** from the TEST account CodeBuild execution role (for source archive and manifest upload)
- **Read** from the PROD account CodeBuild execution role (for source archive and manifest retrieval)
- **S3 Event Notifications** configured to trigger the PROD account pipeline on manifest file arrival

### 8.4 Existing Account-Level Permissions

All other IAM permissions (CFN deploy, SSM writes, CDK deploy, API GW access, etc.) are unchanged — they are already scoped to the account in which the pipeline executes.

---

## 9. Rollback Requirements

- Any previous promotion manifest SHA can be resubmitted to the S3 trigger path to re-execute a prior deployment
- The source archive for a given SHA must be retained in S3 for a defined retention period (retention policy to be determined by the Cloud Architect)
- Re-promotion of a previous SHA bypasses the test pipeline and enters the promotion pipeline directly, subject to the same Manual Approval gate

---

## 10. Audit & Observability Requirements

- Every promotion event must produce a promotion manifest stored durably in S3
- Pipeline execution history in CodePipeline provides the per-stage audit trail
- The promotion manifest must record: git SHA, source stage, target stage, prefix, promoted by, promoted at, and whether post-deploy passed
- No additional audit infrastructure is required at this time; the combination of S3 manifests and CodePipeline history satisfies the audit requirement

## 11. S3 Bucket

We will modify the current account-wide/s3-artifacts-bucket-policy and account-wide/s3-artifacts-bucket to receive artifacts from a single specified account as an optional parameter. We will retain the current lifecycle policy.

We will also have to determine how to add the S3 event triggers that will trigger the correct pipeline. 

## 12. Approve Release

The new pipeline will also have an optional Approve Release stage. After the S3 event is triggered but before the Build stage, there is an optional approval stage. (This creates a double approval, first approval from the sending pipeline, and then a release by the receiving pipeline)

## 13. Versatile

While cross account promotion is the main use case, internal account promotion is also useful if a single account houses all three environments (DEV, TEST, PROD). The set up would be the same with approvals, promotions, s3 buckets, triggers, release, and pipeline stages, but it wouldn't have to be cross account.

Another thing to consider, even through beta and prod were used as examples, there could be any number of production stages, or even test stages. TEST may hold test and qa stages, and PROD may hold beta, staging, prod stages.

We need to be sure we parameterize the stages, allow configuration, and not hard code stage identifiers in conditionals. The only standard is DEV, TEST, PROD environments which can be used for conditionals. The pipeline will need to know what stage in what environment (DEV/TEST/PROD) it is operating under, and what the next target stage is.

## 14. Modular

All new templates should be created as modules with the parent template composed of modules following the existing structure of this repository.

Any modifications to existing modules used by parent templates must be thourouly tested and not introduce breaking changes. Parameters may be additive with defaults that maintain existing settings. (New features disabled by default).

## 15. Existing Service Roles

The pipeline templates are deployed using the service roles that are deployed via the prefix-based-infrastructure.yml template. Any new resources or actions required to deploy the modified pipeline templates and the new templates must be updated to allow deployment.

---

## 15. Open Questions for Architect Review

1. **S3 bucket topology:** Single shared promotion bucket (cross-account write) vs. per-account buckets (TEST pushes to PROD bucket)? The per-account model is simpler operationally and avoids a shared resource dependency. **Answer** We will use per-account
2. **Source archive retention policy:** How long should `source.zip` archives be retained? This determines rollback window. **Answer** We will modify the current account-wide/s3-artifacts-bucket-policy and account-wide/s3-artifacts-bucket to receive artifacts from a single specified account. We will retain the current lifecycle policy.
3. **Approval notification channel:** CodePipeline native email approval vs. Slack/Teams integration vs. internal portal? **Answer** CodePipeline native email approval
5. **Optional DEV account:** If a DEV account exists, does it participate in this promotion flow or remain a developer sandbox only? **Answer** DEV participates and will use one of the existing template-pipeline-* with the added approve/promote stage.
6. **Pipeline instantiation:** How are `beta` and `prod` promotion pipelines provisioned for a new project — manually, via an Atlantis CLI command, or automatically on first promotion event? **Answer** pipelines are instantiated using Atlantis scripts. The script config.py reads in the template parameters and prompts the user for values. A deploy.py subsequently uses CloudFormation CLI and SAM CLI to deploy the pipeline template. These are out of scope as they utilize well-formed templates with proper meta-data grouping, parameter definitions, and relevant outputs.