# Design — Cache-Data Modularization

## Overview

This design extracts the four Cache-Data resources into reusable `AWS::Include`
module snippets under `templates/v2/modules/cache-data/`, and wires those modules into
`templates/v2/account/prefix-based-infrastructure.yml` behind an `EnableCacheData`
on/off parameter. The standalone `templates/v2/storage/template-storage-cache-data.yml`
is the canonical reference and is **not modified**; a new steering document keeps the
two in sync.

The design follows the established module pattern already used by the account-wide and
pipeline modules: a module file is the body of a single resource (no logical ID, no
`Resources:` wrapper), uses long-form intrinsic functions only, and opens with a
contract comment block naming the parent parameters, conditions, and sibling logical
IDs it depends on.

### Design Goals

1. Reuse the exact resource configuration from the standalone template (verbatim),
   changing only what is required for the module/parent contract:
   - `${ProjectId}` naming token to literal `cache-data`
   - shorthand intrinsics (`!Sub`, `!Ref`, `!If`, `!GetAtt`) to long-form
   - add resource-level `Condition:` keys driven by the parent toggle
2. Preserve export names so downstream consumers are unaffected regardless of which
   stack owns the cache-data resources.
3. No default cache-data footprint — resources exist only when `EnableCacheData=true`.

### Non-Goals

- Modifying `template-storage-cache-data.yml` (unchanged).
- Modifying `account-wide-infrastructure.yml`.
- Changing any resource configuration (TTL, encryption, lifecycle, IAM actions).

---

## Architecture

### Component Map

```
templates/v2/modules/cache-data/           (NEW)
├── cache-dynamodb-table.yml                -> consumed as CacheDataDynamoDbTable
├── cache-s3-bucket.yml                     -> consumed as CacheDataS3BucketRegional
├── cache-s3-bucket-policy.yml              -> consumed as CacheDataS3BucketPolicy
└── cache-managed-lambda-policy.yml         -> consumed as ManagedLambdaExecutionRolePolicy

templates/v2/account/prefix-based-infrastructure.yml   (MODIFIED)
├── Parameters:  + EnableCacheData
│                + CacheDataPurgeAgeOfCachedBucketObjInDays
│                + CreateManagedCacheDataLambdaExecutionRolePolicy
├── Metadata:    + "Cache-Data" parameter group (before "Module Source")
├── Conditions:  + CreateCacheData
│                + CreateCacheDataManagedPolicy
├── Resources:   + 4 AWS::Include cache-data resources
└── Outputs:     + Cache-Data console links + exports (conditional)

templates/v2/storage/template-storage-cache-data.yml   (UNCHANGED — reference source)

.kiro/steering/cache-data-module-sync.md    (NEW steering doc)
```

### Module Resolution Path

Modules are resolved at deploy time by the CloudFormation `AWS::Include` transform:

```
s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/cache-data/<module>.yml
```

`prefix-based-infrastructure.yml` already declares `S3ModuleLocation` and
`S3ModuleNamespace` under a `"Module Source"` group, so no new module-source parameters
are needed. The storage management role's `S3ModuleBucketGetObject` statement grants
namespace-wide read (`${S3ModuleLocation}/${S3ModuleNamespace}/*`), which already
covers the `cache-data/` path (verified in requirements Q8).

### Condition Flow

```
EnableCacheData (param, default "false")
   └── CreateCacheData = EnableCacheData == "true"
           ├── CacheDataDynamoDbTable        (Condition: CreateCacheData)
           ├── CacheDataS3BucketRegional     (Condition: CreateCacheData)
           └── CacheDataS3BucketPolicy       (Condition: CreateCacheData)

CreateManagedCacheDataLambdaExecutionRolePolicy (param, default "TRUE")
   └── CreateCacheDataManagedPolicy = And(CreateCacheData, param == "TRUE")
           └── ManagedLambdaExecutionRolePolicy (Condition: CreateCacheDataManagedPolicy)
```

A CloudFormation resource may carry only one `Condition`. The managed policy therefore
uses the combined `CreateCacheDataManagedPolicy` condition rather than nesting two.

---

## Detailed Design

### Naming Translation (standalone to module)

