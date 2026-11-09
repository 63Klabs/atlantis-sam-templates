# Design Document

**Spec:** v0.0.46 Network Template API Origin Protection

## Overview

This design implements [requirements.md](requirements.md) and the locked [PLAN.md](PLAN.md). It changes three source files and their tests and docs:

| File | Change |
|------|--------|
| `templates/v2/network/template-network-route53-cloudfront-s3-apigw.yml` | v0.1.0 to v0.2.0. Adds origin protection, rotation revision, viewer TLS parameter, and a Rules section. Deprecates four function parameters. |
| `templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml` | One new statement, `SecretsManagerOriginSecretRead`. |
| `templates/v2/modules/pipeline/cloudformation-svc-role.yml` | Two new statements for the deployment's own secrets. |

The two pipeline templates that include the pipeline module get a PATCH bump. No new resources are added to the network template, no custom origin request policy is created, and no output changes.

### Decisions that resolve the open items in requirements.md

| # | Open item | Decision | Evidence |
|---|-----------|----------|----------|
| D1 | `Comment` format with a revision | `${Prefix}-${ProjectId}-${StageId} rev ${ApiOriginSecretRevision}`. Empty revision keeps `${Prefix}-${ProjectId}-${StageId}`. | Verified 2026-11-08 on a temporary stack: the Comment changed and the secret was re-resolved. Longest value is 8 + 26 + 8 + 2 hyphens + 5 + 32 = 81 characters, under the 128-character limit. |
| D2 | Four origin-event conditions | Remove `HasStaticFunctionOriginRequest`, `HasStaticFunctionOriginResponse`, `HasApiFunctionOriginRequest`, and `HasApiFunctionOriginResponse`. | After the associations go, nothing references them. `cfn-lint` already reports unused conditions as W8001 warnings (two exist today); leaving four more adds noise. No stack imports a template condition. |
| D3 | `cfn-lint` and the 2025 TLS values | No upgrade and no ignore needed. | `cfn-lint` 1.51.4 in `.venv` passed a distribution using all eight allowed values with exit code 0. |
| D4 | Ingress page location | `docs/end-user/api-ingress-standard.md`. | `docs/end-user/README.md` exists; the page serves adopters. |
| D5 | Managed policy `Description` | Do not change the `Description` property of the network management policy. Update only the module comment block (Requirement 4.4). | `AWS::IAM::ManagedPolicy` `Description` updates require replacement. A replacement would detach and recreate the policy for every prefix on the next service-role stack update. |
| D6 | `Rules` placement | After `Conditions`, before `Resources`, as in `account-wide-infrastructure.yml:363`. | Existing precedent. |
| D7 | Dynamic reference built with `Fn::Sub` | Use `!Sub '{{resolve:secretsmanager:${Prefix}-${ProjectId}-${StageId}-OriginSecret}}'`. | Verified on a temporary stack with `Transform: AWS::Serverless-2016-10-31`: the header resolved to the secret, and with the condition false `OriginCustomHeaders` produced zero headers. |
| D8 | IAM size limits | No change needed, but add a size guard test. | Measured: the deployed network policy is 3,519 of 6,144 characters; the pipeline CloudFormation role inline policy is about 8,375 of 10,240 characters with the new statements (headroom about 1,900). |

## Network Template Design

All snippets use the template's existing style (short-form intrinsics, two-space indent).

### Metadata groups

Add a group after `Routing for API Gateway` and before the deprecated forwarding group. Add the TLS parameter to `Routing for CloudFront`.

```yaml
      - Label:
          default: Routing for CloudFront
        Parameters:
          - DomainForCloudFront
          - CustomSubdomainCloudFront
          - PathStatic
          - AcmCertificateArnForCloudFront
          - ViewerMinimumTlsVersion

      # ... Routing for API Gateway unchanged ...

      - Label:
          default: API Origin Protection
        Parameters:
          - ApiOriginProtection
          - ApiOriginSecretRevision
```

