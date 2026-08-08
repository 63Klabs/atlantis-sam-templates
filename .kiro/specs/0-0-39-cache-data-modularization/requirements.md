# Requirements Document

Cache-Data Modularization

## Introduction

This feature makes the Cache-Data storage resources (a DynamoDB table, an S3 bucket,
an S3 bucket policy, and a managed Lambda execution-role policy) available for
deployment from the account-level `prefix-based-infrastructure.yml` template, gated by
an on/off parameter that mirrors the existing `EnableApiGwCloudWatchLogs` /
`EnableS3ArtifactsBucket` pattern used in `account-wide-infrastructure.yml`.

The resource definitions are extracted into reusable `AWS::Include` module snippets
stored under `templates/v2/modules/cache-data/`. The existing standalone
`templates/v2/storage/template-storage-cache-data.yml` template is **intentionally
left unchanged** and continues to serve as the canonical reference for the resource
definitions. Because the two are maintained separately, a steering document will
require the standalone template and the cache-data modules to be kept in sync.

### Background and Decisions

- `template-storage-cache-data.yml` (v0.0.15) is **not modified** by this spec. It
  remains the prefix + project scoped reference implementation.
- The new modules are consumed **only** by `prefix-based-infrastructure.yml` (v0.0.0,
  development mode — edited in place, no version bump).
- In the modules, the `${ProjectId}` naming token from the standalone template is
  replaced with the literal string `cache-data`. Since `prefix-based-infrastructure.yml`
  provisions prefix-wide shared infrastructure, this yields a single shared cache-data
  resource set per Prefix.
- Export names remain identical to the standalone template (`${Prefix}-CacheData*`).
  The `EnableCacheData` toggle ensures only one stack owns these resources per Prefix,
  avoiding export-name collisions.
- Out of scope: any change to the cache-data resource *configurations* (copied
  verbatim) and any change to `account-wide-infrastructure.yml`.

### Resources in Scope

| Standalone logical ID | Type | Module file |
|-----------------------|------|-------------|
| `CacheDataDynamoDbTable` | `AWS::DynamoDB::Table` | `cache-data/cache-dynamodb-table.yml` |
| `CacheDataS3BucketRegional` | `AWS::S3::Bucket` | `cache-data/cache-s3-bucket.yml` |
| `CacheDataS3BucketPolicy` | `AWS::S3::BucketPolicy` | `cache-data/cache-s3-bucket-policy.yml` |
| `ManagedLambdaExecutionRolePolicy` | `AWS::IAM::ManagedPolicy` | `cache-data/cache-managed-lambda-policy.yml` |

---

## Glossary

| Term | Definition |
|------|------------|
| **Module** | A reusable `AWS::Include` snippet under `templates/v2/modules/cache-data/` containing a single resource body (no logical ID, no `Resources:` wrapper) consumed via `Fn::Transform: AWS::Include`. |
| **Standalone template** | `templates/v2/storage/template-storage-cache-data.yml` (v0.0.15), the canonical prefix + project scoped reference implementation, left unchanged by this spec. |
| **Cache-Data resources** | The DynamoDB table, S3 bucket, S3 bucket policy, and managed Lambda execution-role policy that make up the cache-data resource set. |
| **Prefix** | Team or org identifier (lowercase) used as the leading token in resource names. |
| **ProjectId** | Short application identifier from the standalone template; replaced with the literal `cache-data` in the modules. |
| **Contract comment block** | A leading comment in each module declaring the parent parameters, conditions, and sibling logical IDs the module requires. |
| **Long-form intrinsics** | Full-form CloudFormation intrinsic functions (`Fn::Sub`, `Ref`, `Fn::If`, `Fn::GetAtt`) rather than YAML shorthand tags. |
| **EnableCacheData** | On/off parameter that gates creation of the cache-data resources, mirroring the existing `EnableApiGwCloudWatchLogs` / `EnableS3ArtifactsBucket` pattern. |
| **Export-name collision** | Duplicate CloudFormation export names across stacks; avoided by ensuring only one stack owns the cache-data resources per Prefix. |

---

## Requirements

## Requirement 1 — Cache-Data DynamoDB Table Module