| Aspect | Standalone (`template-storage-cache-data.yml`) | Module (`cache-data/*`) |
|--------|-----------------------------------------------|-------------------------|
| Table name | `${Prefix}-${ProjectId}-CacheData` | `${Prefix}-cache-data-CacheData` |
| Bucket name (org prefix) | `${S3BucketNameOrgPrefix}-${Prefix}-${ProjectId}-${AWS::AccountId}-${AWS::Region}-an` | `${S3BucketNameOrgPrefix}-${Prefix}-cache-data-${AWS::AccountId}-${AWS::Region}-an` |
| Bucket name (no org prefix) | `${Prefix}-${ProjectId}-${AWS::AccountId}-${AWS::Region}-an` | `${Prefix}-cache-data-${AWS::AccountId}-${AWS::Region}-an` |
| Managed policy name | `${Prefix}-${ProjectId}-ManagedLambdaExecutionRolePolicy` | `${Prefix}-cache-data-ManagedLambdaExecutionRolePolicy` |
| Bucket policy Lambda SourceArn | `arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:project/${Prefix}-*` | unchanged (Prefix-scoped) |
| Exports | `${Prefix}-CacheData*` | identical (`${Prefix}-CacheData*`) |
| Intrinsics | shorthand (`!Sub`, `!Ref`, `!If`, `!GetAtt`) | long-form (`Fn::Sub`, `Ref`, `Fn::If`, `Fn::GetAtt`) |
| Resource `Condition` | none / `CreateManagedPolicy` (managed policy) | `CreateCacheData` / `CreateCacheDataManagedPolicy` |

### Module 1 — `cache-dynamodb-table.yml`

Contract comment declares: parameter `Prefix`; condition `CreateCacheData`.

```yaml
# -- Cache-Data DynamoDb Table --
# From: https://www.npmjs.com/package/@63klabs/cache-data
# Parent template must define parameters: Prefix
# Parent template must define conditions: CreateCacheData
# NOTE: AWS::Include does not support YAML shorthand tags (!Sub, !Ref, etc.)
#       All intrinsic functions must use long-form syntax (Fn::Sub, Ref, etc.)
# KEEP IN SYNC with templates/v2/storage/template-storage-cache-data.yml
Type: AWS::DynamoDB::Table
Condition: CreateCacheData
UpdateReplacePolicy: Retain
DeletionPolicy: Delete
Properties:
  TableName:
    Fn::Sub: "${Prefix}-cache-data-CacheData"
  AttributeDefinitions:
    - AttributeName: "id_hash"
      AttributeType: "S"
  KeySchema:
    - AttributeName: "id_hash"
      KeyType: "HASH"
  TimeToLiveSpecification:
    AttributeName: "purge_ts"
    Enabled: true
  BillingMode: "PAY_PER_REQUEST"
```

### Module 2 — `cache-s3-bucket.yml`

Contract comment declares: parameters `Prefix`, `S3BucketNameOrgPrefix`,
`CacheDataPurgeAgeOfCachedBucketObjInDays`; conditions `UseS3BucketNameOrgPrefix`,
`CreateCacheData`.

```yaml
# -- Cache-Data S3 Bucket --
# Parent template must define parameters: Prefix, S3BucketNameOrgPrefix, CacheDataPurgeAgeOfCachedBucketObjInDays
# Parent template must define conditions: UseS3BucketNameOrgPrefix, CreateCacheData
# NOTE: long-form intrinsics only. KEEP IN SYNC with template-storage-cache-data.yml
Type: AWS::S3::Bucket
Condition: CreateCacheData
Properties:
  BucketName:
    Fn::If:
      - UseS3BucketNameOrgPrefix
      - Fn::Sub: "${S3BucketNameOrgPrefix}-${Prefix}-cache-data-${AWS::AccountId}-${AWS::Region}-an"
      - Fn::Sub: "${Prefix}-cache-data-${AWS::AccountId}-${AWS::Region}-an"
  BucketNamespace: "account-regional"
  PublicAccessBlockConfiguration:
    BlockPublicAcls: true
    BlockPublicPolicy: true
    IgnorePublicAcls: true
    RestrictPublicBuckets: true
  BucketEncryption:
    ServerSideEncryptionConfiguration:
      - ServerSideEncryptionByDefault:
          SSEAlgorithm: AES256
  LifecycleConfiguration:
    Rules:
      - Id: "ExpireObjects"
        AbortIncompleteMultipartUpload:
          DaysAfterInitiation: 1
        ExpirationInDays:
          Ref: CacheDataPurgeAgeOfCachedBucketObjInDays
        Prefix: "cache"
        NoncurrentVersionExpirationInDays:
          Ref: CacheDataPurgeAgeOfCachedBucketObjInDays
        Status: "Enabled"
```

