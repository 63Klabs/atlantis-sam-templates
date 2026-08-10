# Design Document

## Overview

This design makes the shared S3 artifacts bucket name optional for `prefix-based-infrastructure.yml` and the two standalone service-role templates. When the operator does not supply `S3ArtifactsBucket`, the two management-role modules (`pipeline-mgmt-role.yml`, `storage-mgmt-role.yml`) resolve the bucket name at deploy time from the account-wide export `${OrgPrefix}-S3-Artifacts-Bucket-Name` via `Fn::ImportValue`. Supplying `S3ArtifactsBucket` remains a supported (but deprecated) override.

The mechanism is a single `Fn::If` on a new `HasS3ArtifactsBucketOverride` condition inside the one IAM statement (`ArtifactBucketGetObjectForManagedStacks`) that references the bucket. All three consuming parent templates gain a new optional `OrgPrefix` parameter, keep an now-optional/deprecated `S3ArtifactsBucket` parameter, and define the `HasS3ArtifactsBucketOverride` condition.

The change is additive and backward compatible: no parameters removed or renamed, no required parameters added, no exports changed. Existing stacks that pass `S3ArtifactsBucket` behave identically.

## Approach

### Why the fallback lives in the modules, not the parent

`AWS::Include` splices a module body into the parent at deploy time. The module references parameters and conditions directly (`${S3ArtifactsBucket}`, `${Prefix}`, `HasS3ArtifactsBucketOverride`). CloudFormation cannot pass a parent-computed value into an `AWS::Include` module — the module reads the parent's parameters and conditions as-is. Therefore the branch selection (override vs. import) must be expressed inside the module using long-form intrinsics.

### Why `Fn::If` around `Fn::ImportValue` is safe

CloudFormation evaluates only the selected branch of an `Fn::If`. When `HasS3ArtifactsBucketOverride` is true, the `Fn::ImportValue` in the false branch is not resolved, so no cross-stack dependency is created and a missing export does not cause failure (satisfies Requirement 7.4). When the condition is false, the `Fn::ImportValue` branch is taken and CloudFormation requires the export to exist, failing natively otherwise (satisfies Requirement 7.1).

### Why `OrgPrefix` is optional here (but required in account-wide)

`account-wide-infrastructure.yml` requires `OrgPrefix`. Adding a required parameter to already-deployed consuming stacks would be a breaking change. Instead `OrgPrefix` is added with `Default: ""` and an AllowedPattern that permits empty. It is only meaningful on the import path; if it is empty and the import path is taken, the import name resolves to `-S3-Artifacts-Bucket-Name`, which fails natively — an acceptable and documented failure mode.

## Architecture

