# Cache-Data Modularization — Questions & Recommendations

This document captures my understanding of the requested work, along with clarifying
questions and recommendations for your approval. Once you respond, I will produce
`requirements.md`.

Spec directory: `.kiro/specs/0-0-39-cache-data-modularization/`
(Version `v0.0.39 (unreleased)` per `CHANGELOG.md`.)

---

## My Understanding of the Goal

1. **Extract** the resources currently defined inline in
   `templates/v2/storage/template-storage-cache-data.yml` into reusable module
   snippets (resource definition only, no logical ID — matching the existing
   `templates/v2/modules/**` pattern used by `account-wide-infrastructure.yml` and
   `prefix-based-infrastructure.yml`).
2. **Modularize** `template-storage-cache-data.yml` so it consumes those same
   modules via `Fn::Transform: AWS::Include` instead of defining resources inline.
3. **Add** the cache-data resources to `prefix-based-infrastructure.yml` by
   consuming the same modules.
4. **Gate** creation of the cache-data resources in `prefix-based-infrastructure.yml`
   behind a `true`/`false` parameter, mirroring the `EnableApiGwCloudWatchLogs` /
   `EnableS3ArtifactsBucket` pattern in `account-wide-infrastructure.yml`.
5. **Output** the cache-data resources (console links + exports) in
   `prefix-based-infrastructure.yml` — conditional on the toggle — matching the
   outputs currently in `template-storage-cache-data.yml`.
6. Place the cache-data parameters/options in their own **"Cache-Data"** metadata
   parameter group in `prefix-based-infrastructure.yml`.

The four resources in scope (from the current cache-data template):
- `CacheDataDynamoDbTable` (`AWS::DynamoDB::Table`)
- `CacheDataS3BucketRegional` (`AWS::S3::Bucket`)
- `CacheDataS3BucketPolicy` (`AWS::S3::BucketPolicy`)
- `ManagedLambdaExecutionRolePolicy` (`AWS::IAM::ManagedPolicy`, conditional)

---

## Key Question — Resource Naming / Scope (most important)

The current cache-data resources are **prefix + project** scoped:

- Table name: `${Prefix}-${ProjectId}-CacheData`
- Bucket name: `${Prefix}-${ProjectId}-${AWS::AccountId}-${AWS::Region}-an`
- Managed policy: `${Prefix}-${ProjectId}-ManagedLambdaExecutionRolePolicy`
- Exports: `${Prefix}-CacheData*` (prefix-only export names)

However, `prefix-based-infrastructure.yml` is **prefix-scoped only** — it has
`Prefix` and `PrefixUpper` but **no `ProjectId`** parameter (it provisions shared,
prefix-wide management roles, not project resources).

Because you want *the same modules* used by both templates, the modules must
reference the same parameters/conditions that both parent templates provide. This
forces a decision on how cache-data resources are named when created from
`prefix-based-infrastructure.yml`.

**Q1. How should cache-data resources be scoped/named in `prefix-based-infrastructure.yml`?**

- **Option A (recommended): Add a `ProjectId` parameter to `prefix-based-infrastructure.yml`.**
  Keeps the modules and resource names identical in both templates
  (`${Prefix}-${ProjectId}-CacheData`, etc.). Lowest-risk, no changes to cache-data
  naming, modules stay simple. The `ProjectId` parameter would live in the new
  "Cache-Data" group (or "Application Resource Naming").
- **Option B: Make cache-data prefix-only when shared (e.g., `${Prefix}-CacheData`).**
  More "prefix-native," but this changes the naming contract and would require the
  module to branch on whether a project is present — and would change the standalone
  cache-data template's names (a **breaking change** to an already-deployed template,
  v0.0.15). Not recommended.

> Recommendation: **Option A** — add `ProjectId` to `prefix-based-infrastructure.yml`
> so module resource names are identical across both parents.

**Answer** Good point. i will backtrack. The current template-storage-cache-data.yml will remain AS IS. We will only use it as a template. They will be maintained separately but the definitions are stable so it won't be a burden. We should create a steering document that affects only the cache data modules and template that requires them to be in sync. We will continue to use Project ID for the stand alone template-storage-cache-data.yml, and replace the use of ProjectId with "cache-data" for the modularized version.

---

## Question — Export Name Collisions

The cache-data outputs export prefix-scoped names such as
`${Prefix}-CacheDataDynamoDbTable`, `${Prefix}-CacheDataS3Bucket`,
`${Prefix}-CacheDataS3BucketArn`, `${Prefix}-CacheDataDynamoDbTableArn`,
`${Prefix}-CacheDataManagedLambdaExecutionRolePolicy`.

If a user deploys **both** the standalone `template-storage-cache-data.yml` **and**
`prefix-based-infrastructure.yml` with cache-data enabled (same Prefix, same
account/region), the exports will **collide** and the second stack will fail.

**Q2. How do you want to handle potential export-name collisions?**