### Module 3 — `cache-s3-bucket-policy.yml`

Contract comment declares: parameter `Prefix`; condition `CreateCacheData`; sibling
logical ID `CacheDataS3BucketRegional`.

```yaml
# -- Cache-Data S3 Bucket Policy --
# Parent template must define parameters: Prefix
# Parent template must define conditions: CreateCacheData
# Parent must name the bucket resource 'CacheDataS3BucketRegional'
# NOTE: long-form intrinsics only. KEEP IN SYNC with template-storage-cache-data.yml
Type: AWS::S3::BucketPolicy
Condition: CreateCacheData
Properties:
  Bucket:
    Ref: CacheDataS3BucketRegional
  PolicyDocument:
    Version: "2012-10-17"
    Id: SecurityPolicy
    Statement:
      - Sid: "DenyNonSecureTransportAccess"
        Effect: Deny
        Principal: "*"
        Action: "s3:*"
        Resource:
          - Fn::Sub: "arn:aws:s3:::${CacheDataS3BucketRegional}"
          - Fn::Sub: "arn:aws:s3:::${CacheDataS3BucketRegional}/*"
        Condition:
          Bool:
            "aws:SecureTransport": false
      - Sid: AllowLambdaReadWriteDelete
        Action:
          - 's3:GetObject'
          - 's3:PutObject'
          - 's3:DeleteObject'
        Effect: Allow
        Principal:
          Service: lambda.amazonaws.com
        Resource:
          Fn::Sub: "arn:aws:s3:::${CacheDataS3BucketRegional}/cache/*"
        Condition:
          StringLike:
            "aws:SourceArn":
              Fn::Sub: "arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:project/${Prefix}-*"
```

### Module 4 — `cache-managed-lambda-policy.yml`

Contract comment declares: parameters `Prefix`, `RolePath`; condition
`CreateCacheDataManagedPolicy`; sibling logical IDs `CacheDataS3BucketRegional`,
`CacheDataDynamoDbTable`.

```yaml
# -- Managed Policy for Lambda Execution Roles accessing Cache-Data --
# Parent template must define parameters: Prefix, RolePath
# Parent template must define conditions: CreateCacheDataManagedPolicy
# Parent must name resources 'CacheDataS3BucketRegional' and 'CacheDataDynamoDbTable'
# NOTE: long-form intrinsics only. KEEP IN SYNC with template-storage-cache-data.yml
Type: AWS::IAM::ManagedPolicy
Condition: CreateCacheDataManagedPolicy
Properties:
  ManagedPolicyName:
    Fn::Sub: "${Prefix}-cache-data-ManagedLambdaExecutionRolePolicy"
  Description: "Standard permissions for Managing permissions to access Cache-Data in a Lambda Execution role"
  Path:
    Ref: RolePath
  PolicyDocument:
    Version: '2012-10-17'
    Statement:
      - Sid: LambdaAccessToS3BucketCacheData
        Action:
          - s3:PutObject
          - s3:GetObject
          - s3:GetObjectVersion
        Effect: Allow
        Resource:
          Fn::Sub: 'arn:aws:s3:::${CacheDataS3BucketRegional}/cache/*'
      - Sid: LambdaAccessToS3ListBucket
        Action:
          - s3:ListBucket
        Effect: Allow
        Resource:
          Fn::Sub: 'arn:aws:s3:::${CacheDataS3BucketRegional}'
      - Sid: LambdaAccessToDynamoDBTableCacheData
        Action:
          - dynamodb:GetItem
          - dynamodb:Scan
          - dynamodb:Query
          - dynamodb:BatchGetItem
          - dynamodb:PutItem
          - dynamodb:UpdateItem
          - dynamodb:BatchWriteItem
        Effect: Allow
        Resource:
          Fn::Sub:
            - 'arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/${TableName}'
            - TableName:
                Ref: CacheDataDynamoDbTable
```