The deprecated function parameters stay in their current groups.

### Parameters

Add `ViewerMinimumTlsVersion` after `AcmCertificateArnForCloudFront` in the CloudFront routing section. Add a new subsection `API Origin Protection` after the API Gateway routing parameters and before `Forwarding for API Gateway behind CloudFront`.

```yaml
  ViewerMinimumTlsVersion:
    Type: String
    Description: "Minimum TLS version (CloudFront security policy) for viewers. Applies only when the
      distribution has a custom domain and ACM certificate (DomainForCloudFront, CustomSubdomainCloudFront,
      and AcmCertificateArnForCloudFront); the default CloudFront domain is fixed at TLSv1 by CloudFront.
      The default TLSv1.2_2021 stops clients that cannot negotiate TLS 1.2 from connecting. Set TLSv1 to
      keep the behavior of earlier template versions."
    Default: TLSv1.2_2021
    AllowedValues:
      - TLSv1
      - TLSv1_2016
      - TLSv1.1_2016
      - TLSv1.2_2018
      - TLSv1.2_2019
      - TLSv1.2_2021
      - TLSv1.2_2025
      - TLSv1.3_2025
    ConstraintDescription: Must be a CloudFront viewer security policy name.

  ApiOriginProtection:
    Type: String
    Description: "Set to 'true' to have CloudFront add the X-Atlantis-Origin-Secret header to every request
      it sends to the API Gateway origin. The value comes from the Secrets Manager secret named
      <Prefix>-<ProjectId>-<StageId>-OriginSecret, which must exist in this region before the stack is
      created or updated with 'true'. The application must reject requests whose header does not match.
      Requires an API Gateway behind CloudFront (ApiGatewayId set, DomainForApiGateway empty)."
    Default: "false"
    AllowedValues: ["true", "false"]
    ConstraintDescription: Must be 'true' or 'false'.

  ApiOriginSecretRevision:
    Type: String
    Description: "Optional label used to roll a rotated origin secret out to the distribution.
      Updating only the secret does not change the distribution, so CloudFormation does not read the
      new value. After you rotate the secret, change this value (for example r2, r3) and update the stack.
      Leave empty until the first rotation."
    Default: ""
    AllowedPattern: "^[a-zA-Z0-9.-]{0,32}$"
    ConstraintDescription: Up to 32 characters; letters, numbers, dots, and dashes.
```

The four deprecated function parameters keep their `Type`, `Default`, `AllowedPattern`, and `ConstraintDescription`. Only the `Description` changes, for example:

```yaml
  CloudFrontStaticFunctionOriginRequest:
    Type: String
    Description: "DEPRECATED - ignored. CloudFront Functions run only on viewer-request and viewer-response
      events, so a function cannot be associated with the origin-request event on static behaviors.
      Retained so existing stacks that pass it still update."
```

The descriptions keep the words "static" or "API" because `TestCloudFrontFunctionParameters` checks them.

### Conditions

```yaml
  # API Origin Protection
  UseApiOriginProtection: !And
    - !Equals [!Ref ApiOriginProtection, "true"]
    - !Condition ApiIsBehindCloudFront
  HasApiOriginSecretRevision: !Not [!Equals [!Ref ApiOriginSecretRevision, ""]]
```

Delete the four origin-event conditions (D2). The viewer-event conditions stay.

### Rules

```yaml
# =============================================================================
# RULES
# -----------------------------------------------------------------------------
# https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/rules-section-structure.html
#

Rules:
  ApiOriginProtectionRequiresApiBehindCloudFront:
    RuleCondition: !Equals [!Ref ApiOriginProtection, "true"]
    Assertions:
      - Assert: !And
          - !Not [!Equals [!Ref ApiGatewayId, ""]]
          - !Equals [!Ref DomainForApiGateway, ""]
        AssertDescription: "ApiOriginProtection 'true' requires ApiGatewayId to be set and DomainForApiGateway to be empty (an API Gateway behind CloudFront)."
```

