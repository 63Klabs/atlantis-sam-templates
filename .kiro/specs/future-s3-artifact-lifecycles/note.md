# Future Consideration: S3 Artifact Bucket Lifecycles & Promotion Retention

**Status:** Parking-lot note for a future spec
**Raised by:** spec `0-0-40-pipeline-with-promotion-approval` (design decision DD-1)
**Date:** 2026-08-14

---

## Summary

The cross-account promotion feature stores promoted source archives (`source.zip`) and
audit manifests (`promote.json`) under a `promotions/*` prefix in the **account-wide
artifacts bucket** (`[org-]cf-artifacts-<acct>-<region>-an`, module
`templates/v2/modules/account-wide/s3-artifacts-bucket.yml`).

Promotion artifacts want a **different, longer** retention than ordinary pipeline build
artifacts:

- **Desired for `promotions/*`:** current version never expires (it is the live deploy
  pointer / rollback source); noncurrent versions retained ~365 days (rollback window).
- **Existing bucket rule (`ExpireObjects`, empty filter, whole bucket):**
  `ExpirationInDays: 395` (current), `NoncurrentVersionExpirationInDays: 30`.

## The S3 limitation

S3 resolves **overlapping** lifecycle rules by applying the action that expires objects
**sooner**, and it offers **no way to exclude a prefix/tag** from a rule (filters are
include-only). See AWS docs:
<https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-conflicts.html>
(Examples 2–4: shorter/expiration action wins).

Consequences:
- Adding a `promotions/*`-scoped rule with 365-day noncurrent retention **does not work** —
  the empty-filter 30-day noncurrent rule still wins for those objects.
- You **cannot** give a sub-prefix *longer* retention than a whole-bucket empty-filter rule
  within the same bucket.

## Decision taken for spec 0-0-40 (Option 3)

To deliver a 365-day rollback window without introducing a second bucket (preserving the
"single account-wide bucket for both S3 source and artifact store" decision, R3a), the
spec:

1. **Raises the whole-bucket `NoncurrentVersionExpirationInDays` from 30 → 365.** This
   gives promoted archives a 365-day rollback window **but also retains noncurrent
   versions of all other build artifacts for 365 days** (a storage-cost tradeoff, accepted
   for now). Note: ordinary pipeline artifacts are largely written under unique keys, so
   noncurrent-version accumulation for non-promotion objects is expected to be modest.
2. **Keeps the whole-bucket `ExpirationInDays: 395` (current version) as-is.** This means
   current promotion objects **do expire at 395 days** — the "current promotion object
   never expires" intent is documented but **not honored** in practice. Impact is limited
   to a stage that has not received a promotion for 395 days losing its stable `source.zip`
   pointer, which a subsequent promotion re-creates.

## What a future spec should evaluate

1. **Dedicated promotions bucket** (e.g. `[org-]cf-promotions-<acct>-<region>-an`) with an
   independent lifecycle: current never expires, noncurrent retained N days. Cleanest
   correctness; also tightens security (a purpose-built bucket whose only cross-account
   access is promotion writes, separate from the general artifact store). Cost: the
   receiving pipeline references two buckets (S3 source vs. artifact store), reversing R3a.
2. **Per-object-tag lifecycle** if/when S3 gains practical tag-exclusion semantics, or by
   tagging *all* writers (including CodePipeline/CodeBuild artifacts) so ordinary and
   promotion objects can be split into mutually-exclusive tag-scoped rules.
3. **Revisit whether the whole-bucket noncurrent bump to 365 days** is causing meaningful
   storage cost, and whether ordinary artifacts should be split back to a shorter window.
4. **True "never expire" for the current promotion pointer** (requires isolating promotion
   objects from the 395-day current-version rule, i.e. option 1 above).

## References

- Spec: `.kiro/specs/0-0-40-pipeline-with-promotion-approval/` (design.md §7.3, requirements.md Requirement 12)
- Module: `templates/v2/modules/account-wide/s3-artifacts-bucket.yml`
- AWS S3 lifecycle conflict resolution: <https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-conflicts.html>