### `prefix-based-infrastructure.yml` Changes

**Parameters (new):**

```yaml
  # ---------------------------------------------------------------------------
  # Cache-Data

  EnableCacheData:
    Type: String
    Description: "Set to 'true' to create the shared, prefix-wide Cache-Data resources (DynamoDB table, S3 bucket, bucket policy, and optional managed Lambda execution policy). See https://www.npmjs.com/package/@63klabs/cache-data"
    Default: "false"
    AllowedValues: ["true", "false"]
    ConstraintDescription: "Must be 'true' or 'false'."

  CacheDataPurgeAgeOfCachedBucketObjInDays:
    Type: Number
    Description: "Similar to CacheData_PurgeExpiredCacheEntriesInHours, but for the S3 Bucket. S3 calculates from time object is created/last modified (not accessed). This should be longer than your longest cache expiration set in custom/policies. Keeping objects in S3 for too long increases storage costs. (30 is recommended)"
    Default: 15
    MinValue: 3
    ConstraintDescription: "Choose a value of 3 days or greater. This should be slightly longer than the longest cache expiration expected"

  CreateManagedCacheDataLambdaExecutionRolePolicy:
    Type: String
    Description: "Create a managed Lambda Execution Role Policy for accessing Cache-Data. Set to FALSE to supply your own policy for the Lambda Execution Role. Only applies when EnableCacheData is 'true'."
    AllowedValues: ["TRUE", "FALSE"]
    Default: "TRUE"
```

**Metadata group (inserted before "Module Source"):**

```yaml
      -
        Label:
          default: "Cache-Data"
        Parameters:
          - EnableCacheData
          - CacheDataPurgeAgeOfCachedBucketObjInDays
          - CreateManagedCacheDataLambdaExecutionRolePolicy
```

**Conditions (new):**

```yaml
  CreateCacheData: !Equals [!Ref EnableCacheData, "true"]
  CreateCacheDataManagedPolicy: !And
    - !Condition CreateCacheData
    - !Equals [!Ref CreateManagedCacheDataLambdaExecutionRolePolicy, "TRUE"]
```

The existing `UseS3BucketNameOrgPrefix` condition is reused by the bucket module.

**Resources (new, appended to Resources):**

```yaml
  # -- Cache-Data DynamoDb Table (Conditional) --
  CacheDataDynamoDbTable:
    Fn::Transform:
      Name: AWS::Include
      Parameters:
        Location: !Sub "s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/cache-data/cache-dynamodb-table.yml"

  # -- Cache-Data S3 Bucket (Conditional) --
  CacheDataS3BucketRegional:
    Fn::Transform:
      Name: AWS::Include
      Parameters:
        Location: !Sub "s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/cache-data/cache-s3-bucket.yml"

  # -- Cache-Data S3 Bucket Policy (Conditional) --
  CacheDataS3BucketPolicy:
    Fn::Transform:
      Name: AWS::Include
      Parameters:
        Location: !Sub "s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/cache-data/cache-s3-bucket-policy.yml"

  # -- Cache-Data Managed Lambda Execution Policy (Conditional) --
  ManagedLambdaExecutionRolePolicy:
    Fn::Transform:
      Name: AWS::Include
      Parameters:
        Location: !Sub "s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/cache-data/cache-managed-lambda-policy.yml"
```

**Outputs (new, conditional):** mirror the standalone template's outputs with identical
export names.