```
account-wide-infrastructure.yml  (deployed with EnableS3ArtifactsBucket=true)
        │
        │ exports  ${OrgPrefix}-S3-Artifacts-Bucket-Name
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Consuming parent templates                                   │
│   • prefix-based-infrastructure.yml                           │
│   • template-service-role-pipeline.yml                        │
│   • template-service-role-storage.yml                         │
│                                                               │
│  Parameters:  OrgPrefix (opt), S3ArtifactsBucket (opt/deprec) │
│  Condition:   HasS3ArtifactsBucketOverride                    │
│        │ AWS::Include                                          │
│        ▼                                                       │
│  pipeline-mgmt-role.yml / storage-mgmt-role.yml               │
│    ArtifactBucketGetObjectForManagedStacks.Resource:          │
│      Fn::If [HasS3ArtifactsBucketOverride,                    │
│               ${S3ArtifactsBucket}/${Prefix}-*,               │
│               ImportValue(${OrgPrefix}-...)/${Prefix}-*]      │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

This change touches three kinds of components: the account-wide producer (unchanged), the consuming parent templates, and the shared `AWS::Include` modules. Their interfaces (inputs consumed, outputs produced, and the contract between parent and module) are described below.

### Account-Wide Infrastructure (producer, unchanged)

- **File:** `templates/v2/account/account-wide-infrastructure.yml`
- **Interface:** When deployed with `EnableS3ArtifactsBucket=true`, exports the artifacts bucket name under the name `${OrgPrefix}-S3-Artifacts-Bucket-Name`.
- **Consumed by:** the two management-role modules via `Fn::ImportValue` on the import path.
- **Not modified** by this design; it is the upstream dependency the fallback resolves against.

### Consuming Parent Templates

- **Files:** `prefix-based-infrastructure.yml`, `template-service-role-pipeline.yml`, `template-service-role-storage.yml`
- **Inputs (parameters):**
  - `OrgPrefix` (String, optional, `Default: ""`) — resolves the account-wide export on the import path.
  - `S3ArtifactsBucket` (String, optional/deprecated, `Default: ""`) — direct override; when non-empty, bypasses the import.
- **Conditions exposed to modules:** `HasS3ArtifactsBucketOverride = Not(Equals(Ref S3ArtifactsBucket, ""))`.
- **Module contract (interface to `AWS::Include`):** the parent must define, at minimum, `S3ArtifactsBucket`, `OrgPrefix`, `Prefix`, and the `HasS3ArtifactsBucketOverride` condition, since the spliced module body references these names directly.
- **Outputs:** unchanged. No exports added, removed, or renamed.

### Management-Role Modules (consumers)

- **Files:** `templates/v2/modules/management-roles/pipeline-mgmt-role.yml`, `storage-mgmt-role.yml`
- **Interface (inputs read from parent):** `S3ArtifactsBucket`, `OrgPrefix`, `Prefix`, and condition `HasS3ArtifactsBucketOverride`.
- **Behavior:** the single IAM statement `ArtifactBucketGetObjectForManagedStacks` selects its `Resource` ARN via `Fn::If` on `HasS3ArtifactsBucketOverride` — override branch uses `${S3ArtifactsBucket}`, import branch uses `Fn::ImportValue` of `${OrgPrefix}-S3-Artifacts-Bucket-Name`. Long-form intrinsics only (no `!`-tag shorthand), because parent-level shorthand is not valid inside a spliced module body.
- **Constraint:** modules are not individually versioned; the interface contract is documented in each module's header comment block.

## Components and Changes

| Component | File | Change |
|-----------|------|--------|
| Prefix-Based Template | `templates/v2/account/prefix-based-infrastructure.yml` | Add `OrgPrefix` param; make `S3ArtifactsBucket` optional + deprecated; add `HasS3ArtifactsBucketOverride`; metadata; version → v0.0.2 |
| Pipeline Mgmt Role Module | `templates/v2/modules/management-roles/pipeline-mgmt-role.yml` | `Fn::If` fallback on `ArtifactBucketGetObjectForManagedStacks`; update contract comment |
| Storage Mgmt Role Module | `templates/v2/modules/management-roles/storage-mgmt-role.yml` | Same as above |
| Standalone Pipeline Template | `templates/v2/service-role/template-service-role-pipeline.yml` | Add `OrgPrefix` + `S3ArtifactsBucket` + `HasS3ArtifactsBucketOverride`; metadata; version → v0.0.19 |
| Standalone Storage Template | `templates/v2/service-role/template-service-role-storage.yml` | Same as above; version → v0.0.4 |
| Docs | `docs/templates/v2/account/…`, `docs/templates/v2/service-role/…` | Document new/changed params and behavior |
| Changelog | `CHANGELOG.md` | Add entries under `v0.0.39 (unreleased)` |

## Detailed Design

### 1. New parameter: `OrgPrefix` (all three consuming templates)

Placed in the "Application Resource Naming" metadata group, adjacent to `PrefixUpper`.

```yaml
  OrgPrefix:
    Type: String
    Description: "Organization-level prefix (UPPER CASE) used to resolve the account-wide S3 artifacts bucket export '<OrgPrefix>-S3-Artifacts-Bucket-Name' from account-wide-infrastructure. This is DISTINCT from PrefixUpper (the team/namespace prefix). Only required when S3ArtifactsBucket is left empty so the bucket name is imported from the account-wide stack. Leave empty if you supply S3ArtifactsBucket directly."
    Default: ""
    AllowedPattern: "^[A-Z][A-Z0-9-]{0,18}[A-Z0-9]$|^$"
    MaxLength: 20
    ConstraintDescription: "May be empty, or 2 to 20 characters. UPPER case alphanumeric and dashes. Must start with a letter and end with a letter or number."