The Rule uses parameter values only, as Rules require. The `UseApiOriginProtection` condition repeats the check so that a stack never emits the header when no API origin exists, even if the Rule is bypassed.

### Resources: `CloudFrontDistribution`

**Comment (D1):**

```yaml
        Comment: !If
          - HasApiOriginSecretRevision
          - !Sub "${Prefix}-${ProjectId}-${StageId} rev ${ApiOriginSecretRevision}"
          - !Sub "${Prefix}-${ProjectId}-${StageId}"
```

**API origin (D7):** add `OriginCustomHeaders` to the existing `ApiGatewayOrigin` entry, beside `CustomOriginConfig`.

```yaml
              OriginCustomHeaders: !If
                - UseApiOriginProtection
                - - HeaderName: X-Atlantis-Origin-Secret
                    HeaderValue: !Sub '{{resolve:secretsmanager:${Prefix}-${ProjectId}-${StageId}-OriginSecret}}'
                - !Ref AWS::NoValue
```

The reference is versionless. A header named `X-Atlantis-Origin-Secret` is allowed by CloudFront (not on its blocked list) and overwrites a viewer-sent header of the same name.

**Viewer certificate:**

```yaml
        ViewerCertificate:
          CloudFrontDefaultCertificate: !If [ CreateDnsRecordForCloudFront, !Ref AWS::NoValue, true]
          AcmCertificateArn: !If [ CreateDnsRecordForCloudFront, !Ref AcmCertificateArnForCloudFront, !Ref AWS::NoValue ]
          MinimumProtocolVersion: !If [ CreateDnsRecordForCloudFront, !Ref ViewerMinimumTlsVersion, !Ref AWS::NoValue ]
          SslSupportMethod: !If [ CreateDnsRecordForCloudFront, 'sni-only', !Ref AWS::NoValue ]
```

With a custom domain the value changes from the implicit `TLSv1` to `TLSv1.2_2021`. This is an in-place update ("No interruption" per the CloudFormation reference) and is the one intended behavior change.

**Function associations (Requirement 7.3):** each of the four `FunctionAssociations` lists keeps only its viewer-request and viewer-response items. The lists are:

- DefaultCacheBehavior static branch and API branch (`!If [StaticOriginIsRoot, static, api]`).
- The static path behavior (`HasRouteForStaticOrigin`).
- The API path behavior (`HasRouteForApiInCloudFront`).

Example, the default behavior API branch after the change:

```yaml
              - - !If
                  - HasApiFunctionViewerRequest
                  - EventType: viewer-request
                    FunctionARN: !Ref CloudFrontApiFunctionViewerRequest
                  - !Ref AWS::NoValue
                - !If
                  - HasApiFunctionViewerResponse
                  - EventType: viewer-response
                    FunctionARN: !Ref CloudFrontApiFunctionViewerResponse
                  - !Ref AWS::NoValue
```

If a stack still passes a function ARN for an origin event it is accepted and ignored. Setting it could not have worked before (CloudFormation documents origin-facing event types as unsupported for CloudFront Functions).

**Unchanged:** both `OriginRequestPolicyId` values (`b689b0a8-53d0-40ab-baf2-68738e2966ac`), cache policies, logging, aliases, tags, and all outputs.

### Header comment

Only version and date change: `# Version: v0.2.0/<YYYY-MM-DD of the change>` (steering rule). Add the `Rules` section comment block. Do not edit other header comments.

### Update behavior

| Change | Existing stack, defaults | Effect |
|--------|--------------------------|--------|
| `OriginCustomHeaders` | `ApiOriginProtection="false"` | `AWS::NoValue`, no change |
| `Comment` | revision empty | identical value, no change |
| `FunctionAssociations` | no origin-event ARN set | identical list, no change |
| `MinimumProtocolVersion` | custom domain | `TLSv1` to `TLSv1.2_2021`, in-place update. Operators set `TLSv1` to avoid it. |
| `Rules`, new parameters, removed conditions | any | no resource effect |