```yaml
  # ---------------------------------------------------------------------------
  # Cache-Data

  CacheDataDynamoDbWebConsole:
    Condition: CreateCacheData
    Description: "DynamoDb Table Web Console"
    Value: !Sub "https://console.aws.amazon.com/dynamodbv2/home?region=${AWS::Region}#table?name=${CacheDataDynamoDbTable}&initialTableGroup=%23all"

  CacheDataS3BucketWebConsole:
    Condition: CreateCacheData
    Description: "S3 Bucket Web Console"
    Value: !Sub "https://s3.console.aws.amazon.com/s3/buckets/${CacheDataS3BucketRegional}?region=${AWS::Region}"

  CacheDataDynamoDbTableExport:
    Condition: CreateCacheData
    Description: "DynamoDb Table Name"
    Value: !Ref CacheDataDynamoDbTable
    Export:
      Name: !Sub '${Prefix}-CacheDataDynamoDbTable'

  CacheDataS3BucketExport:
    Condition: CreateCacheData
    Description: "S3 Bucket Name"
    Value: !Ref CacheDataS3BucketRegional
    Export:
      Name: !Sub '${Prefix}-CacheDataS3Bucket'

  CacheDataS3BucketArnExport:
    Condition: CreateCacheData
    Description: "S3 Bucket ARN"
    Value: !Sub "arn:aws:s3:::${CacheDataS3BucketRegional}"
    Export:
      Name: !Sub '${Prefix}-CacheDataS3BucketArn'

  CacheDataDynamoDbTableArnExport:
    Condition: CreateCacheData
    Description: "DynamoDb Table ARN"
    Value: !Sub "arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/${CacheDataDynamoDbTable}"
    Export:
      Name: !Sub '${Prefix}-CacheDataDynamoDbTableArn'

  CacheDataManagedLambdaExecutionRolePolicyArn:
    Condition: CreateCacheDataManagedPolicy
    Description: "Managed policy ARN for Lambda Execution Role to access Cache-Data resources"
    Value: !Ref ManagedLambdaExecutionRolePolicy
    Export:
      Name: !Sub '${Prefix}-CacheDataManagedLambdaExecutionRolePolicy'
```

> Note: Output logical IDs are prefixed with `CacheData` to avoid collision with any
> existing output names in `prefix-based-infrastructure.yml`. Export names remain
> exactly as in the standalone template.

### Steering Document — `cache-data-module-sync.md`

Inclusion mode: `fileMatch` scoped to the cache-data module and standalone template
paths, so it activates whenever those files are in context.

Content outline:
- Purpose: the standalone template and the cache-data modules describe the same
  resources and MUST be kept in sync.
- The intentional differences that are expected (naming substitution, long-form
  intrinsics, embedded conditions, renamed managed-policy parameter).
- Required action: any change to one side triggers a review/update of the other side
  within the same change set.
- A mapping table (standalone logical ID to module file).

---

## Components and Interfaces

The design is composed of four module snippets (each the body of a single resource)
and one parent-template integration point. Because `AWS::Include` snippets are not
standalone templates, their "interface" is a contract expressed in the leading comment
block: the parent template must supply the named parameters, conditions, and sibling
logical IDs.

| Component | File | Resource Type | Interface it consumes from parent |
|-----------|------|---------------|-----------------------------------|
| `CacheDataDynamoDbTable` | `modules/cache-data/cache-dynamodb-table.yml` | `AWS::DynamoDB::Table` | Params: `Prefix`. Conditions: `CreateCacheData` |
| `CacheDataS3BucketRegional` | `modules/cache-data/cache-s3-bucket.yml` | `AWS::S3::Bucket` | Params: `Prefix`, `S3BucketNameOrgPrefix`, `CacheDataPurgeAgeOfCachedBucketObjInDays`. Conditions: `UseS3BucketNameOrgPrefix`, `CreateCacheData` |
| `CacheDataS3BucketPolicy` | `modules/cache-data/cache-s3-bucket-policy.yml` | `AWS::S3::BucketPolicy` | Params: `Prefix`. Conditions: `CreateCacheData`. Sibling: `CacheDataS3BucketRegional` |
| `ManagedLambdaExecutionRolePolicy` | `modules/cache-data/cache-managed-lambda-policy.yml` | `AWS::IAM::ManagedPolicy` | Params: `Prefix`, `RolePath`. Conditions: `CreateCacheDataManagedPolicy`. Siblings: `CacheDataS3BucketRegional`, `CacheDataDynamoDbTable` |
| Parent integration | `account/prefix-based-infrastructure.yml` | (host template) | Declares params/conditions above; references each module via `Fn::Transform: AWS::Include` at the module resolution path |