```

Note: `MinLength` is intentionally omitted — a `MinLength: 2` would reject the empty default. The pattern's `|^$` alternative permits empty.

### 2. Modified parameter: `S3ArtifactsBucket` (all three consuming templates)

Remains in the "External Resources" metadata group. For the two standalone templates this parameter is **added** (they currently lack it while the module references it); for the prefix-based template it is **modified** to become optional.

```yaml
  S3ArtifactsBucket:
    Type: String
    Description: "DEPRECATED: Name of the existing S3 artifacts bucket used by managed stacks. This value is now derived automatically from the account-wide export '<OrgPrefix>-S3-Artifacts-Bucket-Name'. Supplying it here overrides the export and is retained only for backward compatibility. Encouraged usage: leave empty and set OrgPrefix so the name is imported from account-wide-infrastructure. Service roles are granted s3:GetObject and s3:GetObjectVersion on keys prefixed with <Prefix>-* within this bucket."
    Default: ""
    AllowedPattern: "^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$|^$"
    MaxLength: 63
    ConstraintDescription: "Must be empty or a valid S3 bucket name between 3 and 63 characters containing only lowercase letters, numbers, and hyphens."
```

Note: `MinLength: 3` is removed so an empty value is permitted; the `|^$` alternative permits empty.

### 3. New condition: `HasS3ArtifactsBucketOverride` (all three consuming templates)

```yaml
Conditions:
  # ... existing conditions ...
  HasS3ArtifactsBucketOverride: !Not [!Equals [!Ref S3ArtifactsBucket, ""]]
```

(Parent templates use YAML shorthand; only the modules must use long-form.)

### 4. Module change: `ArtifactBucketGetObjectForManagedStacks` (both modules)

Both modules currently contain:

```yaml
      - Sid: ArtifactBucketGetObjectForManagedStacks
        Effect: Allow
        Action:
          - s3:GetObject
          - s3:GetObjectVersion
        Resource:
          Fn::Sub: "arn:aws:s3:::${S3ArtifactsBucket}/${Prefix}-*"
```

Replace the `Resource` with an `Fn::If` (long-form only). Actions and Effect are unchanged:

```yaml
      - Sid: ArtifactBucketGetObjectForManagedStacks
        Effect: Allow
        Action:
          - s3:GetObject
          - s3:GetObjectVersion
        Resource:
          Fn::If:
            - HasS3ArtifactsBucketOverride
            - Fn::Sub: "arn:aws:s3:::${S3ArtifactsBucket}/${Prefix}-*"
            - Fn::Sub:
                - "arn:aws:s3:::${ArtifactsBucketName}/${Prefix}-*"
                - ArtifactsBucketName:
                    Fn::ImportValue:
                      Fn::Sub: "${OrgPrefix}-S3-Artifacts-Bucket-Name"
```

Behavior:
- Override present → `arn:aws:s3:::<S3ArtifactsBucket>/<Prefix>-*` (identical to today).
- Override absent → resolves the account-wide export, producing `arn:aws:s3:::<imported-bucket>/<Prefix>-*`.

### 5. Module contract comment updates (both modules)

The header comment block currently lists required parent parameters and conditions. Add `OrgPrefix` to parameters and `HasS3ArtifactsBucketOverride` to conditions. Example for `pipeline-mgmt-role.yml`:

```yaml
# Parent template must define parameters:
#   Prefix, PrefixUpper, S3BucketNameOrgPrefix, ServiceRolePath, RolePath,
#   PermissionsBoundaryArn, GroupNames, RoleNames, UserNames,
#   S3ModuleLocation, S3ModuleNamespace, S3ArtifactsBucket, OrgPrefix
# Parent template must define conditions:
#   UseS3BucketNameOrgPrefix, HasPermissionsBoundaryArn,
#   HasGroupNames, HasRoleNames, HasUserNames, HasS3ArtifactsBucketOverride
```

`S3ArtifactsBucket` already appears in the existing contract comment; `OrgPrefix` and `HasS3ArtifactsBucketOverride` are the additions.

### 6. Metadata grouping (all three consuming templates)

- `OrgPrefix` → "Application Resource Naming" group, after `PrefixUpper`.
- `S3ArtifactsBucket` → "External Resources" group (already present in prefix-based; added to the two standalone templates, which currently have `PermissionsBoundaryArn` alone in that group).

### 7. Version and header updates

Only the `# Version: vX.Y.Z/YYYY-MM-DD` line changes (date = current date, 2026-08-10):

