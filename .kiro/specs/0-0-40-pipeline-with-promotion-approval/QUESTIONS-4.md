# Cross-Account Serverless CI/CD Promotion
## Pre-Requirements Round 4: One Contradiction to Resolve

**Status:** Draft for Developer/Architect Review
**Purpose:** Resolve a single contradiction in your `QUESTIONS-3.md` answers (audit-CLI doc location) so I can write `requirements.md`
**Companion Documents:** [PRELIMINARY.md](./PRELIMINARY.md), [QUESTIONS.md](./QUESTIONS.md), [QUESTIONS-2.md](./QUESTIONS-2.md), [QUESTIONS-3.md](./QUESTIONS-3.md)
**Date:** 2026-08-13

---

## 0. How to Use This Document

This is the last round — essentially **one** open item plus a courtesy confirmation of how I'll encode the audit CLI. Add an **Answer:** line under each `U#`. Reply **"proceed"** (or answer U1) and I'll generate `requirements.md`.

---

## 1. The Contradiction

Your two answers for the audit-CLI doc location point at different directories:

- **T3c answer:** *"…it should be in the `docs/end-user` directory as it is ran by the consumer of these templates."*
- **T3d answer:** *"approval-audit CLI doc should actually live in `docs/maintainer/` as it is performed by the maintainer of this repo."*
- **(Original R5a said `docs/admin-ops`.)*

So across three answers you've named all three doc directories. I need one.

### U1 — Which directory owns the approval-audit CLI doc?

I read the existing `docs/` READMEs to see who each audience is:

| Directory | Audience (per its README) | Do they audit *deployed* pipelines across accounts? |
|---|---|---|
| `docs/maintainer/` | Platform engineers who **maintain the templates in this repo** (63klabs or a self-hosting org's fork). They do **not** have access to consumers' deployed pipelines. | **No** — they maintain templates, not deployments. |
| `docs/end-user/` | Developers/ops who run `config.py`/`deploy.py` to deploy **one** pipeline. "The end user does not interact with the S3 bucket directly." | Partly — they deploy pipelines but aren't described as fleet auditors. |
| `docs/admin-ops/` | **Admins/Operations who set up the organization's use** of the platform and the CI/CD pipelines. | **Yes** — this is the governance/oversight audience. |

An audit of *"which deployed pipelines across our accounts have an approval gate disabled"* is a **fleet-governance** task run against live AWS accounts. The repo **maintainer** can't run it (no access to consumers' accounts), and it's broader than a single **end-user** deployment. It fits the **`docs/admin-ops`** audience best — which also happens to be where you first suggested it (R5a).

- **Recommendation:** Put the approval-audit CLI doc in **`docs/admin-ops/`**.
- **U1a:** Confirm `docs/admin-ops/`, or pick `docs/end-user/` or `docs/maintainer/` and I'll use that. *(The two-account **integration test** stays in `docs/maintainer/` per your Q24 answer — that one genuinely is a maintainer task.)*
  **Answer:** Confirm `docs/admin-ops/`

---

## 2. Courtesy Confirmation — How I'll Encode the Audit CLI (from T3a/T3b/T3c)

Just so the requirement matches your intent (no answer needed unless something's off):

- **Three copy-paste, one-line commands** (AWS CLI + pipes/`jq`), per T3a:
  1. Pipelines that **promote but lack the Approve-to-Promote gate** (`PromoteApprovalRequired=false` in effect).
  2. Promoted-artifact pipelines that **lack the Approve-Release gate** (`ReleaseApprovalRequired=false` in effect).
  3. **Either** of the above.
- **Detection method A** (per T3b): inspect **deployed pipeline structure** via `aws codepipeline list-pipelines` + `get-pipeline`, keying on the presence/absence of the `Manual` approval action. To make this reliably detectable, I'll give the approval actions **distinct, recognizable names** in the templates (e.g. stage/action names `ApproveToPromote` and `ApproveRelease`) and, where useful, an Atlantis marker so the commands only match Atlantis pipelines.
  - Note: command #1 only flags pipelines that **actually have a Promote stage** (a pipeline that simply doesn't promote is **not** flagged).

- **U2a:** Any objection to naming the approval actions `ApproveToPromote` / `ApproveRelease` so the structure-inspection commands can detect them? (Otherwise no answer needed.)
  **Answer:** no objection

---

## 3. What's Blocking `requirements.md`

- **U1a** — the audit-CLI doc directory. That's the only true blocker.

Everything else (Rounds 1–3) is locked. Answer U1a (or reply **"proceed"** and I'll place the audit-CLI doc in `docs/admin-ops/` per my recommendation) and I'll generate `requirements.md`.