**Interface contract rules (all modules):**

- No logical ID and no `Resources:` wrapper — each file is a bare resource body.
- Long-form intrinsics only (`Fn::Sub`, `Ref`, `Fn::If`, `Fn::GetAtt`); shorthand tags
  are unsupported by `AWS::Include`.
- Each module carries exactly one resource-level `Condition:` key.
- The parent binds each module to a fixed logical ID; sibling references inside a module
  (e.g. `Ref: CacheDataS3BucketRegional`) are satisfied only because the parent uses
  those exact logical IDs. Renaming a parent logical ID is a breaking interface change.

---

## Data Models

### DynamoDB Cache Table

| Attribute | Type | Role |
|-----------|------|------|
| `id_hash` | String (`S`) | Partition (HASH) key — cache entry identifier |
| `purge_ts` | Number (epoch seconds) | TTL attribute (`TimeToLiveSpecification.Enabled: true`) |

- Billing mode: `PAY_PER_REQUEST` (on-demand).
- `UpdateReplacePolicy: Retain`, `DeletionPolicy: Delete`.
- Non-key attributes are schemaless (written by the cache-data library at runtime).

### S3 Cache Object Model

- All cached objects live under the `cache/` key prefix.
- Lifecycle rule `ExpireObjects` expires current and noncurrent objects after
  `CacheDataPurgeAgeOfCachedBucketObjInDays` days and aborts incomplete multipart
  uploads after 1 day.
- Encryption: SSE-S3 (`AES256`); all public access blocked.

### Parameter Data Model (parent template)

| Parameter | Type | Default | Allowed / Constraints |
|-----------|------|---------|-----------------------|
| `EnableCacheData` | String | `"false"` | `true` \| `false` |
| `CacheDataPurgeAgeOfCachedBucketObjInDays` | Number | `15` | `MinValue: 3` |
| `CreateManagedCacheDataLambdaExecutionRolePolicy` | String | `"TRUE"` | `TRUE` \| `FALSE` |

### Export Model

Export names are identical to the standalone template so consumers are stack-agnostic:
`${Prefix}-CacheDataDynamoDbTable`, `${Prefix}-CacheDataS3Bucket`,
`${Prefix}-CacheDataS3BucketArn`, `${Prefix}-CacheDataDynamoDbTableArn`, and
`${Prefix}-CacheDataManagedLambdaExecutionRolePolicy` (managed-policy export is
conditional on `CreateCacheDataManagedPolicy`).

---

## Correctness Properties

These invariants must hold for the design to be considered correct:

1. **No footprint when disabled.** With `EnableCacheData="false"`, none of the four
   cache-data resources and none of the cache-data outputs/exports are created.
2. **Export stability.** For any given `Prefix`, the exported names match the standalone
   template exactly, regardless of which stack owns the resources.
3. **Single owner per Prefix.** The `EnableCacheData` toggle ensures cache-data resources
   are owned by exactly one stack per `Prefix`, preventing duplicate-export collisions.
4. **One condition per resource.** Each module resource carries exactly one `Condition`;
   the managed policy uses the combined `CreateCacheDataManagedPolicy` rather than nesting.
5. **Managed-policy gating.** `CreateCacheDataManagedPolicy` is true only when both
   `CreateCacheData` is true and `CreateManagedCacheDataLambdaExecutionRolePolicy="TRUE"`.
6. **Naming fidelity.** Module resource configuration is byte-equivalent to the standalone
   template except for the documented translations (`${ProjectId}` → `cache-data`,
   shorthand → long-form intrinsics, added `Condition:` keys, renamed managed-policy param).
7. **Reference source untouched.** `template-storage-cache-data.yml` is unchanged.
8. **Sibling references resolve.** Every sibling logical ID referenced inside a module
   is present in the parent under that exact name.

---

## Error Handling

Errors are handled at the CloudFormation/deployment layer, since modules are declarative
snippets with no runtime logic of their own.

- **Missing module object in S3.** If a `cache-data/*.yml` object is absent at the
  resolved `AWS::Include` location, the template transform fails at change-set creation.
  Mitigation: modules are published to the same namespace path already granted by the
  storage management role's `S3ModuleBucketGetObject` statement.