Enabling protection or changing the revision is an in-place distribution update. Verified on 2026-11-08: the update completed in 49 seconds and the origin received the new value.

## Management Policy Module Design

File: `templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml`. Add after `AcmCertificateRead`:

```yaml
      # ------------------------------------------------------------------
      # Origin Secret Read (for ApiOriginProtection)
      # ------------------------------------------------------------------
      # With ApiOriginProtection='true' the network template sets an origin
      # header from {{resolve:secretsmanager:<Prefix>-<ProjectId>-<StageId>-OriginSecret}}.
      # CloudFormation resolves it with THIS role's identity at stack create/update,
      # so the role needs GetSecretValue on the convention-named secret.
      # Secrets Manager appends a six-character suffix to the secret ARN.
      - Sid: SecretsManagerOriginSecretRead
        Effect: Allow
        Action:
          - secretsmanager:GetSecretValue
        Resource:
          - Fn::Sub: "arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${Prefix}-*-OriginSecret-??????"
```

Notes:

- Long-form `Fn::Sub` only (module rule). The module already requires `Prefix`; no new parameters or conditions.
- Add a line to the module comment block: the policy also lets the service role read the origin secret for `ApiOriginProtection`. Leave the `Description` property unchanged (D5).
- Verified 2026-11-08: the same statement, applied to the XCME role, let the network stack resolve the secret, and a secret not matching `-OriginSecret` was denied.
- The module is included by `prefix-based-infrastructure.yml`, `template-service-role-network-cloudfront.yml`, and `template-service-role-network-full.yml`. None of these needs a code change. They pick up the module at their next update.
- Size: 3,711 of 6,144 characters after the change (D8).

## Pipeline Role Module Design

File: `templates/v2/modules/pipeline/cloudformation-svc-role.yml`. Add after `SsmParameterCRUDThisDeploymentOnly`, matching its indentation and style:

```yaml
          - Sid: SecretsManagerCRUDThisDeploymentOnly
            Action:
              - secretsmanager:CreateSecret
              - secretsmanager:UpdateSecret
              - secretsmanager:DeleteSecret
              - secretsmanager:PutSecretValue
              - secretsmanager:DescribeSecret
              - secretsmanager:TagResource
              - secretsmanager:UntagResource
            Effect: Allow
            Resource:
              Fn::Sub: arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${Prefix}-${ProjectId}-${StageId}-*
          # GetRandomPassword has no resource type; it is needed for GenerateSecretString
          - Sid: SecretsManagerGetRandomPassword
            Action:
              - secretsmanager:GetRandomPassword
            Effect: Allow
            Resource: "*"
```

Notes:

- No `GetSecretValue`: verified 2026-11-08 that a stack using this role to resolve the secret value fails with `AccessDenied`, while create, update (including tags), and delete succeed.
- `GetRandomPassword` was present throughout the test, so whether `GenerateSecretString` strictly needs it is not isolated. Keep it (Decision 8).
- The module comment block lists required parent parameters; no new ones are needed (`Prefix`, `ProjectId`, `StageId` already exist).
- Template impact: `template-pipeline.yml` v2.0.23 becomes v2.0.24 and `template-pipeline-github.yml` v2.0.5 becomes v2.0.6, each with the date of the change. `template-pipeline-s3-source.yml` also includes the module and is bumped from v2.0.0 to v2.0.1 (PATCH bump, dated). `template-pipeline-build-only.yml` does not include this module.
- Rollout: the role is created by each pipeline stack, so an application gets the statement at its next pipeline stack update, not at the service-role update.
- Size: the inline policy grows to about 8,375 of 10,240 characters, using worst-case test values (D8). Rendered ARNs with real values are slightly longer, so the guard test below uses maximum-length parameters.