**User Story:** As a platform administrator, I want the Cache-Data DynamoDB table
defined as a reusable module, so that it can be included by
`prefix-based-infrastructure.yml`.

#### Acceptance Criteria

1. WHEN the module `templates/v2/modules/cache-data/cache-dynamodb-table.yml` is
   authored THEN it SHALL contain a single resource body (no logical ID, no
   `Resources:` wrapper) per the module standards.
2. THE module SHALL use long-form intrinsic functions only (`Fn::Sub`, `Ref`,
   `Fn::If`, `Fn::GetAtt`, etc.) — no YAML shorthand tags.
3. THE module SHALL open with a contract comment block declaring the parent
   parameters (`Prefix`, `CacheDataPurgeAgeOfCachedBucketObjInDays`) and conditions
   (`CreateCacheData`) it requires.
4. THE table `TableName` SHALL be `${Prefix}-cache-data-CacheData` (the standalone
   `${ProjectId}` token replaced with the literal `cache-data`).
5. THE table's attribute definitions, key schema, TTL specification (`purge_ts`,
   enabled), and `PAY_PER_REQUEST` billing mode SHALL match the standalone template
   verbatim.
6. THE module SHALL preserve `UpdateReplacePolicy: Retain` and `DeletionPolicy: Delete`.
7. THE module SHALL carry `Condition: CreateCacheData`.

---

## Requirement 2 — Cache-Data S3 Bucket Module

**User Story:** As a platform administrator, I want the Cache-Data S3 bucket defined
as a reusable module, so that it can be included by `prefix-based-infrastructure.yml`.

#### Acceptance Criteria

1. THE module `templates/v2/modules/cache-data/cache-s3-bucket.yml` SHALL be a single
   resource body using long-form intrinsics and a contract comment block declaring
   required parameters (`Prefix`, `S3BucketNameOrgPrefix`,
   `CacheDataPurgeAgeOfCachedBucketObjInDays`) and conditions
   (`UseS3BucketNameOrgPrefix`, `CreateCacheData`).
2. THE bucket name SHALL be
   `${S3BucketNameOrgPrefix}-${Prefix}-cache-data-${AWS::AccountId}-${AWS::Region}-an`
   when `UseS3BucketNameOrgPrefix` is true, otherwise
   `${Prefix}-cache-data-${AWS::AccountId}-${AWS::Region}-an`.
3. THE bucket's `PublicAccessBlockConfiguration`, `BucketEncryption` (AES256),
   `BucketNamespace: "account-regional"`, and `LifecycleConfiguration` (including the
   `cache` prefix rule using `CacheDataPurgeAgeOfCachedBucketObjInDays`) SHALL match
   the standalone template verbatim.
4. THE module SHALL carry `Condition: CreateCacheData`.

---

## Requirement 3 — Cache-Data S3 Bucket Policy Module

**User Story:** As a platform administrator, I want the Cache-Data S3 bucket policy
defined as a reusable module, so that access controls are applied consistently.

#### Acceptance Criteria

1. THE module `templates/v2/modules/cache-data/cache-s3-bucket-policy.yml` SHALL be a
   single resource body using long-form intrinsics and a contract comment block that
   declares the required parameter (`Prefix`), condition (`CreateCacheData`), and the
   sibling logical ID it references (`CacheDataS3BucketRegional`).
2. THE policy SHALL reference the bucket via `Ref: CacheDataS3BucketRegional`.
3. THE policy statements (`DenyNonSecureTransportAccess` and
   `AllowLambdaReadWriteDelete` with the `aws:SourceArn` condition scoped to
   `arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:project/${Prefix}-*`) SHALL match
   the standalone template verbatim.
4. THE module SHALL carry `Condition: CreateCacheData`.

---

## Requirement 4 — Cache-Data Managed Lambda Execution Policy Module

**User Story:** As a platform administrator, I want the managed Lambda execution-role
policy defined as a reusable module, so that Lambda functions can be granted scoped
access to the Cache-Data resources.

#### Acceptance Criteria

1. THE module `templates/v2/modules/cache-data/cache-managed-lambda-policy.yml` SHALL
   be a single resource body using long-form intrinsics and a contract comment block
   declaring required parameters (`Prefix`, `RolePath`), condition
   (`CreateCacheDataManagedPolicy`), and the sibling logical IDs it references
   (`CacheDataS3BucketRegional`, `CacheDataDynamoDbTable`).