- `prefix-based-infrastructure.yml`: v0.0.1 → **v0.0.2**
- `template-service-role-pipeline.yml`: v0.0.18 → **v0.0.19**
- `template-service-role-storage.yml`: v0.0.3 → **v0.0.4**

Modules are not individually versioned.

## Data Models

No data models change. The only structural change is the `Resource` field of one IAM statement, which moves from a scalar `Fn::Sub` mapping to an `Fn::If` mapping selecting between two `Fn::Sub` forms.

## Error Handling

| Scenario | Behavior |
|----------|----------|
| `S3ArtifactsBucket` non-empty | Override path; no import; no cross-stack dependency (Req 7.4). |
| `S3ArtifactsBucket` empty, export exists | Import path; role scoped to imported bucket; hard cross-stack link created (Req 7.3). |
| `S3ArtifactsBucket` empty, export missing | Native CloudFormation error: "No export named `<OrgPrefix>-S3-Artifacts-Bucket-Name` found" (Req 7.1). No custom guard added. |
| `S3ArtifactsBucket` empty, `OrgPrefix` empty | Import name resolves to `-S3-Artifacts-Bucket-Name`; native "No export named" failure. Documented. |
| Invalid `S3ArtifactsBucket`/`OrgPrefix` value | Rejected at parameter validation by AllowedPattern before deployment. |

Documentation will state that the account-wide stack must be deployed first with `EnableS3ArtifactsBucket = "true"` and a matching `OrgPrefix`, and that `Fn::ImportValue` prevents deletion/modification of the export while referenced.

## Correctness Properties

These invariants must hold for the change to be considered correct. They are the properties the Testing Strategy verifies.

1. **Backward compatibility.** For any stack that supplies a non-empty `S3ArtifactsBucket`, the resolved `Resource` ARN is byte-for-byte identical to the pre-change output (`arn:aws:s3:::${S3ArtifactsBucket}/${Prefix}-*`). No parameter is removed or renamed, no required parameter is added, and no export is changed.

2. **Branch exclusivity.** Exactly one branch of the `Fn::If` is evaluated per deployment. When `HasS3ArtifactsBucketOverride` is true, the `Fn::ImportValue` branch is never resolved, so no cross-stack dependency on the account-wide export is created (Req 7.4).

3. **Import correctness.** When `S3ArtifactsBucket` is empty, the `Resource` resolves to `arn:aws:s3:::<imported-bucket>/${Prefix}-*` where `<imported-bucket>` is the value exported as `${OrgPrefix}-S3-Artifacts-Bucket-Name`, establishing a hard cross-stack link (Req 7.1, 7.3).

4. **Least privilege preserved.** In both branches the statement keeps `Effect: Allow`, actions exactly `[s3:GetObject, s3:GetObjectVersion]`, and a key prefix of `${Prefix}-*`. The fallback never widens actions or resource scope.

5. **Fail-fast on missing dependency.** If the import path is taken and the export does not exist (including the degenerate case of an empty `OrgPrefix` resolving to `-S3-Artifacts-Bucket-Name`), CloudFormation fails natively with a "No export named" error. No custom guard masks this (Req 7.1).

6. **Empty-default validity.** Both new/modified parameters accept their empty `Default: ""` value: the AllowedPattern includes the `|^$` alternative and `MinLength` is absent, so an empty value passes parameter validation.

7. **Module intrinsic form.** Within the modules, the artifacts statement uses only long-form intrinsics (`Fn::If`, `Fn::Sub`, `Fn::ImportValue`) and contains no `!`-tag shorthand, so the body remains valid when spliced via `AWS::Include` (Req 4.5/5.5).

8. **Non-interference.** All IAM statements other than `ArtifactBucketGetObjectForManagedStacks` in both modules are unchanged (Req 4.7/5.7).