## Test Design

All new tests are fast unit tests (testing guidelines). They load templates with `tests.cfn_test_utils.load_template` and follow the style of the existing files.

### `tests/test_network_template_unit.py` (changes)

| Existing test or list | Change |
|----------------------|--------|
| `test_template_version_is_v0_1_0` (line ~2564) | Rename and expect `# Version: v0.2.0/` |
| `ALL_CONDITIONS`, `STATIC_CONDITIONS`, `API_CONDITIONS`, `CONDITION_TO_PARAM` (lines ~2086-2127) | Keep only the four viewer conditions. Replace the `zip(ALL_CONDITIONS, ALL_FUNCTION_PARAMS)` mapping, which depends on the old ordering, with an explicit dictionary of condition to parameter |
| `EVENT_TYPES` and the tests `test_static_branch_event_types`, `test_api_branch_event_types`, `test_static_path_event_types`, `test_api_path_event_types` | Expect `['viewer-request', 'viewer-response']` |
| `test_static_branch_has_4_items`, `test_api_branch_has_4_items`, `test_static_path_has_4_items`, `test_api_path_has_4_items` | Expect 2 items; rename |
| `test_*_references_*_params`, `test_*_uses_*_conditions`, `test_no_*_refs_*` | Expect only viewer parameters and conditions |
| `TestCloudFrontFunctionParameters` (all 8 parameters) | Unchanged; the pattern, type, default, and description tests still pass because the descriptions keep "static" and "API" |
| `TestCloudFrontFunctionMetadataGroups` | Unchanged (groups still hold all four parameters) |
| `TestCloudFrontFunctionConditions` | Check the four viewer conditions exist; add a test that the four origin conditions are absent |

New test classes in the same file:

- `TestApiOriginProtectionParameter`: type, default `"false"`, allowed values, description names the secret and the header.
- `TestApiOriginProtectionMetadata`: group `API Origin Protection` exists, contains both parameters, sits after `Routing for API Gateway` and before the deprecated forwarding group.
- `TestApiOriginProtectionCondition`: `UseApiOriginProtection` is an `!And` of the toggle and `ApiIsBehindCloudFront`.
- `TestApiOriginProtectionRule`: `Rules` section exists with the named rule, rule condition, assertion, and a non-empty `AssertDescription`.
- `TestOriginCustomHeaders`: `ApiGatewayOrigin` entry has `OriginCustomHeaders` as `!If [UseApiOriginProtection, [one header], NoValue]`; header name; the `!Sub` string equals `{{resolve:secretsmanager:${Prefix}-${ProjectId}-${StageId}-OriginSecret}}`; no `:` version segments; no other origin carries the property; no secret or reference in `Outputs`.
- `TestApiOriginSecretRevision`: parameter default `""`, pattern, max length; `Comment` is `!If [HasApiOriginSecretRevision, ...]` with the exact strings from D1.
- `TestViewerMinimumTlsVersion`: default `TLSv1.2_2021`, the eight allowed values in order, group `Routing for CloudFront`, `MinimumProtocolVersion` is `!If [CreateDnsRecordForCloudFront, !Ref ViewerMinimumTlsVersion, NoValue]`.
- `TestApiOriginRequestPolicyUnchanged`: the default behavior and API path behavior still use `b689b0a8-53d0-40ab-baf2-68738e2966ac`; `Resources` has no `AWS::CloudFront::OriginRequestPolicy`.
- `TestDeprecatedFunctionParameters`: all four descriptions start with `DEPRECATED`, parameters keep default `""` and pattern, and no `origin-request` or `origin-response` string appears under any `FunctionAssociations`.

### `tests/test_network_template_property.py`

Update only the list that includes the origin parameters if a test depends on the removed conditions. The ARN-pattern property for all eight parameters stays valid. No new property tests.

