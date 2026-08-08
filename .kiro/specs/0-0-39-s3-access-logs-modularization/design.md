# Design — S3 Access-Logs Modularization

## Overview

This design extracts the two S3 access-log resources into reusable `AWS::Include` module
snippets under `templates/v2/modules/s3-access-logs/`, and wires those modules into
`templates/v2/account/account-wide-infrastructure.yml` behind an `EnableS3AccessLogBucket`
on/off parameter. The standalone `templates/v2/storage/template-storage-s3-access-logs.yml`
is the canonical reference and is **not modified**; a new steering document keeps the two
in sync.

In addition, the account-wide artifacts bucket (`modules/account-wide/s3-artifacts-bucket.yml`)
is updated to use the new access-log bucket as its server access logging destination behind
a precedence rule with the existing `S3LogBucketName` parameter.

The design follows the established module pattern already used by the account-wide,
cache-data, and pipeline modules: a module file is the body of a single resource (no logical
ID, no `Resources:` wrapper), uses long-form intrinsics only, and opens with a contract
comment block naming the parent parameters, conditions, and sibling logical IDs it depends
on.

### Design Goals

1. Reuse the exact resource configuration from the standalone template, changing only what
   is required for the module/parent contract:
   - drop the `${Prefix}` and `${ProjectId}` naming tokens (the account-wide parent has
     neither)
   - shorthand intrinsics (`!Sub`, `!Ref`, `!If`, `!GetAtt`, `!Join`) to long-form
   - add resource-level `Condition:` keys driven by the parent toggle
2. No default access-log footprint — resources exist only when
   `EnableS3AccessLogBucket=true`.
3. Make the shared access-log bucket the default logging destination for the account-wide
   artifacts bucket, while preserving an explicit `S3LogBucketName` override.

### Non-Goals

- Modifying `template-storage-s3-access-logs.yml` (unchanged).
- Changing any access-log resource configuration (encryption, lifecycle, ownership
  controls, policy statements) beyond the documented translations.

---

## Architecture

### Component Map

```
templates/v2/modules/s3-access-logs/           (NEW)
├── s3-access-log-bucket.yml                    -> consumed as AccessLogBucketRegional
└── s3-access-log-bucket-policy.yml             -> consumed as AccessLogBucketPolicy

templates/v2/account/account-wide-infrastructure.yml   (MODIFIED)
├── Parameters:  + EnableS3AccessLogBucket
│                + LogExpirationInDays
│                + AllowLegacyCloudFrontLogs
├── Metadata:    + "S3 Access Log Bucket" parameter group (before "Module Source")
├── Conditions:  + EnableS3AccessLogBucket
│                + EnableLegacyCloudFrontLogs
├── Resources:   + AccessLogBucketRegional (AWS::Include)
│                + AccessLogBucketPolicy    (AWS::Include)
└── Outputs:     + S3AccessLogBucketName / Arn / Console (conditional)

templates/v2/modules/account-wide/s3-artifacts-bucket.yml   (MODIFIED)
└── LoggingConfiguration destination precedence + LogFilePrefix

templates/v2/storage/template-storage-s3-access-logs.yml    (UNCHANGED — reference source)

.kiro/steering/s3-access-logs-module-sync.md    (NEW steering doc)
```

### Module Resolution Path

```
s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/s3-access-logs/<module>.yml
```

`account-wide-infrastructure.yml` already declares `S3ModuleLocation` and
`S3ModuleNamespace` under a `"Module Source"` group, so no new module-source parameters are
needed.

### Condition Flow

```
EnableS3AccessLogBucket (param, default "false")
   └── EnableS3AccessLogBucket condition = param == "true"
           ├── AccessLogBucketRegional   (Condition: EnableS3AccessLogBucket)
           └── AccessLogBucketPolicy      (Condition: EnableS3AccessLogBucket)

AllowLegacyCloudFrontLogs (param, default "false")
   └── EnableLegacyCloudFrontLogs condition = param == "true"
           ├── AccessLogBucketRegional.PublicAccessBlock.BlockPublicAcls / OwnershipControls
           └── AccessLogBucketPolicy AllowCloudFrontLogDelivery statement
```

---

## Detailed Design

### Naming Translation (standalone to module)

| Aspect | Standalone (`template-storage-s3-access-logs.yml`) | Module (`s3-access-logs/*`) |
|--------|----------------------------------------------------|-----------------------------|
| Bucket name (org prefix) | `${S3BucketNameOrgPrefix}-${Prefix}-${ProjectId}-access-logs-${AWS::AccountId}-${AWS::Region}-an` | `${S3BucketNameOrgPrefix}-access-logs-${AWS::AccountId}-${AWS::Region}-an` |
| Bucket name (no org prefix) | `${Prefix}-${ProjectId}-access-logs-${AWS::AccountId}-${AWS::Region}-an` | `access-logs-${AWS::AccountId}-${AWS::Region}-an` |
| Intrinsics | shorthand (`!Sub`, `!Ref`, `!If`, `!GetAtt`, `!Join`) | long-form (`Fn::Sub`, `Ref`, `Fn::If`, `Fn::GetAtt`, `Fn::Join`) |
| Resource `Condition` | none | `EnableS3AccessLogBucket` |
| Outputs | `${Prefix}-${ProjectId}-LoggingBucket*` (in template) | parent-side `${OrgPrefix}-S3-AccessLog-Bucket-*` |