- **Option A (recommended): Keep identical export names and document that cache-data
  should be provisioned by *only one* stack per Prefix (either standalone OR via
  prefix-based-infrastructure, not both).** Simplest; consumers reference the same
  export name regardless of which stack created it.
- **Option B: Use distinct export names in `prefix-based-infrastructure.yml`** (e.g.,
  a suffix). Avoids collisions but means downstream stacks must know which stack
  produced the cache resources.

> Recommendation: **Option A** — identical exports + documentation note that only one
> stack should own the cache-data resources per Prefix.

**Answer** Option A, since that is the purpose of the parameter that is set to true or false for creating the cache-data stack at the prefix-infra level.

---

## Question — Shared Condition for Modules

Module snippets embed a static `Condition:` (e.g., the s3-artifacts module has
`Condition: EnableS3ArtifactsBucket`). To share the *same* module between both
parents, both parents must define the condition the module references.

- In `prefix-based-infrastructure.yml`, the condition is driven by the new toggle
  (e.g., `CreateCacheDataResources: !Equals [!Ref EnableCacheData, "true"]`).
- In `template-storage-cache-data.yml`, cache-data resources are currently
  **always created** (no condition).

**Q3. In the standalone `template-storage-cache-data.yml`, should the shared
condition simply always evaluate to true, or should I also add an `EnableCacheData`
toggle there (defaulting to `true`)?**

> Recommendation: In the standalone template, define the shared condition as
> **always true** (e.g., `!Equals ["true", "true"]`) so behavior is unchanged and no
> new parameter is introduced there. Keep the `CreateManagedLambdaExecutionRolePolicy`
> toggle as-is for the managed policy module.

**Answer** Since I now backtracked about using modules for template-storage-cache-data i don't think this is relevant anymore. 

---

## Question — Toggle Parameter Name

**Q4. What should the enable/disable parameter be named in
`prefix-based-infrastructure.yml`?**

> Recommendation: **`EnableCacheData`** (`AllowedValues: ["true","false"]`,
> `Default: "false"`) to match the existing `EnableApiGwCloudWatchLogs` and
> `EnableS3ArtifactsBucket` naming/casing convention.

**Answer** Yes use recommendation to match existing
---

## Question — Module Location & Names

There is no `storage` subdirectory under `templates/v2/modules/` yet (current
subdirs: `account-wide`, `management-roles`, `pipeline`, `pipeline-policies`).

**Q5. Do you approve creating `templates/v2/modules/storage/` for the cache-data
modules?**

> Recommendation: **Yes.** Proposed module files:
> - `templates/v2/modules/storage/cache-data-dynamodb-table.yml`
> - `templates/v2/modules/storage/cache-data-s3-bucket.yml`
> - `templates/v2/modules/storage/cache-data-s3-bucket-policy.yml`
> - `templates/v2/modules/storage/cache-data-managed-lambda-policy.yml`

**Answer**: I want cache-data to receive it's own modules:
- `templates/v2/modules/cache-data/cache-dynamodb-table.yml`
- `templates/v2/modules/cache-data/cache-s3-bucket.yml`
- `templates/v2/modules/cache-data/cache-s3-bucket-policy.yml`
- `templates/v2/modules/cache-data/cache-managed-lambda-policy.yml`

---

## Question — Parameters Introduced into `prefix-based-infrastructure.yml`

To create cache-data resources, the following parameters (beyond the existing
`Prefix`, `S3BucketNameOrgPrefix`, `RolePath`) are needed. These would form the new
**"Cache-Data"** metadata group:

- `EnableCacheData` (toggle — see Q4)
- `ProjectId` (see Q1, Option A) **no longer needed, see answer to Q1**
- `CacheDataPurgeAgeOfCachedBucketObjInDays` (Number, Default 15, MinValue 3)
- `CreateManagedLambdaExecutionRolePolicy` (`TRUE`/`FALSE`, Default `TRUE`) **Update to CreateManagedCacheDataLambdaExecutionRolePolicy**

