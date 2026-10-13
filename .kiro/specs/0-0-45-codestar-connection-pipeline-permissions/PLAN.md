# PLAN: CodeStar/CodeConnections Pipeline Management Permissions

**Spec:** `0-0-45-codestar-connection-pipeline-permissions`
**Status:** Planning only — options and recommendations for iteration. No template changes yet.
**Target version:** v0.0.45 (unreleased)

---

## 1. The Issue (Detected)

Deploying `template-pipeline-github.yml` fails with:

```
User: arn:aws:sts::123456789012:assumed-role/XME-CloudFormation-Service-Role-Pipeline-Management/AWSCloudFormation
is not authorized to perform: codestar-connections:PassConnection
on resource: arn:aws:codeconnections:us-east-2:123456789012:connection/76e6e0e6-8ca1-4197-a4a1-522cc74c5e0a
because no identity-based policy allows the codestar-connections:PassConnection action
(Service: CodePipeline, Status Code: 400 ...)
```

### What is actually happening

There are **two different roles** in play, and they are easy to confuse:

| Role | Defined in | Trusted by | When used | Connection perms today |
|------|-----------|------------|-----------|------------------------|
| **Pipeline Management (deployer) role** `${PrefixUpper}-CloudFormation-Service-Role-Pipeline-Management` | `modules/management-roles/pipeline-mgmt-role.yml` | `cloudformation.amazonaws.com`, `codebuild.amazonaws.com` | At **deploy time**, assumed by CloudFormation to CREATE the pipeline stack | **NONE** |
| **CodePipeline runtime role** `${Prefix}-Worker-${ProjectId}-${StageId}-CodePipelineServiceRole` | inline in `template-pipeline-github.yml` | `codepipeline.amazonaws.com` | At **run time**, when the pipeline executes the Source action | `UseConnection` only (both `codeconnections:` and `codestar-connections:` namespaces) |

When CloudFormation (as the **deployer** role) creates the `AWS::CodePipeline::Pipeline` whose Source action embeds a `ConnectionArn`, CodePipeline validates that the **caller** (the deployer role) holds **`codestar-connections:PassConnection`** on that connection ARN. This is the classic "pass" semantic: you must be authorized to hand a connection to the pipeline service, exactly like `iam:PassRole`.

The deployer role (`pipeline-mgmt-role.yml`) has broad prefix-scoped grants (`codepipeline:*`, `codebuild:*`, `cloudformation:*`, `iam:PassRole` on Worker roles, S3, logs, events, sns, codestar-notifications) but **zero** `codestar-connections` / `codeconnections` statements. That missing grant is the root cause.

> **Note on service namespaces:** AWS renamed the service from "CodeStar Connections" (`codestar-connections`) to "CodeConnections" (`codeconnections`). IAM still treats `codestar-connections:*` as the canonical action namespace in most regions, and the error message uses `codestar-connections:PassConnection` even though the resource ARN is `arn:aws:codeconnections:...`. For maximum compatibility we should grant **both** namespaces (the repo already does this for `UseConnection` in the runtime role).

### Verified facts (from the templates)

- `template-pipeline-github.yml` takes the connection ARN as a **parameter** `GitHubConnectionArn` (AllowedPattern `^arn:aws:codeconnections:\S+:\d{12}:connection\/\S+$`). It is **not** imported via `Fn::ImportValue` — the operator copies it from the account-wide stack output.
- The account-wide stack (`account-wide-infrastructure.yml`) creates the connection via `modules/account-wide/codeconnections-github.yml` (`AWS::CodeConnections::Connection`, `ConnectionName: ${OrgPrefix}-${GitHubOrg}-github-connection`, `DeletionPolicy: Retain`) and **exports** the ARN as `${OrgPrefix}-GitHub-Connection-Arn`.
- The deployer role module (`pipeline-mgmt-role.yml`) already receives `OrgPrefix` as a parent parameter (used today to import the artifacts bucket name). So the module **can** reach account-wide exports without a new parameter.
- `prefix-based-infrastructure.yml` and `template-service-role-pipeline.yml` both assemble the deployer role via `AWS::Include` and both already pass `OrgPrefix`. Neither currently references the connection in any way.
- The GitHub pipeline is the only consumer. `template-pipeline-s3-source.yml` explicitly documents that it needs **no** connection permissions, and `template-pipeline.yml` (CodeCommit) and `-build-only` do not use connections.