### Module 1 — `s3-access-log-bucket.yml`

Contract: params `S3BucketNameOrgPrefix`, `LogExpirationInDays`, `AllowLegacyCloudFrontLogs`;
conditions `UseS3BucketNameOrgPrefix`, `EnableS3AccessLogBucket`, `EnableLegacyCloudFrontLogs`.
`AWS::S3::Bucket`, `DeletionPolicy: Retain`, `UpdateReplacePolicy: Retain`,
`Condition: EnableS3AccessLogBucket`. Encryption AES256 (bucket keys), versioning Suspended,
public-access block with the legacy toggle on `BlockPublicAcls`, `DeleteOldLogs` lifecycle
rule using `LogExpirationInDays`, and `OwnershipControls` set to `BucketOwnerPreferred` only
when `EnableLegacyCloudFrontLogs`.

### Module 2 — `s3-access-log-bucket-policy.yml`

Contract: conditions `EnableS3AccessLogBucket`, `EnableLegacyCloudFrontLogs`; sibling
`AccessLogBucketRegional`. `AWS::S3::BucketPolicy`, `Condition: EnableS3AccessLogBucket`,
`Bucket: Ref AccessLogBucketRegional`. Statements: `DenyNonSecureTransportAccess`,
`AllowS3LogDelivery` (principal `logging.s3.amazonaws.com`, `aws:SourceAccount` =
`${AWS::AccountId}`), and a conditional `AllowCloudFrontLogDelivery` (principal
`delivery.logs.amazonaws.com`) gated by `EnableLegacyCloudFrontLogs`.

### `account-wide-infrastructure.yml` Changes

**Parameters (new):** `EnableS3AccessLogBucket` (String, true/false, default false),
`LogExpirationInDays` (Number, default 90, 1–365), `AllowLegacyCloudFrontLogs` (String,
true/false, default false).

**Metadata group** `"S3 Access Log Bucket"` inserted after `"S3 Artifacts Bucket"` and
before `"Module Source"`, containing the three parameters.

**Conditions (new):** `EnableS3AccessLogBucket`, `EnableLegacyCloudFrontLogs`.

**Resources (new):** `AccessLogBucketRegional` and `AccessLogBucketPolicy`, each via
`Fn::Transform: AWS::Include`.

**Outputs (new, conditional):** `S3AccessLogBucketName` (export
`${OrgPrefix}-S3-AccessLog-Bucket-Name`), `S3AccessLogBucketArn` (export
`${OrgPrefix}-S3-AccessLog-Bucket-Arn`), `S3AccessLogBucketConsole`.

### Artifacts-Bucket Logging Precedence

`modules/account-wide/s3-artifacts-bucket.yml` `LoggingConfiguration` becomes a nested
`Fn::If`:

```yaml
LoggingConfiguration:
  Fn::If:
    - HasLoggingBucket
    - DestinationBucketName:
        Ref: S3LogBucketName
      LogFilePrefix: "cf-artifacts/"
    - Fn::If:
        - EnableS3AccessLogBucket
        - DestinationBucketName:
            Ref: AccessLogBucketRegional
          LogFilePrefix: "cf-artifacts/"
        - Ref: "AWS::NoValue"
```

Precedence: an explicit `S3LogBucketName` wins; otherwise the account-wide access-log
bucket is used when enabled; otherwise no logging. `LogFilePrefix` is `cf-artifacts/` for
either destination.

### Ordering / Dependencies

No explicit `DependsOn` on the access-log resources. When the artifacts bucket logs to the
account-wide access-log bucket (i.e. `EnableS3AccessLogBucket=true` and `S3LogBucketName`
empty), the `Ref: AccessLogBucketRegional` inside the taken `Fn::If` branch creates an
implicit dependency, so the log bucket is created first. Because that `Ref` only exists in
that branch, when the feature is off there is no reference to the uncreated resources —
avoiding the fragility of a `DependsOn` pointing at a resource excluded by a false
condition. Log delivery is a runtime activity, and the bucket policy is created within the
same stack operation, so policy-before-bucket ordering is not required for stack success.

### Steering Document — `s3-access-logs-module-sync.md`

Inclusion mode `fileMatch` scoped to the s3-access-logs modules and standalone template.
Documents the sync requirement, the intentional differences (dropped Prefix/ProjectId,
long-form intrinsics, embedded conditions, OrgPrefix exports), the required cross-update
action, and a standalone-logical-ID to module-file mapping.

---

## Components and Interfaces