2. THE managed policy `ManagedPolicyName` SHALL be
   `${Prefix}-cache-data-ManagedLambdaExecutionRolePolicy`.
3. THE policy statements (`LambdaAccessToS3BucketCacheData`,
   `LambdaAccessToS3ListBucket`, `LambdaAccessToDynamoDBTableCacheData`) and the
   `Path` (`RolePath`) SHALL match the standalone template verbatim.
4. THE module SHALL carry `Condition: CreateCacheDataManagedPolicy`, where that
   condition is the logical AND of `EnableCacheData` being true and
   `CreateManagedCacheDataLambdaExecutionRolePolicy` being `TRUE`.

---

## Requirement 5 — `prefix-based-infrastructure.yml` Parameters and Metadata

**User Story:** As a platform administrator, I want a Cache-Data parameter group in
`prefix-based-infrastructure.yml`, so that I can enable and configure the Cache-Data
resources from a single deployment.

#### Acceptance Criteria

1. THE template SHALL add an `EnableCacheData` parameter (Type String, `AllowedValues:
   ["true","false"]`, `Default: "false"`, with a `ConstraintDescription`).
2. THE template SHALL add a `CacheDataPurgeAgeOfCachedBucketObjInDays` parameter
   (Type Number, `Default: 15`, `MinValue: 3`) matching the standalone template's
   definition.
3. THE template SHALL add a `CreateManagedCacheDataLambdaExecutionRolePolicy`
   parameter (Type String, `AllowedValues: ["TRUE","FALSE"]`, `Default: "TRUE"`) —
   the renamed equivalent of the standalone `CreateManagedLambdaExecutionRolePolicy`.
4. THE three new parameters SHALL be grouped under a new `AWS::CloudFormation::Interface`
   parameter group labeled `"Cache-Data"`, ordered after the existing groups and
   before the `"Module Source"` group.
5. THE template SHALL NOT add a `ProjectId` parameter.
6. THE template SHALL reuse the existing `Prefix`, `RolePath`, `S3BucketNameOrgPrefix`
   parameters and the existing `UseS3BucketNameOrgPrefix` condition.

---

## Requirement 6 — `prefix-based-infrastructure.yml` Conditions and Resources

**User Story:** As a platform administrator, I want the Cache-Data resources created
only when I opt in, so that the stack has no cache-data footprint by default.

#### Acceptance Criteria

1. THE template SHALL define a condition `CreateCacheData` equal to
   `!Equals [!Ref EnableCacheData, "true"]`.
2. THE template SHALL define a condition `CreateCacheDataManagedPolicy` equal to
   `!And [ CreateCacheData, !Equals [!Ref CreateManagedCacheDataLambdaExecutionRolePolicy, "TRUE"] ]`.
3. THE template SHALL declare the following logical IDs, each consuming the
   corresponding module via `Fn::Transform: AWS::Include` from
   `s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/cache-data/...`:
   - `CacheDataDynamoDbTable` → `cache-dynamodb-table.yml`
   - `CacheDataS3BucketRegional` → `cache-s3-bucket.yml`
   - `CacheDataS3BucketPolicy` → `cache-s3-bucket-policy.yml`
   - `ManagedLambdaExecutionRolePolicy` → `cache-managed-lambda-policy.yml`
4. THE logical IDs SHALL match exactly the sibling names the modules reference via
   `Ref`/`Fn::GetAtt`.
5. WHEN `EnableCacheData` is `"false"` THEN none of the four cache-data resources
   SHALL be created.
6. THE existing `cfn-lint` `ignore_checks` in the template SHALL remain sufficient
   (E6101, W2001, W8001); additional suppressions SHALL be added only if new lint
   findings arise from the added resources/conditions.

---

## Requirement 7 — `prefix-based-infrastructure.yml` Outputs

**User Story:** As a platform administrator, I want the Cache-Data outputs surfaced
from `prefix-based-infrastructure.yml`, so that other stacks and I can reference the
created resources exactly as with the standalone template.

#### Acceptance Criteria