### Why `${Prefix}-*` wildcard scoping does NOT work here

Every other grant in the deployer role is scoped to `arn:...:${Prefix}-*`. Connection ARNs do **not** follow the `Prefix-ProjectId-StageId` convention — they are `arn:aws:codeconnections:<region>:<account>:connection/<random-uuid>`. The random UUID means there is no name-based pattern to match, and the connection lives at the **account/org level**, shared across all prefixes. This is the core tension with the least-privilege convention and drives the options below.

---

## 2. How Permissions Are Deployed and Interconnected

```
account-wide-infrastructure.yml
  └── (AWS::Include) modules/account-wide/codeconnections-github.yml
        → AWS::CodeConnections::Connection  "${OrgPrefix}-${GitHubOrg}-github-connection"
        → Export: ${OrgPrefix}-GitHub-Connection-Arn      ← connection ARN lives here

prefix-based-infrastructure.yml   (admin, run once per prefix)
  └── (AWS::Include) modules/management-roles/pipeline-mgmt-role.yml
        → IAM Role "${PrefixUpper}-CloudFormation-Service-Role-Pipeline-Management"  ← DEPLOYER role (needs PassConnection)
  (template-service-role-pipeline.yml is the older/alternate assembler of the same role)

template-pipeline-github.yml      (developer, deployed BY the deployer role above)
  ├── Parameter GitHubConnectionArn  (operator pastes the exported ARN)
  ├── inline CodePipelineServiceRole  ← RUNTIME role (has UseConnection)
  └── AWS::CodePipeline::Pipeline Source action → ConnectionArn: !Ref GitHubConnectionArn
```

Key interconnection insight: the connection is **account-wide and shared**, but the deployer role is **per-prefix**. Any prefix that deploys a GitHub pipeline must be able to `PassConnection` the shared connection. The fix therefore belongs in the **deployer role module** (`pipeline-mgmt-role.yml`), consumed by both prefix-based assemblers.

---

## 3. The Fix — Where It Goes

Add a `codestar-connections` / `codeconnections` statement granting (at minimum) **`PassConnection`** — and, for robustness, `GetConnection` / `UseConnection` / `GetConnectionToken` / `ListTagsForResource` — to the deployer role in `modules/management-roles/pipeline-mgmt-role.yml`.

The only real decision is **how to scope the `Resource`** (and optionally add conditions) to stay as close to least privilege as possible given that connection ARNs are UUID-based and account-wide.

---

## 4. Options for Scoping (ranked)

### Option A — Import the specific connection ARN from the account-wide export *(recommended)*

Scope the statement's `Resource` to the exact connection ARN by importing the account-wide export the module already has the `OrgPrefix` for:

```yaml
- Sid: PassGitHubConnectionForPipelines
  Effect: Allow
  Action:
    - codestar-connections:PassConnection
    - codestar-connections:GetConnection
    - codestar-connections:UseConnection
    - codeconnections:PassConnection
    - codeconnections:GetConnection
    - codeconnections:UseConnection
  Resource:
    - Fn::ImportValue:
        Fn::Sub: "${OrgPrefix}-GitHub-Connection-Arn"
```

Optionally, further constrain `PassConnection` with the documented condition key that limits *which service* the connection may be passed to:

```yaml
  Condition:
    StringEquals:
      codestar-connections:PassedToService: codepipeline.amazonaws.com
```

**Pros**
- Tightest possible scope: exactly one connection ARN, exactly the services needed.
- Reuses the existing `OrgPrefix` parameter and the existing export — no new parameters, no new wiring for the common path.
- Fully additive; nothing existing changes behavior.

**Cons / risks**
- Creates a **hard cross-stack dependency**: the prefix-based stack would fail to deploy if the account-wide stack has **not** created the connection (i.e., `GitHubOrg` was left empty, so the export `${OrgPrefix}-GitHub-Connection-Arn` does not exist). `Fn::ImportValue` of a missing export is a deploy-time error.
- `OrgPrefix` is currently **optional** (default `""`) in both assemblers — an empty `OrgPrefix` makes the import nonsensical.
- Once imported, the account-wide connection output **cannot be deleted** while the prefix stack references it (export lock). Probably acceptable since the connection is `Retain` and long-lived, but worth noting.

**Mitigation for the hard dependency:** gate the whole statement behind a condition (e.g., a new `HasGitHubConnection` or reuse an `OrgPrefix`-present condition) so it is only emitted when the operator opts in. See Option C, which combines A + a toggle.