| Component | File | Resource Type | Interface it consumes from parent |
|-----------|------|---------------|-----------------------------------|
| `AccessLogBucketRegional` | `modules/s3-access-logs/s3-access-log-bucket.yml` | `AWS::S3::Bucket` | Params: `S3BucketNameOrgPrefix`, `LogExpirationInDays`, `AllowLegacyCloudFrontLogs`. Conditions: `UseS3BucketNameOrgPrefix`, `EnableS3AccessLogBucket`, `EnableLegacyCloudFrontLogs` |
| `AccessLogBucketPolicy` | `modules/s3-access-logs/s3-access-log-bucket-policy.yml` | `AWS::S3::BucketPolicy` | Conditions: `EnableS3AccessLogBucket`, `EnableLegacyCloudFrontLogs`. Sibling: `AccessLogBucketRegional` |
| Artifacts bucket (modified) | `modules/account-wide/s3-artifacts-bucket.yml` | `AWS::S3::Bucket` | Conditions: `HasLoggingBucket`, `EnableS3AccessLogBucket`. Sibling: `AccessLogBucketRegional` |
| Parent integration | `account/account-wide-infrastructure.yml` | (host template) | Declares params/conditions above; references each module via `Fn::Transform: AWS::Include` |

---

## Correctness Properties

1. **No footprint when disabled.** With `EnableS3AccessLogBucket="false"`, neither
   access-log resource and none of the access-log outputs/exports are created.
2. **Naming fidelity.** Module resource configuration matches the standalone template
   except for the documented translations (dropped Prefix/ProjectId, shorthand → long-form,
   added `Condition:` keys).
3. **Reference source untouched.** `template-storage-s3-access-logs.yml` is unchanged.
4. **Sibling references resolve.** `AccessLogBucketRegional` is present in the parent under
   that exact name so the policy module's `Ref` resolves.
5. **Backward-compatible logging.** With the feature off, the artifacts bucket logging
   behavior equals the prior `HasLoggingBucket`-only rule (plus the `LogFilePrefix`).
6. **Precedence.** An explicit `S3LogBucketName` always wins over the account-wide bucket.
7. **Conditional-safe ordering.** No `DependsOn` to a conditionally-absent resource; the
   only cross-resource reference (`Ref: AccessLogBucketRegional`) lives in a branch taken
   only when the bucket exists.

---

## Error Handling

- **Missing module object in S3.** Absent module at the resolved `AWS::Include` location
  fails the transform at change-set creation. Mitigation: modules published to the same
  namespace path already granted by the management-role S3 read statement.
- **Undefined parent parameter/condition/sibling.** A module referencing an undeclared name
  fails validation before resources are created; guarded by contract comments and the
  interfaces table.
- **Shorthand intrinsic in a module.** Silently breaks under `AWS::Include`; guarded by the
  long-form-only rule and review.
- **Toggle typos.** `AllowedValues` reject invalid parameter values with the provided
  `ConstraintDescription`.
- **Deploy-time failures roll back.** Both access-log resources share one condition, so a
  failed create rolls back cleanly without partial resources.

---

## Testing Strategy

Following the repository testing guidelines (favor fast unit tests, minimize property-based
tests):

1. Run the existing cfn-lint suite over the modified `account-wide-infrastructure.yml`.
2. Static review of each module against the module-standards checklist (no logical ID,
   long-form intrinsics, contract comment, exactly one correct `Condition`, sibling IDs
   present in parent).
3. Confirm `template-storage-s3-access-logs.yml` is unchanged.
4. Verify the disabled path: with `EnableS3AccessLogBucket="false"`, no access-log
   resources, outputs, or exports are emitted, and artifacts logging is unchanged.
5. Verify the reversed precedence: a non-empty `S3LogBucketName` wins over the access-log
   bucket.

No property-based tests are added — the template set is small and controlled.

---

## Design Decisions and Rationale

1. **Standalone template unchanged; modules maintained separately.** Keeps the reference
   implementation stable; the sync steering doc mitigates drift.
2. **Drop `${Prefix}`/`${ProjectId}`.** The account-wide parent is not prefix/project
   scoped; dropping the tokens yields one shared account-wide access-log bucket.
3. **`S3LogBucketName` precedence over the access-log bucket.** Per maintainer direction —
   an explicitly supplied destination should always win; the shared bucket is the default
   fallback.
4. **`OrgPrefix` export names.** The parent has no Prefix/ProjectId; exports follow the
   sibling artifacts-bucket `${OrgPrefix}-` convention.
5. **No `DependsOn` to conditional resource.** Avoids relying on ambiguous CloudFormation
   behavior on the default path; implicit `Ref`-based ordering is conditional-safe.

---

## Requirements Traceability

| Requirement | Addressed by |
|-------------|--------------|
| R1 bucket module | Module 1 design |
| R2 bucket policy module | Module 2 design |
| R3 parameters & metadata | Parameters + Metadata group design |
| R4 conditions & resources | Conditions + Resources design |
| R5 artifacts logging precedence | Artifacts-Bucket Logging Precedence design |
| R6 outputs | Outputs design |
| R7 steering doc | Steering document design |
| R8 docs & changelog | Handled in tasks (docs + CHANGELOG) |
| R9 validation | Testing strategy |
