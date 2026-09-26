# Design — v0.0.44 CloudFront Log Prefix Identity Segmentation

## 1. Overview

A single logical change applied in two places, both inside `templates/v2/network/template-network-route53-cloudfront-s3-apigw.yml`: insert `${Prefix}-${ProjectId}-${StageId}` immediately after the `cloudfront/` service prefix, for the v1 inline logging block and for the v2 delivery destination prefix. Supporting changes cover one output, one condition, the template comment, the README, tests, and the changelog.

Resulting layout in either logging bucket:

```
cloudfront/
  acme-orders-test/          <- Prefix-ProjectId-StageId
    E1ABCDEF2GHIJK.2026-09-25-14.a1b2c3d4.gz
  acme-orders-prod/
    E9ZYXWVU8TSRQP.2026-09-25-14.e5f6g7h8.gz
```

### 1.1 Why the account-wide stack needs no change

| Account-wide construct | Matcher | Matches `cloudfront/<identity>/…`? |
|---|---|---|
| Main bucket lifecycle rule `ExpireCloudFront` | `Filter.Prefix: cloudfront/` | yes |
| Main bucket policy `AllowCloudFrontV2LogDelivery` | `Resource: ${bucket.Arn}/cloudfront/*` | yes |
| Legacy bucket lifecycle rule `ExpireCloudFrontLegacy` | `Filter.Prefix: cloudfront/` | yes |
| Legacy bucket policy `AllowCloudFrontLegacyLogDelivery` | `Resource: ${bucket.Arn}/cloudfront/*` | yes |

Because the identity is inserted **after** the service prefix rather than before it, every matcher above is a prefix of the new key and continues to match. `account-wide-infrastructure.yml` and the `modules/s3-access-logs/*` files are untouched.

## 2. Change 1 — v1 inline logging prefix (R1)

In `CloudFrontDistribution.Properties.DistributionConfig`, the only edit is the `Prefix` line:

```yaml
        Logging: !If
          - HasV1Destination
          - IncludeCookies: 'false'
            Bucket: !Sub
              - "${LegacyBucket}.s3.amazonaws.com"
              - LegacyBucket: !If
                  - HasLogBucket
                  - !Ref S3LogBucketName
                  - Fn::ImportValue: !Sub "${OrgPrefix}-CloudFront-Legacy-Log-Bucket-Name"
            Prefix: !Sub "cloudfront/${Prefix}-${ProjectId}-${StageId}/"
          - !Ref AWS::NoValue
```

The trailing slash is explicit. CloudFront would append one anyway, but stating it keeps the value self-describing and matches the value reported by the `CloudFrontLogPrefix` output (§4). Nothing else in the block changes: `HasV1Destination`, the bucket resolution, and the `AWS::NoValue` fallback are all as-is.

## 3. Change 2 — v2 delivery destination prefix (R2)

In `CloudFrontDeliveryDestination`:

```yaml
      DestinationResourceArn: !Sub
        - "arn:${AWS::Partition}:s3:::${DestBucket}/cloudfront/${Prefix}-${ProjectId}-${StageId}"
        - DestBucket: !If
            - HasLogBucket
            - !Ref S3LogBucketName
            - Fn::ImportValue: !Sub "${OrgPrefix}-S3-AccessLog-Bucket-Name"
```

`${Prefix}`, `${ProjectId}`, and `${StageId}` resolve as ordinary template parameters alongside the `DestBucket` substitution variable; only `DestBucket` needs the explicit mapping entry. No trailing slash: the destination prefix is a path appended to the bucket ARN, and the delivery service supplies the separator for the remaining path segments.

`CloudFrontDeliverySource` and `CloudFrontDelivery` are unchanged.

> **Update behavior:** `DestinationResourceArn` updates require replacement, so an existing v2 stack replaces `CloudFrontDeliveryDestination` and, through the reference, `CloudFrontDelivery`. Both are stateless; expect a short delivery gap, not data loss.

## 4. Change 3 — `CloudFrontLogPrefix` output (R4)

Current state has two defects: the value is already `cloudfront/${Prefix}-${ProjectId}-${StageId}` (it was never updated when the prefix was flattened, so it reports a path that does not exist), and the `HasLogBucket` condition means the output disappears whenever the destination comes from the account-wide import rather than an explicit `S3LogBucketName`.

New condition, placed with the other CloudFront logging conditions after `CreateV2Delivery`:

