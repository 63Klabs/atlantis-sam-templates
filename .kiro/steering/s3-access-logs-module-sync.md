---
inclusion: fileMatch
fileMatchPattern: 'templates/v2/{modules/s3-access-logs/*,storage/template-storage-s3-access-logs.yml}'
---

# S3 Access-Logs Module Sync

## Purpose

The standalone template `templates/v2/storage/template-storage-s3-access-logs.yml` and the
`AWS::Include` module snippets under `templates/v2/modules/s3-access-logs/` share a common
ancestry: a single S3 access-log bucket and its bucket policy.

The standalone template is the **canonical reference for the shared configuration
primitives** (prefix + project scoped) and is intentionally left un-modularized and
**frozen** as a deprecated per-project template.

> **Important (updated v0.0.44):** As of v0.0.44 the account-wide side is a **two-bucket
> superset** of the standalone. It adds a separate CloudFront legacy bucket, per-prefix
> lifecycle rules, prefix-scoped and multi-principal bucket policies (including a Bedrock
> large-object delivery statement and a CloudFront standard-logging-v2 statement), and new
> parameters — none of which apply to a single project-scoped bucket. The 1:1 "same two
> resources, identical configuration" relationship no longer holds. The sync obligation is
> therefore **narrowed to the shared primitives only** (see "Shared Primitives" below); the
> account-wide-only behaviors listed under "Account-Wide-Only Supersets" are intentional and
> MUST NOT be back-ported into the standalone template.

## Standalone Logical ID to Module File Mapping

| Standalone logical ID | Resource type | Module file |
|-----------------------|---------------|-------------|
| `AccessLogBucketRegional` | `AWS::S3::Bucket` | `templates/v2/modules/s3-access-logs/s3-access-log-bucket.yml` |
| `LoggingBucketPolicy` | `AWS::S3::BucketPolicy` | `templates/v2/modules/s3-access-logs/s3-access-log-bucket-policy.yml` |
| _(none — account-wide only)_ | `AWS::S3::Bucket` | `templates/v2/modules/s3-access-logs/cloudfront-legacy-log-bucket.yml` |
| _(none — account-wide only)_ | `AWS::S3::BucketPolicy` | `templates/v2/modules/s3-access-logs/cloudfront-legacy-log-bucket-policy.yml` |