## Testing Strategy

Per the repository testing guidelines, the focus is fast, concrete unit tests; no new property-based tests are needed for this change.

### Unit tests — modules (new test file, e.g. `tests/test_mgmt_role_artifacts_bucket_fallback_unit.py`)

Load both modules with the existing `load_template` util. Because parent templates use long-form in modules, `Fn::If`/`Fn::Sub`/`Fn::ImportValue` parse as plain mapping keys.

For each module (`pipeline-mgmt-role.yml`, `storage-mgmt-role.yml`):
- `ArtifactBucketGetObjectForManagedStacks` exists with `Effect: Allow` and actions exactly `[s3:GetObject, s3:GetObjectVersion]` (Req 4.1/5.1).
- Its `Resource` is an `Fn::If` whose first element is `HasS3ArtifactsBucketOverride` (Req 4.2/5.2).
- True branch equals `Fn::Sub: "arn:aws:s3:::${S3ArtifactsBucket}/${Prefix}-*"` (Req 4.3/5.3).
- False branch is an `Fn::Sub` list form whose variable map contains `ArtifactsBucketName` → `Fn::ImportValue` → `Fn::Sub: "${OrgPrefix}-S3-Artifacts-Bucket-Name"`, and whose template string contains `${ArtifactsBucketName}/${Prefix}-*` (Req 4.4/5.4).
- No `!`-tag shorthand keys appear in the statement (long-form only) (Req 4.5/5.5).
- Header comment contains `OrgPrefix` and `HasS3ArtifactsBucketOverride` (Req 4.6/5.6) — read the file text and assert substrings.
- Regression: a representative unrelated statement (e.g., `S3ModuleBucketGetObject`) is unchanged (Req 4.7/5.7).

### Unit tests — consuming templates (new test file, e.g. `tests/test_consuming_templates_artifacts_params_unit.py`)

For each of the three consuming templates:
- `OrgPrefix` parameter: `Default == ""`, `AllowedPattern == "^[A-Z][A-Z0-9-]{0,18}[A-Z0-9]$|^$"`, `MaxLength == 20`, no `MinLength` key (Req 1.1–1.3).
- `S3ArtifactsBucket` parameter: `Default == ""`, `AllowedPattern == "^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$|^$"`, `MaxLength == 63`, no `MinLength` key, `Description` starts with `DEPRECATED:` (Req 2.1–2.3).
- `HasS3ArtifactsBucketOverride` condition exists and equals `Not(Equals(Ref S3ArtifactsBucket, ""))` (Req 3.1).
- Metadata: `OrgPrefix` listed in "Application Resource Naming"; `S3ArtifactsBucket` listed in "External Resources" (Req 1.5, 6.4/6.8).
- Header version line matches the expected bumped version (Req 8.1–8.3).

### Existing tests

Existing module tests (`test_mgmt_role_allow_transform_operations_unit.py`, `test_iam_tagrole_permissions_boundary_fix_unit.py`, `test_storage_mgmt_role_s3_pattern_fix_unit.py`) assert on other statements and should remain green. Run the full suite to confirm no regressions (Req 10.4). If any of them assert on the exact scalar shape of the artifacts statement, update those assertions to the `Fn::If` structure.

### Linting

Run the repo's `cfn-lint` flow over the three modified consuming templates. Existing ignore checks (E6101, W2001, W8001) should remain sufficient; add no new suppressions unless a specific finding requires it (Req 10.1–10.2).

## Requirements Coverage

| Requirement | Addressed by |
|-------------|--------------|
| 1 (OrgPrefix param) | Detailed Design §1, §6 |
| 2 (S3ArtifactsBucket optional/deprecated) | §2, §6 |
| 3 (HasS3ArtifactsBucketOverride) | §3 |
| 4 (pipeline module fallback) | §4, §5 |
| 5 (storage module fallback) | §4, §5 |
| 6 (standalone templates) | §1–§3, §6, §7 |
| 7 (deploy behavior/dependency) | Approach, Error Handling |
| 8 (versioning) | §7 |
| 9 (docs/changelog) | Components table |
| 10 (validation) | Testing Strategy |