- **Undefined parent parameter/condition/sibling.** A module referencing a name the
  parent does not declare produces a transform/validation error before any resource is
  created. The contract comment blocks and the Components and Interfaces table are the
  guard against this; cfn-lint over the parent surfaces it early.
- **Shorthand intrinsic in a module.** Shorthand tags silently break under `AWS::Include`.
  Guarded by the "long-form only" rule and static review; no shorthand appears in any
  module body.
- **Toggle typos.** `AllowedValues` on `EnableCacheData` and
  `CreateManagedCacheDataLambdaExecutionRolePolicy` reject invalid values at parameter
  validation time with the provided `ConstraintDescription`.
- **Deploy-time failures roll back.** Because all four resources are conditional and
  gated by the same `CreateCacheData` condition, a failed create rolls back cleanly
  without leaving partial cache-data resources.
- **Retention on delete.** The DynamoDB table uses `UpdateReplacePolicy: Retain` to
  avoid accidental data loss on replacement; deletion behavior is otherwise `Delete`.

---

## Testing Strategy

Following the repository testing guidelines (favor fast unit tests, minimize
property-based tests):

1. Run the existing cfn-lint suite over the modified `prefix-based-infrastructure.yml`.
2. Static review of each module against the module-standards checklist (no logical ID,
   long-form intrinsics, contract comment, exactly one correct `Condition`, sibling IDs
   present in parent).
3. Confirm `template-storage-cache-data.yml` is unchanged (diff against baseline).
4. Verify the disabled path: with `EnableCacheData="false"`, no cache-data resources,
   outputs, or exports are emitted.
5. Verify export-name parity between the modularized outputs and the standalone template.

No property-based tests are added — the template set is small and controlled, so fast
unit-level linting and static review provide sufficient CI/CD confidence.

---

## cfn-lint / Validation Strategy

- `prefix-based-infrastructure.yml` already suppresses `E6101`, `W2001`, `W8001`,
  which cover AWS::Include invisibility and apparently-unused parameters/conditions.
  The new parameters/conditions are consumed only inside modules, so these existing
  suppressions remain sufficient. No new suppressions are anticipated.
- Module files are resource-body snippets and are not independently lintable as full
  templates; they are validated indirectly via the parent template and by review
  against the module standards checklist.
- Validation runs through the repository's existing linter tooling
  (`cfn_linter` / pytest). Per the testing guidelines, fast unit-level linting is the
  primary mechanism; no property-based tests are added.

See the [Testing Strategy](#testing-strategy) section above for the full test plan.

---

## Design Decisions and Rationale

1. **Standalone template unchanged; modules maintained separately.** Per your
   direction, avoids introducing new required parameters (`S3ModuleLocation`) into an
   already-deployed (v0.0.15) template and keeps the reference implementation stable.
   The sync steering doc mitigates drift risk.
2. **`${ProjectId}` to `cache-data` literal.** `prefix-based-infrastructure.yml` is
   prefix-scoped with no project concept; substituting the literal yields one shared
   cache-data set per Prefix and keeps the modules parameter-simple.
3. **Identical export names.** Downstream consumers reference the same exports
   regardless of which stack owns the resources; the `EnableCacheData` toggle enforces
   single ownership per Prefix, preventing collisions.
4. **Combined `CreateCacheDataManagedPolicy` condition.** CloudFormation allows one
   `Condition` per resource, so the managed policy's two gating inputs are combined
   with `Fn::And`.
5. **`CacheData`-prefixed output logical IDs.** Prevents any clash with existing
   outputs in the parent while preserving the canonical export names.

---

## Requirements Traceability

| Requirement | Addressed by |
|-------------|--------------|
| R1 DynamoDB module | Module 1 design |
| R2 S3 bucket module | Module 2 design |
| R3 bucket policy module | Module 3 design |
| R4 managed policy module | Module 4 design + combined condition |
| R5 parameters & metadata | Parameters + Metadata group design |
| R6 conditions & resources | Conditions + Resources design |
| R7 outputs | Outputs design |
| R8 steering doc | Steering document design |
| R9 docs & changelog | Handled in tasks (docs + CHANGELOG) |
| R10 validation | Validation strategy |