**Q6. Do you approve this parameter set and grouping them under a "Cache-Data"
metadata group?** (I'll order the group after existing groups, before "Module Source".)

> Note: `prefix-based-infrastructure.yml` already defines `UseS3BucketNameOrgPrefix`
> and `RolePath`, which the modules need — so those are reused.

**Answer** Note my comments in **bold** otherwise use your recommendation

---

## Question — Versioning

- `template-storage-cache-data.yml` is **v0.0.15** (PATCH > 0 → production mode).
  Refactoring to `AWS::Include` while **preserving logical IDs, resource names, and
  outputs** is non-breaking → I would bump to **v0.0.16**.
  - **Caveat:** modularizing introduces two new parameters (`S3ModuleLocation`,
    `S3ModuleNamespace`). `S3ModuleLocation` has no default in the other templates
    (it's effectively required). Adding a required parameter changes the deploy
    interface for existing standalone deployers.
- `prefix-based-infrastructure.yml` is **v0.0.0** (development mode) → no version
  bump, edits in place.


**Q7. For the standalone cache-data template, is a **PATCH bump to v0.0.16**
acceptable (treating the module refactor as non-breaking), or do you consider the new
required `S3ModuleLocation` parameter a breaking change warranting a new versioned
file?**

> Recommendation: Treat as **non-breaking PATCH → v0.0.16**, consistent with how the
> pipeline templates were modularized in `0-0-39-pipeline-module-extraction` (which
> also added `S3ModuleLocation`/`S3ModuleNamespace` and incremented PATCH). Give
> `S3ModuleNamespace` a default of `"atlantis"` as elsewhere; `S3ModuleLocation`
> stays without a default (matching the other modularized templates).

**Answer** We won't be changing template-storage-cache-data.yml anymore - see answer to Q1

---

## Question — Management Role S3 Module Access

The `0-0-39` work added `S3ModuleBucketReadOnly` permissions to management roles so
CloudFormation's `AWS::Include` transform can read module snippets from S3. The
`prefix-based-infrastructure.yml` and `template-storage-cache-data.yml` are deployed
by the **storage** management role.

**Q8. Should this spec verify/ensure the storage management role
(`storage-mgmt-role.yml`) already grants read access to the module bucket namespace
for the new `storage/` module path, or is that already covered by the existing
namespace-wide grant?**

> Recommendation: The existing grant appears namespace-scoped
> (`.../templates/v2/modules/*`), so the new `storage/` path should already be
> covered. I'll **verify** during design and only add a task if a gap exists.

**Answer** Verify and let me know if there are issues.

---

## Out-of-Scope Confirmation

**Q9. Confirm the following are out of scope:**
- Changing the cache-data resource *configurations* (TTL attrs, encryption,
  lifecycle rules, IAM actions) — I will copy them **verbatim** into modules.
- Modifying `account-wide-infrastructure.yml` (referenced only as the pattern to
  mirror; no cache-data resources added there).

> Recommendation: Keep both out of scope.

**Answer** Yes both are out of scope

---

## Documentation & Changelog (planned final tasks, not questions)

Per repo steering, the spec will include final tasks to:
- Update `docs/templates/v2/storage/template-storage-cache-data-README.md`.
- Update `docs/templates/v2/account/` docs for `prefix-based-infrastructure` (new
  parameters, resources, outputs, Cache-Data group).
- Update `templates/v2/modules/README.md` with a Storage Modules section.
- Add a `CHANGELOG.md` entry under `v0.0.39 (unreleased)`.

---

## Final Resolved Decisions (per your answers)

| # | Topic | Resolution |
|---|-------|------------|
| Q1 | Naming/scope | **`template-storage-cache-data.yml` stays AS-IS** (not modularized; used as the reference source). New modules created for `prefix-based-infrastructure.yml` only. In the modules, the `${ProjectId}` token is replaced with the literal `cache-data`. A **new steering doc** will require the standalone template and the cache-data modules to be kept in sync. |
| Q2 | Export collisions | Option A — identical export names (`${Prefix}-CacheData*`); the `EnableCacheData` toggle ensures only one stack owns the resources per Prefix. |
| Q3 | Standalone condition | N/A — standalone template unchanged. Module conditions are defined only in `prefix-based-infrastructure.yml`. |
| Q4 | Toggle name | `EnableCacheData` (`AllowedValues: ["true","false"]`, `Default: "false"`). |
| Q5 | Module directory | Create **`templates/v2/modules/cache-data/`** with: `cache-dynamodb-table.yml`, `cache-s3-bucket.yml`, `cache-s3-bucket-policy.yml`, `cache-managed-lambda-policy.yml`. |
| Q6 | Params + group | New **"Cache-Data"** group (ordered before "Module Source") with `EnableCacheData`, `CacheDataPurgeAgeOfCachedBucketObjInDays`, and `CreateManagedCacheDataLambdaExecutionRolePolicy` (renamed). No `ProjectId`. Reuse existing `RolePath`, `S3BucketNameOrgPrefix`, `UseS3BucketNameOrgPrefix`. |
| Q7 | Versioning | No change to `template-storage-cache-data.yml`. `prefix-based-infrastructure.yml` is v0.0.0 (dev mode) — edit in place, no bump. |
| Q8 | Mgmt role S3 access | **Verified — no gap.** `storage-mgmt-role.yml` `S3ModuleBucketGetObject` grants `arn:aws:s3:::${S3ModuleLocation}/${S3ModuleNamespace}/*` (namespace-wide), covering the new `cache-data/` path. `S3ModuleBucketListByNamespace` covers listing. No additional task required. |
| Q9 | Out of scope | Confirmed — no resource config changes; no `account-wide-infrastructure.yml` changes. |

### Added scope from your answers
- **New steering document** under `.kiro/steering/` scoped to the cache-data modules
  and `template-storage-cache-data.yml`, requiring their resource definitions to be
  kept in sync (since the standalone template is intentionally NOT modularized).

Proceeding to write `requirements.md`.