### `tests/test_network_cloudfront_mgmt_policy_unit.py` (additions)

`TestSecretsManagerOriginSecretRead`: statement exists; `Effect` is `Allow`; `Action` is exactly `secretsmanager:GetSecretValue`; the resource is a `Fn::Sub` string equal to the pattern in the design; `CloudFrontOriginRequestPolicyRead` still has exactly its three read actions; no statement contains `CreateOriginRequestPolicy`, `UpdateOriginRequestPolicy`, or `DeleteOriginRequestPolicy`; existing tests unchanged.

### New file `tests/test_pipeline_cfn_svc_role_secrets_unit.py`

- Locate the two statements by `Sid` in `cloudformation-svc-role.yml`; assert exact action lists, `Effect`, resource strings, `GetRandomPassword` on `"*"`, and that no statement allows `secretsmanager:GetSecretValue`.
- Size guard (D8): render the statement list by replacing every `${Name}` in each `Fn::Sub` with a worst-case-length string (`Prefix` 8, `ProjectId` 26, `StageId` 8, region 14, account 12, other variables 20), remove whitespace, and assert the total is under 10,240 characters, which is the per-role inline policy limit. This guards future additions to a policy that is already near the limit.
- Assert `# Version: v2.0.24/` in `template-pipeline.yml`, `# Version: v2.0.6/` in `template-pipeline-github.yml`, `# Version: v2.0.1/` in `template-pipeline-s3-source.yml`, and that `template-pipeline-build-only.yml` still reads `v2.0.7`.

### Template validation

`tests/test_cfn_templates.py` and `cfn_linter` validate every template and module for errors. The baseline has only warnings on the network template (two W8001, two W1001 pairs, W1028). The change must introduce no new error. Expected net effect: no new warnings; the removed conditions are not among the existing warnings.

### Release check (Requirement 13.1)

Not automatable in unit tests: create a change set of the new network template against a stack deployed from v0.1.0 with `ApiOriginProtection="false"`, an empty revision, and `ViewerMinimumTlsVersion="TLSv1"`. It must show no resource changes. A second change set with the default TLS value must show only the `Distribution` modification for `MinimumProtocolVersion`. Record the stack and result in the changelog PR notes.

## Documentation Design

| File | Change |
|------|--------|
| `docs/templates/v2/network/template-network-route53-cloudfront-s3-apigw-README.md` | Update header version to v0.2.0 and date. New parameter group section with `ApiOriginProtection` and `ApiOriginSecretRevision` (table form per steering), `ViewerMinimumTlsVersion` under CloudFront routing, `DEPRECATED` notes on the four function parameters, a `Rules` section, the `OriginCustomHeaders` description under `CloudFrontDistribution`, updated conditions list, new management-statement text where the README lists the network role's statements, deployment order, rotation steps, troubleshooting (`AccessDenied` on `secretsmanager:GetSecretValue`, secret not found, rotation not applied, 403 rewrite), version history entry, link to the ingress page. Preserve every existing blockquote. |
| `docs/end-user/api-ingress-standard.md` (new) | Content list from Requirement 11.2. Include the verified numbers and the REST-only caveat. Link back to the network README. |
| `docs/README.md`, `docs/end-user/README.md` | Add links to the ingress page. |
| `docs/templates/v2/network/README.md` | Version and summary update for the network template. |
| `docs/templates/v2/pipeline/template-pipeline-README.md`, `template-pipeline-github-README.md` | Add the two new CloudFormation role statements to the `CloudFormationSvcRole` permissions list (near line 619), and the version bump. |
| `docs/templates/v2/pipeline/template-pipeline-s3-source-README.md` | Add the two statements and update the version header to v2.0.1. |
| `docs/templates/v2/pipeline/README.md` | Version references for the three bumped templates. |
| `CHANGELOG.md` | Entries under `## v0.0.46 (unreleased)` only, in Added, Changed, Deprecated, and Breaking Changes, with the update-time notes from Requirement 12.3. Link the spec. |

