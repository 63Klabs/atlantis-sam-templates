# Clarifying Questions: Simplify Parameters for Account Wide

Before drafting `requirements.md`, I reviewed the following and found several decisions
that will materially shape the requirements. Please answer inline (or edit this file).
Once resolved, I'll generate `requirements.md`.

## What I Reviewed

- `templates/v2/account/prefix-based-infrastructure.yml` (v0.0.1) — defines `S3ArtifactsBucket` (currently **required**) and `PrefixUpper`; consumes the management-role modules.
- `templates/v2/account/account-wide-infrastructure.yml` (v0.0.0) — defines `OrgPrefix` (UPPER, 2–20, **required**, no default) and conditionally exports the artifacts bucket name as `${OrgPrefix}-S3-Artifacts-Bucket-Name` (only when `EnableS3ArtifactsBucket = "true"`).
- `templates/v2/modules/management-roles/pipeline-mgmt-role.yml` and `storage-mgmt-role.yml` — these are the **only** two modules that reference `S3ArtifactsBucket`, via the `ArtifactBucketGetObjectForManagedStacks` statement: `arn:aws:s3:::${S3ArtifactsBucket}/${Prefix}-*`.
- The network management-role modules (`network-cloudfront-mgmt-role.yml`, `network-full-mgmt-role.yml`) do **not** reference the artifacts bucket.
- `templates/v2/service-role/template-service-role-pipeline.yml` and `template-service-role-storage.yml` — standalone (deprecation-noticed) templates that **also consume the same two modules**.

---

## Key Findings That Drive the Questions

1. **Only two modules use `S3ArtifactsBucket`** (pipeline-mgmt-role, storage-mgmt-role). The SPEC says "each of the service role modules," but the network roles never reference it. So the change scope is those two modules.

2. **The fallback must live inside the modules.** `AWS::Include` modules read parameters/conditions directly (`${S3ArtifactsBucket}`). The parent cannot re-compute or reassign a parameter value for a module. To fall back to the export, the two modules must use `Fn::If` to choose between `Ref S3ArtifactsBucket` and `Fn::ImportValue`. That means both modules gain a dependency on a new `OrgPrefix` parameter and a new override condition.

3. **Blast radius — the standalone service-role templates.** `template-service-role-pipeline.yml` and `template-service-role-storage.yml` consume these exact modules but currently define **neither** `S3ArtifactsBucket` **nor** `OrgPrefix`, and they do not define an override condition. Editing the shared modules will require those parents to be updated too (or they break). Note: they appear to already reference `${S3ArtifactsBucket}` through the module without declaring it, so they may already be out of sync.

4. **The export is conditional.** `${OrgPrefix}-S3-Artifacts-Bucket-Name` only exists when the account-wide stack was deployed with `EnableS3ArtifactsBucket = "true"`. If neither the `S3ArtifactsBucket` override nor the export is present, deployment fails on an unresolved import.

---

## Questions

### Q1. Scope of module changes
Confirm the change applies to **only** `pipeline-mgmt-role.yml` and `storage-mgmt-role.yml` (the two that reference `S3ArtifactsBucket`), and that the network roles are untouched.