---

### Option B — Scope to all connections in the account/region

```yaml
Resource:
  - Fn::Sub: "arn:aws:codeconnections:${AWS::Region}:${AWS::AccountId}:connection/*"
  - Fn::Sub: "arn:aws:codestar-connections:${AWS::Region}:${AWS::AccountId}:connection/*"
```

**Pros**
- No cross-stack dependency, no new parameter, no condition needed. Works whether or not the account-wide connection exists yet. Simplest and most robust against ordering.
- Still account/region-scoped — not `Resource: "*"`.

**Cons**
- Broader than necessary: the deployer role could pass **any** connection in the account/region, not just the org's GitHub connection. Weakens least privilege.
- Partially mitigated by adding `codestar-connections:PassedToService: codepipeline.amazonaws.com` and relying on the fact that `PassConnection` only matters at pipeline-create time.

---

### Option C — Option A gated behind an explicit opt-in toggle *(recommended if we want zero ordering surprises)*

Add a new optional parameter to the two prefix-based assemblers, e.g. `GitHubConnectionArn` (default `""`) **or** a boolean `EnableGitHubConnectionAccess`, and a `HasGitHubConnection` condition. Emit the `PassConnection` statement only when set.

- If using an explicit **`GitHubConnectionArn` parameter**, the admin pastes the ARN at prefix-provisioning time → tightest scope, **no** cross-stack `ImportValue` dependency, no reliance on export existence/ordering.
- If using a **boolean toggle + `ImportValue`**, you keep the single-source-of-truth export but make the dependency opt-in.

**Pros**
- Fully backward compatible (new optional param, default off → renders identically to today).
- Tight scope, admin-controlled, no surprise ordering failures.

**Cons**
- Requires touching `prefix-based-infrastructure.yml` and `template-service-role-pipeline.yml` (new param + condition + pass-through to the module) and the module contract comment.
- Slightly more operator steps (set one param when a prefix will host GitHub pipelines).

---

### Option D — Add the grant to the runtime role in the pipeline template instead

Rejected. The error is thrown against the **deployer** role at stack-create time, not the runtime role. Adding `PassConnection` to the inline `CodePipelineServiceRole` would not resolve the deploy-time `AccessDenied`. (We may still consider whether the runtime role needs `PassConnection` — generally it does **not**; `UseConnection` is correct for execution.)

---

## 5. Locked Design (decided)

**Option A (tight scope, `A-import` sub-option) + Option C opt-in gate + `PassedToService` guard.**

Decisions from section 8 are locked. The final design:

### 5.1 New parameter (on `prefix-based-infrastructure.yml` only)

```yaml
  EnableGitHubConnectionAccess:
    Type: String
    Description: "Set to 'true' to grant this prefix's Pipeline Management service role permission to pass and use the account-wide GitHub CodeConnections connection (required to deploy template-pipeline-github.yml). Requires OrgPrefix to be set and the account-wide GitHub connection (GitHubOrg) to have been created, because the connection ARN is imported from the account-wide export '<OrgPrefix>-GitHub-Connection-Arn'. Leave 'false' for prefixes that do not deploy GitHub-sourced pipelines."
    Default: "false"
    AllowedValues: ["true", "false"]
    ConstraintDescription: "Must be 'true' or 'false'."
```

- **Name:** `EnableGitHubConnectionAccess` (string `"true"`/`"false"`), matching the repo's existing `Enable*` convention.
- Group it under the existing **"Pipeline Management"** / IAM metadata group (whichever the pipeline-mgmt params already live under) in `prefix-based-infrastructure.yml`.

### 5.2 New condition (in `prefix-based-infrastructure.yml`)

```yaml
  HasGitHubConnection: !Equals [!Ref EnableGitHubConnectionAccess, "true"]
```

- **Gate on the toggle only** — deliberately **does NOT** also test `OrgPrefix`. This is the **"fail loudly"** decision: if an admin enables access without a valid `OrgPrefix` / without the account-wide connection existing, the `Fn::ImportValue "${OrgPrefix}-GitHub-Connection-Arn"` resolves to a missing export and the stack fails at deploy time, surfacing the misconfiguration immediately rather than silently granting nothing.

### 5.3 Module statement (in `modules/management-roles/pipeline-mgmt-role.yml`)