The ingress page documents the verified client-IP behavior as follows, with its scope stated:

| API type behind the distribution | `identity.sourceIp` | `CloudFront-Viewer-Address` | `X-Forwarded-For` |
|-------------------------------|---------------------|------------------------------|-------------------|
| Regional (REST, verified) | True viewer address | Present, true address, viewer cannot override | Viewer-sent value is kept as the left entries |
| Edge-optimized (REST, verified) | An edge address | Dropped | `viewer, edge, edge` |
| HTTP API, IPv6 viewers | Not tested | Not tested | Not tested |

## Error Handling and Failure Modes

| Situation | Behavior |
|-----------|----------|
| `ApiOriginProtection="true"` and no API behind CloudFront | The Rule fails the stack create or update with its `AssertDescription` before any resource change. |
| Secret does not exist | Stack create or update fails at the distribution with a resolution error. No partial change to the distribution on update. |
| Service role lacks `GetSecretValue` | Fails with `AccessDeniedException` naming the role and the secret. Troubleshooting entry points to the service-role update. |
| Secret rotated, revision unchanged | The distribution keeps the old value. Documented in the parameter description and rotation steps. |
| Secret deleted after deployment | The distribution keeps sending the last resolved value. The next stack update fails until the secret is restored. |
| Application stack role lacks the new statements | Creating the secret fails with `AccessDenied`. Documented fix: update the pipeline stack. |
| `ApiOriginSecretRevision` outside the pattern | Rejected at parameter validation. |

## Security Considerations

- The secret value is present in the CloudFront configuration. Any principal with `cloudfront:GetDistribution` or `GetDistributionConfig` can read it. It is not present in CloudFormation metadata (verified).
- `GetSecretValue` is scoped to `${Prefix}-*-OriginSecret-??????` for the network role. The pipeline role cannot read secret values, only create and manage secrets named for its own deployment.
- The pipeline role statement lets a deployment create any secret named `${Prefix}-${ProjectId}-${StageId}-*`. It cannot touch another deployment's secrets.
- Constant-time comparison, no logging of the header, and rejection on a missing configured secret are application duties, stated in the ingress page.
- No exploit detail is added; the bypass is already described in the public issue.

## Rollout and Rollback

Order for adopters (documented in the README and changelog):

1. Update the service role (`prefix-based-infrastructure`, `template-service-role-network-cloudfront`, or `template-service-role-network-full`) so it holds `SecretsManagerOriginSecretRead`.
2. Update the pipeline stack to pick up the Secrets Manager statements.
3. Deploy the application stack that creates `${Prefix}-${ProjectId}-${StageId}-OriginSecret` with `GenerateSecretString`.
4. Update the network stack with `ApiOriginProtection="true"`.
5. Turn on enforcement in the application, accepting old and new values during any later rotation.

Rollback: set `ApiOriginProtection="false"` to remove the header (application should stop enforcing first). Returning to template v0.1.0 also reverts the TLS default. Removing the new IAM statements is safe once no stack uses protection.

## Task Ordering (input to tasks.md)

1. Version management: network template v0.2.0 header; pipeline templates PATCH bumps (steering requires the version task first).
2. Network template: parameters and metadata, conditions, Rules, distribution changes, deprecations.
3. Management policy module and pipeline role module.
4. Tests (update existing, then add new), run `pytest` and `cfn-lint`.
5. Docs: network README, ingress page, pipeline READMEs, category READMEs.
6. CHANGELOG entry.
7. Release check: change sets (Requirement 13.1) and confirm the test account has no leftover test grants (Requirement 13.2).

The core feature (items 2 to 3 for origin protection, with docs and tests) can ship independently of the TLS parameter and the function-parameter deprecation if the schedule requires it.