- **Recommended:** Yes — only those two modules.
- Alternative: Also touch network roles (not needed; they don't use the bucket).

**Answer:** Only applies to `pipeline-mgmt-role.yml` and `storage-mgmt-role.yml`

---

### Q2. `OrgPrefix` parameter in `prefix-based-infrastructure.yml` — required or optional?
The SPEC says to add `OrgPrefix` "following the same parameter definition found in account-wide-infrastructure." In account-wide it is **required** (no default). But adding a *required* parameter to `prefix-based-infrastructure.yml` is a **breaking change** for existing deployments.

- **Option A (recommended):** Add `OrgPrefix` with the same pattern/constraints as account-wide, but give it `Default: ""` so it stays optional and backward compatible. It is only consulted when `S3ArtifactsBucket` is not supplied. Keep the AllowedPattern but allow empty (`...|^$`).
- **Option B:** Add `OrgPrefix` exactly as in account-wide (required, no default). Simpler/consistent, but breaks existing stacks and forces every deployer to supply it even when passing `S3ArtifactsBucket` directly.

**Answer:** Option A

---

### Q3. Is `OrgPrefix` the same value as `PrefixUpper`?
`prefix-based-infrastructure.yml` already has `PrefixUpper` (UPPER, 2–8). The export uses the account-wide `OrgPrefix` (UPPER, 2–20). These are conceptually different (org-wide vs. team prefix) and likely differ in value, so I believe a separate `OrgPrefix` parameter is required to build the import name.

- **Recommended:** Add a distinct `OrgPrefix` parameter (do not reuse `PrefixUpper`).
- Alternative: If your convention guarantees `OrgPrefix == PrefixUpper`, we could reuse `PrefixUpper` and skip adding a parameter. Please confirm whether that guarantee holds.

**Answer:** OrgPrefix is distinct from PrefixUpper

---

### Q4. Override condition name
I plan to add a condition to detect whether the operator supplied `S3ArtifactsBucket`.

- **Recommended name:** `HasS3ArtifactsBucketOverride` = `!Not [!Equals [!Ref S3ArtifactsBucket, ""]]`
- The two modules would use `Fn::If [HasS3ArtifactsBucketOverride, <ref bucket>, <import ${OrgPrefix}-S3-Artifacts-Bucket-Name>]`.

Any preferred naming?

**Answer:** HasS3ArtifactsBucketOverride

---

### Q5. Standalone service-role templates (`template-service-role-pipeline.yml`, `template-service-role-storage.yml`)
Because they share the two modules being changed, they must be kept consistent. How do you want to handle them?

- **Option A (recommended):** Update both standalone templates in this spec too — add `S3ArtifactsBucket` (deprecated, optional) + `OrgPrefix` + the override condition so they keep working with the updated modules.
- **Option B:** Leave them out of scope and accept they will break (they are deprecation-noticed anyway).
- **Option C:** Treat them as a separate follow-up spec.

Also: were these two templates already broken (they reference `${S3ArtifactsBucket}` via the module without declaring it)? If so, this spec is a good place to fix them.

**Answer:** Option A

---

### Q6. Behavior when neither override nor export exists
If `S3ArtifactsBucket` is empty **and** the account-wide stack has no `${OrgPrefix}-S3-Artifacts-Bucket-Name` export, the stack fails at deploy time on the unresolved `Fn::ImportValue`.

- **Recommended:** Accept CloudFormation's native "No export named ... found" error as the failure mode, and document the dependency (account-wide must be deployed with `EnableS3ArtifactsBucket = "true"` first). Also note that `Fn::ImportValue` creates a hard cross-stack link that blocks deletion of the account-wide export while referenced.
- Alternative: Any additional guard/validation you'd want (CFN can't conditionally require a parameter, so options are limited).

**Answer:** Use recommendation

---

### Q7. Deprecation marking for `S3ArtifactsBucket`
The SPEC wants the parameter marked deprecated while remaining functional. CloudFormation has no native deprecation flag.

- **Recommended:** Prefix the parameter `Description` with `"DEPRECATED: "`, explain that the value is now derived from the `${OrgPrefix}-S3-Artifacts-Bucket-Name` export and that supplying it is an override for backward compatibility. Mirror the note in the template README and CHANGELOG. Keep it in the "External Resources" metadata group.

**Answer:** Use recommendation

---

### Q8. Versioning
`prefix-based-infrastructure.yml` is at `v0.0.1` (PATCH > 0 → production mode). The changes (new optional `OrgPrefix`, making `S3ArtifactsBucket` optional, module fallback) are additive and backward compatible.

- **Recommended:** Treat as **non-breaking** → PATCH bump to `v0.0.2` on `prefix-based-infrastructure.yml`. If we update the standalone service-role templates (Q5), PATCH-bump each of those as well. Modules are not individually versioned. CHANGELOG unreleased is `v0.0.39`.
- Flag: If you choose Q2 Option B (required `OrgPrefix`), that becomes a **breaking change** and would instead require a new versioned template file per the version-control rules. Please confirm you prefer to avoid that.

**Answer:** Treat as **non-breaking** → PATCH bump to `v0.0.2` on `prefix-based-infrastructure.yml`. We will override the breaking change and patch release the standalones as well.

---

## Summary of My Recommendation (if you just want the default path)

- Add optional `OrgPrefix` (Default `""`, account-wide pattern + empty allowed) to `prefix-based-infrastructure.yml`. [Q2-A, Q3]
- Make `S3ArtifactsBucket` optional (Default `""`, allow empty) and mark it `DEPRECATED:` in its description. [Q7]
- Add condition `HasS3ArtifactsBucketOverride`. [Q4]
- Update the two modules (`pipeline-mgmt-role.yml`, `storage-mgmt-role.yml`) to use `Fn::If` → override value, else `Fn::ImportValue "${OrgPrefix}-S3-Artifacts-Bucket-Name"`; update their contract comment blocks. [Q1]
- Update the two standalone service-role templates to stay consistent with the modules. [Q5-A]
- Non-breaking → PATCH bumps; document the account-wide dependency and native import-failure behavior. [Q6, Q8]