1. WHEN `EnableCacheData` is `"true"` THEN the template SHALL output, under a
   `Cache-Data` output subsection, the equivalents of the standalone template's
   outputs: `DynamoDbWebConsole`, `S3BucketWebConsole`, `DynamoDbTableExport`,
   `S3BucketExport`, `S3BucketArnExport`, `DynamoDbTableArnExport`.
2. THE exported outputs SHALL use the identical export names from the standalone
   template: `${Prefix}-CacheDataDynamoDbTable`, `${Prefix}-CacheDataS3Bucket`,
   `${Prefix}-CacheDataS3BucketArn`, `${Prefix}-CacheDataDynamoDbTableArn`.
3. WHEN `CreateCacheDataManagedPolicy` is true THEN the template SHALL output
   `ManagedLambdaExecutionRolePolicyArn` exported as
   `${Prefix}-CacheDataManagedLambdaExecutionRolePolicy`.
4. EACH cache-data output SHALL carry the appropriate `Condition` (`CreateCacheData`
   or `CreateCacheDataManagedPolicy`) so that no output is emitted when the resources
   are not created.

---

## Requirement 8 — Cache-Data Sync Steering Document

**User Story:** As a maintainer, I want a steering rule that keeps the standalone
cache-data template and the cache-data modules in sync, so that the intentionally
un-modularized reference template does not drift from the modules.

#### Acceptance Criteria

1. A new steering document SHALL be created under `.kiro/steering/` scoped to the
   cache-data modules (`templates/v2/modules/cache-data/*`) and the standalone
   template (`templates/v2/storage/template-storage-cache-data.yml`).
2. THE steering document SHALL state that the resource definitions in the modules and
   the standalone template MUST be kept in sync, and SHALL document the intentional
   differences (the `${ProjectId}` → `cache-data` naming substitution, long-form
   intrinsics in modules, embedded module conditions, and the renamed
   `CreateManagedCacheDataLambdaExecutionRolePolicy` parameter).
3. THE steering document SHALL describe the required action when either side changes
   (review and update the other side within the same change).

---

## Requirement 9 — Documentation and Changelog

**User Story:** As a user of the template repository, I want documentation and the
changelog updated, so that the new capability is discoverable and traceable.

#### Acceptance Criteria

1. THE `templates/v2/modules/README.md` SHALL be updated with a Cache-Data Modules
   section listing the four new modules and their consuming template.
2. THE documentation for `prefix-based-infrastructure.yml` under
   `docs/templates/v2/account/` SHALL be updated (created if absent) to document the
   new Cache-Data parameter group, resources, conditions, and outputs. Existing
   blockquotes SHALL be preserved.
3. THE standalone `docs/templates/v2/storage/template-storage-cache-data-README.md`
   SHALL be updated only if needed to cross-reference the new modules; the template
   itself is unchanged.
4. A `CHANGELOG.md` entry SHALL be added under `v0.0.39 (unreleased)`, referencing
   this spec (`.kiro/specs/0-0-39-cache-data-modularization/`), listing the four new
   modules (Added) and the `prefix-based-infrastructure.yml` change (Changed), without
   modifying any existing changelog text.

---

## Requirement 10 — Validation

**User Story:** As a maintainer, I want the changed templates and modules validated,
so that I have confidence the changes deploy correctly.

#### Acceptance Criteria

1. THE `prefix-based-infrastructure.yml` template and the four new module files SHALL
   pass the repository's cfn-lint validation (via the existing linter/pytest tooling).
2. THE standalone `template-storage-cache-data.yml` SHALL remain byte-for-byte
   unchanged (verified by leaving it untouched).
3. THE storage management role S3 module access SHALL be confirmed to cover the
   `cache-data/` module path (already verified: `S3ModuleBucketGetObject` grants the
   namespace-wide `${S3ModuleLocation}/${S3ModuleNamespace}/*`).

---

## Naming Note

Applying the `${ProjectId}` → `cache-data` substitution to the DynamoDB table produces
the name `${Prefix}-cache-data-CacheData`, which reads with a slight redundancy
(`cache-data-CacheData`). This is a direct, literal application of the agreed
substitution and preserves the standalone resource identifier suffix (`CacheData`).
Flagging for awareness; no action required unless you prefer a different identifier.

**The redundancy is acceptable**