Emitted only when `HasGitHubConnection` is true (wrapped via `Fn::If` → `AWS::NoValue` when false). Scoped to the single imported connection ARN, both service namespaces, read + pass + use actions, guarded by `PassedToService`:

```yaml
      - Fn::If:
        - HasGitHubConnection
        - Sid: PassGitHubConnectionForPipelines
          Effect: Allow
          Action:
            - codestar-connections:PassConnection
            - codestar-connections:UseConnection
            - codestar-connections:GetConnection
            - codestar-connections:GetConnectionToken
            - codestar-connections:ListTagsForResource
            - codeconnections:PassConnection
            - codeconnections:UseConnection
            - codeconnections:GetConnection
            - codeconnections:GetConnectionToken
            - codeconnections:ListTagsForResource
          Resource:
            - Fn::ImportValue:
                Fn::Sub: "${OrgPrefix}-GitHub-Connection-Arn"
          Condition:
            StringEquals:
              codestar-connections:PassedToService: codepipeline.amazonaws.com
        - Ref: "AWS::NoValue"
```

> **Note:** `AWS::NoValue` as a statement-list element is removed by CloudFormation, so when the toggle is `false` the policy renders exactly as it does today (fully backward compatible). The module already receives `OrgPrefix` as a parent parameter, so no new module parameter is needed — only the new `HasGitHubConnection` **condition** must be added to the module contract.

### 5.4 Scope summary of locked answers

| Question | Decision |
|----------|----------|
| 1 Scope | Option A/C, `A-import` (specific connection ARN via import) |
| 2 Opt-in | Gated per prefix via `EnableGitHubConnectionAccess` |
| 3 ARN source | `Fn::ImportValue "${OrgPrefix}-GitHub-Connection-Arn"` |
| 4 Multiple connections | No — one connection per prefix |
| 5 `PassedToService` | Yes — `codepipeline.amazonaws.com` |
| 6 Assembler | `prefix-based-infrastructure.yml` + module only; deprecated `template-service-role-pipeline.yml` left as-is |
| 7 Read actions | Include `GetConnection`, `GetConnectionToken`, `ListTagsForResource` |
| Param name/type | `EnableGitHubConnectionAccess`, string `"true"`/`"false"` |
| Empty `OrgPrefix` + toggle true | **Fail loudly** (gate on toggle only; import of missing export errors at deploy) |

---

## 6. Tagging / Naming Convention Notes

- Connection ARNs are UUID-based and account-wide, so the standard `${Prefix}-*` ARN wildcard **cannot** apply here (documented above). This is an inherent exception to the naming-convention-based scoping; call it out in the module comment.
- The connection resource itself is named per convention-ish: `${OrgPrefix}-${GitHubOrg}-github-connection` and tagged `GitHubOrg=<org>`. We cannot IAM-scope on connection name (only ARN), and ABAC on connections is limited; `aws:ResourceTag` conditions on `codestar-connections` resources are **not** broadly supported for `PassConnection`. The `codestar-connections:PassedToService` condition key is the supported, meaningful constraint and should be used.

---

## 7. Backward Compatibility / Breaking-Change Assessment

- All options are **additive** (new IAM statement, optionally a new optional parameter + condition). No parameter renamed/removed, no output/export changed, no resource replaced.
- Per the version-control steering: the affected templates are in **development mode (PATCH = 0 / beta)**, so changes are applied in place without new versioned files. Still a **non-breaking** change regardless.
- Versioning actions when we implement:
  - `modules/management-roles/pipeline-mgmt-role.yml` — module (no independent version header); note change in CHANGELOG.
  - If Option A-param / C: date-bump headers on `prefix-based-infrastructure.yml` and `template-service-role-pipeline.yml` (both v0.0.x dev-mode; no PATCH increment).
  - CHANGELOG entry under **v0.0.45 (unreleased)**.
  - Update docs: `pipeline-mgmt-role` is covered under the account/prefix READMEs and `template-pipeline-github-README.md` (connection permissions section).

---

## 8. Clarifications — RESOLVED

*All answered; see §5 for the consolidated locked design. Two follow-up details also locked: parameter name `EnableGitHubConnectionAccess` (string "true"/"false"), and empty-`OrgPrefix`-with-toggle-true behavior = **fail loudly** (gate on toggle only).*