```yaml
  HasCloudFrontLogging: !Or
    - !Condition HasV1Destination
    - !Condition CreateV2Delivery
```

Output:

```yaml
  CloudFrontLogPrefix:
    Condition: HasCloudFrontLogging
    Description: "The prefix used for CloudFront log files in the destination S3 bucket. Applies to both v1 and v2 logging."
    Value: !Sub "cloudfront/${Prefix}-${ProjectId}-${StageId}/"
```

This makes the value correct by construction for both modes and present exactly when logging is active. `CloudFrontLogBucket` keeps its `HasLogBucket` condition (out of scope per requirements §Non-goals 4).

## 5. Change 4 — corrected comment (R3)

The comment block above `CloudFrontDeliverySource` currently ends with an incorrect claim about the object key layout. Replace that sentence so it reads, in substance: the destination prefix on the delivery destination ARN sets the leading path of delivered objects and replaces the default `AWSLogs/<account>/<service>/` path, yielding keys under `cloudfront/<Prefix>-<ProjectId>-<StageId>/`. The preceding sentences describing the `CreateV2Delivery` gating are kept.

## 6. Documentation (R3)

`docs/templates/v2/network/template-network-route53-cloudfront-s3-apigw-README.md`:

1. **"v0.0.44 Changes (CloudFront logging v1/v2)" section** — replace "Objects land under the flat `cloudfront/` prefix" (v1 bullet) and the incorrect `cloudfront/AWSLogs/<account>/CloudFront/...` sentence (v2 bullet) with the shared `cloudfront/<Prefix>-<ProjectId>-<StageId>/` layout, and note that both modes now produce the same layout.
2. **`CloudFrontLogPrefix` output section** — update the example value to `cloudfront/myorg-webapp-prod/`, update the condition to `HasCloudFrontLogging`, and keep the existing explanation of service/ownership/stage organization, which now actually describes the implementation.
3. **`S3LogBucketName` parameter section** — no constraint changes; only the prose describing where logs land, if it references the flat prefix.
4. **Examples** — update Example 6's stated result (`prefix cloudfront/myorg-marketing-site-prod`) to include the trailing slash, and check Example 7 and any other example that names a log path.
5. Preserve all existing blockquotes, including the region-strategy note.

No category README change: the network category README does not describe log prefixes.

## 7. Tests (R5)

`tests/test_network_template_unit.py`:

- `test_logging_prefix_format` — remove the `isinstance(prefix_value, dict)` guard that currently lets every assertion be skipped (the property was a plain string after the prefix was flattened, so this test has been passing vacuously). Assert the `!Sub` form and the exact value `cloudfront/${Prefix}-${ProjectId}-${StageId}/`.
- `test_cloudfront_log_prefix_has_condition` — expect `HasCloudFrontLogging`.
- `test_cloudfront_log_prefix_value` — expect the trailing-slash value; drop the `isinstance` guard here as well.
- `test_cloudfront_log_bucket_and_prefix_consistency` (asserts both outputs share `HasLogBucket`) — split so the bucket output keeps `HasLogBucket` and the prefix output expects `HasCloudFrontLogging`.
- New `test_v2_delivery_destination_includes_identity_prefix` — assert `CloudFrontDeliveryDestination.Properties.DestinationResourceArn`'s `!Sub` template contains `/cloudfront/${Prefix}-${ProjectId}-${StageId}` and does not end with a slash.
- New `test_has_cloudfront_logging_condition_exists` — assert the condition is defined as an `!Or` over `HasV1Destination` and `CreateV2Delivery`.

`tests/test_network_template_property.py`:

- Update the expected v1 prefix in the existing property test to the new value and adjust its docstring. No new property-based tests (per `testing-guidelines.md`, unit tests carry this coverage).

## 8. Validation

1. `cfn-lint` the network template; no new findings.
2. `pytest tests/` fully green, with the previously vacuous prefix assertion now actually executing.
3. Confirm by inspection that no `templates/v2/account/**` or `templates/v2/modules/**` file needed modification (§1.1).

## 9. Requirements traceability

| Requirement | Design section |
|---|---|
| R1 v1 prefix | §2 |
| R2 v2 prefix | §3 |
| R3 corrected layout docs | §5, §6 |
| R4 `CloudFrontLogPrefix` output | §4 |
| R5 tests | §7, §8 |
| R6 versioning + changelog | tasks §1, §5 |