The consuming parent template (`templates/v2/account/account-wide-infrastructure.yml`)
names the bucket resource `AccessLogBucketRegional` (matching the standalone logical ID so
the policy module's `Ref: AccessLogBucketRegional` resolves) and names the policy resource
`AccessLogBucketPolicy`. The parent also names the two legacy-CloudFront resources
`CloudFrontLegacyLogBucket` and `CloudFrontLegacyLogBucketPolicy`. The two
`cloudfront-legacy-log-bucket*.yml` modules have **no standalone counterpart** and are not
subject to the sync obligation.

## Intentional Differences (Expected — Do NOT "fix" these)

The modules deliberately diverge from the standalone template in the following ways.
These differences are by design and must be preserved when syncing:

1. **Naming substitution (Prefix and ProjectId removed).** The standalone bucket name is
   `${S3BucketNameOrgPrefix}-${Prefix}-${ProjectId}-access-logs-${AWS::AccountId}-${AWS::Region}-an`
   (or the no-org-prefix variant `${Prefix}-${ProjectId}-access-logs-...`). The modules
   drop the `${Prefix}` and `${ProjectId}` tokens entirely because the account-wide parent
   has neither:
   - With org prefix: `${S3BucketNameOrgPrefix}-access-logs-${AWS::AccountId}-${AWS::Region}-an`
   - Without org prefix: `access-logs-${AWS::AccountId}-${AWS::Region}-an`

2. **Long-form intrinsics.** The standalone template uses YAML shorthand tags (`!Sub`,
   `!Ref`, `!If`, `!GetAtt`, `!Join`). The modules use long-form intrinsics only
   (`Fn::Sub`, `Ref`, `Fn::If`, `Fn::GetAtt`, `Fn::Join`) because `AWS::Include` does not
   support shorthand tags.

3. **Embedded module conditions.** Each module carries a resource-level `Condition:` key
   that the standalone template does not use. Both `s3-access-log-bucket.yml` and
   `s3-access-log-bucket-policy.yml` carry `Condition: EnableS3AccessLogBucket`. The
   condition name intentionally matches the account-wide convention (`EnableS3ArtifactsBucket`,
   etc.) rather than the `Create*` convention used by the cache-data modules.

4. **Outputs live in the parent, with different export names.** The standalone template
   exports `${Prefix}-${ProjectId}-LoggingBucketName` and `-LoggingBucketArn`. Because the
   account-wide parent has no `Prefix`/`ProjectId`, its outputs use the `${OrgPrefix}-`
   convention (for example `${OrgPrefix}-S3-AccessLog-Bucket-Name`). Module files never
   contain outputs.

## Account-Wide-Only Supersets (v0.0.44+) (Expected — Do NOT back-port)

The account-wide modules diverge from the standalone in the following additional,
intentional ways. These are account-wide-only concepts that do NOT belong in a single
project-scoped bucket, so they MUST NOT be "synced" back into the standalone template:

- **D1 — Bucket count.** The account-wide side is two buckets + two policies: the main
  access-log bucket (ACLs off) **plus** a separate `cloudfront-logs-legacy` bucket (ACLs on).
  The standalone remains one bucket + one policy.
- **D2 — `AllowLegacyCloudFrontLogs` semantics.** In the account-wide parent this parameter
  provisions the **separate** legacy bucket. In the standalone it toggles ACLs on its single
  bucket (unchanged).
- **D3 — Main bucket ownership.** The account-wide main bucket is unconditionally
  `BucketOwnerEnforced` (ACLs disabled), with no `AllowLegacyCloudFrontLogs` ownership branch.
  The standalone keeps its conditional ownership/public-access-block toggle.
- **D4 — Lifecycle.** The account-wide main bucket has multiple prefix-filtered rules
  (`cloudfront/` on `LogExpirationInDays`; four `s3access/*` rules on
  `S3AccessLogExpirationInDays`; a conditional `bedrock/` rule on
  `BedrockLargeObjectLogExpirationInDays`). The standalone keeps its single `DeleteOldLogs`
  rule on `LogExpirationInDays`.
- **D5 — Policy scope.** The account-wide main policy scopes each grant to a prefix
  (`.../s3access/*`, `.../cloudfront/*`, `.../bedrock/AWSLogs/.../BedrockModelInvocationLogs/*`).
  The standalone grants whole-bucket `/*`.
- **D6 — Principals.** The account-wide main policy grants `logging.s3.amazonaws.com`
  (s3access), `delivery.logs.amazonaws.com` (CloudFront v2, `cloudfront/`), and (conditionally)
  `bedrock.amazonaws.com`. The legacy bucket policy grants `delivery.logs.amazonaws.com` for
  CloudFront v1. The standalone grants `logging.s3` + optional legacy `delivery.logs` (v1).
- **D7 — Parameters/conditions.** The account-wide parent adds `S3AccessLogExpirationInDays`,
  `EnableBedrockLargeObjectLogging`, `BedrockLargeObjectLogExpirationInDays`,
  `BedrockLargeObjectLogBucketName` (and supporting conditions). The standalone does not have
  these.

## Shared Primitives (still kept in sync)

Only the following shared configuration primitives on the **main** access-log bucket +
policy must still match the standalone template (translating for the intentional differences
above): encryption (AES256 with bucket keys), versioning (Suspended), retention policies
(Retain / UpdateReplace Retain), the `DenyNonSecureTransportAccess` policy statement, and the
shape of the ACL-toggle mechanism (`PublicAccessBlockConfiguration` + `OwnershipControls`).
The per-prefix lifecycle rules (D4), prefix-scoped/multi-principal statements (D5/D6), the
second legacy bucket (D1/D2), and the new parameters (D7) are account-wide-only and are NOT
synced.

## Required Action When Either Side Changes

A change to a **shared primitive** (see "Shared Primitives" above) on the main
`s3-access-log-bucket.yml` / `s3-access-log-bucket-policy.yml` module or on the standalone
template triggers a review and matching update of the **other** side **within the same
change set**:

1. When editing a shared primitive in a `templates/v2/modules/s3-access-logs/s3-access-log-*.yml`
   module, review the corresponding resource in
   `templates/v2/storage/template-storage-s3-access-logs.yml` and apply the equivalent change
   (translating for the intentional differences above).
2. When editing a shared primitive in `templates/v2/storage/template-storage-s3-access-logs.yml`,
   review the corresponding module file(s) and apply the equivalent change.
3. Use the mapping table above to locate the counterpart resource.
4. Changes confined to the **Account-Wide-Only Supersets** (D1–D7) or to the two
   `cloudfront-legacy-log-bucket*.yml` modules do **not** require any standalone update.
5. Confirm that only the intentional differences (and the D1–D7 supersets) remain after the
   sync — no unintended drift in the shared primitives.