1. **Scope preference:** Do you want the tightest scope (specific connection ARN — Options A/C) or the simplest/most robust (account-region connection wildcard — Option B)? This is the main decision. **Answer:** I want Options A/C with `A-import` sub option.
2. **Opt-in vs always-on:** Should the `PassConnection` grant always be present in the deployer role, or gated behind an opt-in (new parameter/toggle) so prefixes that never host GitHub pipelines get nothing extra? **Answer:** Gated so that each prefix can enable or prevent use of the connection.
3. **ARN source:** If we go tight-scope, prefer **`Fn::ImportValue`** (single source of truth, but creates a cross-stack export lock and requires the account-wide connection to exist first) or a **new `GitHubConnectionArn` parameter** on the prefix templates (no coupling, admin pastes the ARN)? **Answer:** Fn::ImportValue
4. **Multiple connections:** Could a single prefix ever need to pass **more than one** connection (e.g., multiple GitHub orgs / a GitLab connection later)? If yes, a list parameter or the account-region wildcard (Option B) is more future-proof than a single imported ARN. **Answer:** no, a prefix only has one connection
5. **`PassedToService` condition:** OK to add `codestar-connections:PassedToService = codepipeline.amazonaws.com` as an extra guard? (Recommended; low risk, tightens intent.) **Answer:** Yes
6. **Which assembler is canonical?** Both `prefix-based-infrastructure.yml` and `template-service-role-pipeline.yml` build this role. The CHANGELOG marks the `service-role` category as deprecated in favor of `prefix-based-infrastructure.yml`. Should we update **both**, or only `prefix-based-infrastructure.yml` (and the module), leaving the deprecated template as-is? **Answer:** prefix-based-infrastructure.yml, leave deprecated as is.
7. **GetConnection/ListTagsForResource:** Include read actions (`GetConnection`, `ListTagsForResource`, `GetConnectionToken`) alongside `PassConnection`, or keep strictly to `PassConnection` + `UseConnection` to minimize the grant? **Answer:** Include read

---

## 9. Implementation Outline (locked)

1. **Module** `modules/management-roles/pipeline-mgmt-role.yml`
   - Add the `Fn::If: [HasGitHubConnection, <PassGitHubConnectionForPipelines statement>, Ref AWS::NoValue]` entry to the policy `Statement` list (both namespaces, imported-ARN scope, read + pass + use actions, `PassedToService` guard) — exactly as in §5.3.
   - Update the module contract comment block: add `HasGitHubConnection` to the required parent **conditions**; note that `OrgPrefix` must resolve a valid `${OrgPrefix}-GitHub-Connection-Arn` export when the condition is true; document the connection-ARN scoping exception to the `${Prefix}-*` convention.
2. **Assembler** `prefix-based-infrastructure.yml` (only — deprecated `template-service-role-pipeline.yml` left as-is per Q6)
   - Add the `EnableGitHubConnectionAccess` parameter (§5.1) and list it in the appropriate `AWS::CloudFormation::Interface` group.
   - Add the `HasGitHubConnection` condition (§5.2) — gate on the toggle only (fail-loudly).
   - Date-bump the header comment (dev-mode v0.0.x, no PATCH increment per version-control steering).
   - Confirm the existing `cfn-lint` `ignore_checks` already cover the new condition consumed by `AWS::Include` (W8001); add if missing.
3. **Docs**
   - `docs/templates/v2/account/prefix-based-infrastructure-README.md`: document `EnableGitHubConnectionAccess`, its dependency on `OrgPrefix` + the account-wide connection, and the fail-loudly behavior.
   - `docs/templates/v2/account/account-wide-infrastructure-README.md`: cross-reference that the exported `${OrgPrefix}-GitHub-Connection-Arn` is consumed by the prefix role when the toggle is on.
   - `docs/templates/v2/pipeline/template-pipeline-github-README.md`: clarify deployer-role vs runtime-role connection permissions and the prerequisite that the prefix was provisioned with `EnableGitHubConnectionAccess="true"`.
4. **CHANGELOG.md** — entry under `v0.0.45 (unreleased)` (Fixed: deployer role missing `PassConnection`; Added: `EnableGitHubConnectionAccess`).
5. **Validation** — run cfn-lint via the repo's pytest harness on `prefix-based-infrastructure.yml` (and lint the module indirectly); confirm the `false` default renders an unchanged policy.

---

### Next step

Design is locked. We can either:
- proceed straight to implementation of the five items above, or
- formalize the spec first (`requirements.md` → `design.md` → `tasks.md`) per the workspace spec workflow.

Awaiting your go / preference on which path.
