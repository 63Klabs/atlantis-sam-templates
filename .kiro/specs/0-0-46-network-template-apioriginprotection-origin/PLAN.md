# Network template: ApiOriginProtection (origin secret header for API origins)

> **Status**: Locked 2026-11-08 (reopened after runtime verification and re-locked the same day; stripping policy dropped, Decision 10)
> **Verification note (2026-11-08)**: runtime checks in account 458901159113 / us-east-2 showed the managed policy already delivers `CloudFront-Viewer-Address` and viewers cannot spoof it. The stripping policy and its management-role statement were dropped (Decision 10). Results in [Section 2.1](#21-runtime-verification-results-2026-11-08).
> **Issue**: [ISSUE.md](ISSUE.md) (GitHub #10)
> **Reviewed against**: `dev` at `a79a109` (v0.0.45 release) on 2026-11-08. Working tree has only the unreleased `v0.0.46` CHANGELOG header and the untracked spec folders for #9 and #10.
> **Related plan**: [#9 PLAN.md](../0-0-46-network-template-forward-cloudfront-viewer/PLAN.md) (re-locked). Its stripping hand-off (its Decision 6) is withdrawn; #9 closes as already satisfied on Regional APIs.

## 1. Summary

The network template protects its S3 origin with an Origin Access Control but has no equivalent for the API Gateway origin. The distribution reaches the API through the default `execute-api` endpoint, so anyone can call that endpoint directly and skip the distribution's caching and any attached web ACL. The issue proposes an opt-in `ApiOriginProtection` parameter. When `"true"`, CloudFront adds an `X-Atlantis-Origin-Secret` origin header whose value comes from a Secrets Manager secret named `${Prefix}-${ProjectId}-${StageId}-OriginSecret` through a dynamic reference. The application accepts requests only when the header matches. CloudFront overwrites any viewer-sent header of the same name.

The design is sound and fits the template. Review found these items the issue does not cover:

1. **Rotation does not work as written.** AWS states that updating only a Secrets Manager secret does not make CloudFormation fetch the new value; the value is retrieved only when a stack operation modifies the resource that holds the reference. The issue's rotation step "update the distribution" needs a deliberate change to the distribution (Q2).
2. **The application-side permission is missing.** The issue's deployment order has the application stack create the secret first. The pipeline CloudFormation service role has no Secrets Manager permission at all (Q3).
3. **Four extra items are bundled into the issue** (TLS minimum version, origin-event function parameters, error-response documentation) (Q1). A stripping policy for a client-sent `CloudFront-Viewer-Address` was handed over from #9 and then dropped after runtime checks showed the header is already delivered and cannot be spoofed (Decision 10).
4. **A 403 from the application is rewritten by the distribution** whenever a static origin exists, because the 403 and 404 custom error responses apply to the whole distribution. If the application rejects a bad secret with 403, viewers of a mixed static and API site see `index.html` with status 200 instead (Section 4.3).

Decided shape (Q1 to Q9, Decision 10): implement `ApiOriginProtection` with a rotation-revision parameter and a rule that rejects the toggle when no API sits behind CloudFront. Add the TLS parameter and deprecate the four origin-event function parameters. Add a read statement for the origin secret to the network management policy and a create-and-manage-only Secrets Manager statement to the pipeline CloudFormation role. Document edge-optimized APIs instead of refusing them. No stripping policy and no new origin request policy resource. Runtime checks V1 to V5, V7, and V8 passed; V6 runs during implementation.

## 2. Assessment of the issue

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| 1 | The S3 origin is protected by OAC, the API origin has no equivalent | Confirmed | `CloudFrontOriginAccessControl` (`templates/v2/network/template-network-route53-cloudfront-s3-apigw.yml`, `Condition: HasStaticOrigin`) is referenced by the S3 origin. The API origin block (lines ~697-709) has no `OriginCustomHeaders`. |
| 2 | The template cannot disable the default endpoint because the distribution's origin is that endpoint | Confirmed | Origin `DomainName: ${ApiGatewayId}.execute-api.${AWS::Region}.amazonaws.com` (line ~697). Template takes only an API ID. |
| 3 | CloudFront overwrites a viewer-sent header of the same name | Confirmed (AWS docs) | CloudFront "Add custom headers to origin requests": a header already present in the viewer request has its value overwritten. `X-Atlantis-Origin-Secret` is not on the list of headers CloudFront refuses to add (`X-Amz-*`, `X-Edge-*`, `X-Real-Ip`, `Via`, `Host`, and others). |
| 4 | A `{{resolve:secretsmanager:...}}` reference is accepted in `HeaderValue` and the value stays out of `describe-stacks`, events, and the stored template | Confirmed (V2) | AWS: the reference can be used in all resource properties, and CloudFormation and Secrets Manager do not persist the resolved value, but the value "may show up in the service whose resource it's being used in." Reporter measured the rest on 2026-11-09. The CloudFront configuration holds the value in the clear (Section 4.1). Reproduced on 2026-11-08 with the SAM transform and a Rules block (Section 2.1). |
| 5 | A value change reached the edge about a minute after the update began; CloudFormation finished at about two minutes | Consistent with V4 | Reporter measurement. CloudFront propagation is variable; rotation steps must wait for `Deployed` plus a margin, as the issue says. |
| 6 | The pipeline's CloudFormation service role needs a permission to resolve the reference (open point) | Confirmed, issue misdirected (V1) | The network stack is deployed with the network service role, not a pipeline role: `${PrefixUpper}-CloudFormation-Service-Role-Network-CloudFront-Mgmt` (`templates/v2/modules/management-roles/network-cloudfront-mgmt-role.yml`). AWS: the caller needs `secretsmanager:GetSecretValue`. CloudFormation resolves with the service role's identity: the XCME network role failed with `AccessDenied` on `GetSecretValue` (Section 2.1). |
| 7 | Rotation: accept both values in the application, update the distribution, wait for `Deployed` plus margin, remove the old value | Partially confirmed | AWS: updating only the secret does not make CloudFormation re-resolve it; the resource containing the reference must be modified (`dynamic-references-secretsmanager`). The issue does not say how to force a modification (Q2). |
| 8 | Management-role permission needed: `secretsmanager:GetSecretValue` on the convention-named secret; spec 0-0-38 is the precedent | Confirmed | `network-cloudfront-mgmt-policy.yml` has no Secrets Manager statement (`grep secretsmanager templates/` finds nothing). `0-0-38-network-cloudfront-mgmt-policy-gaps` added statements to the same file and tests in `tests/test_network_cloudfront_mgmt_policy_unit.py`. |
| 9 | Deployment order: application stack creates the secret, then the network stack, then the application enforces | Partially confirmed | Feasible only if the application stack's CloudFormation role may create a secret. `templates/v2/modules/pipeline/cloudformation-svc-role.yml` has no Secrets Manager statement (Q3). |
| 10 | `ViewerMinimumTlsVersion` (default `TLSv1.2_2021`): current distributions with a custom domain and `sni-only` use `TLSv1` | Confirmed (V7) | `ViewerCertificate` (lines 903-906) sets no `MinimumProtocolVersion`. AWS says a value is required with an ACM certificate; the omitted-value default is not stated on the page I could read. Needs `aws cloudfront get-distribution-config` on a deployed stack. Without an alias, CloudFront fixes the policy at `TLSv1` regardless of the setting, as the issue notes. Allowed values include `TLSv1.2_2021`, `TLSv1.2_2025`, and `TLSv1.3_2025`. |
| 11 | The four origin-request and origin-response function parameters take CloudFront Function ARNs, but CloudFront Functions run only on viewer events | Confirmed | CloudFormation `FunctionAssociation` docs: origin-facing event types cannot be used with a CloudFront function. The parameters are at lines 280-323 and wired into `FunctionAssociations` for the default and API path behaviors. Tests list them (`tests/test_network_template_unit.py:2092-2115`, `tests/test_network_template_property.py:1592-1596`). Setting any of them probably fails the deploy today. |
| 12 | The distribution-wide 403 and 404 `CustomErrorResponses` also apply to API responses when a static origin exists | Confirmed | `CustomErrorResponses` is under `Condition HasStaticOrigin` and not scoped to a behavior (lines ~882-896): 403 and 404 map to `/index.html` with 200. |
| 13 | With the default `"false"`, the new property resolves to `AWS::NoValue` and an existing stack shows no change set | Confirmed as feasible for the protection feature | The template already uses `!If [...] AWS::NoValue` for optional properties. The bundled TLS default (`TLSv1.2_2021`, Q1 A) does change existing custom-domain distributions on their next update, which the issue itself acknowledges as the one behavior change. The rotation parameter defaults to empty so the `Comment` is unchanged, and the stripping policy was dropped (Decision 10). |
| 14 | Documentation to update includes "the promotion integration test" | Not confirmed | `docs/maintainer/promotion-integration-test.md` covers promotion pipelines and does not mention network or CloudFront. Probably a copy error. Proposed: drop it. |
| 15 | A third party's distribution cannot present the secret; the header reaches both edge-optimized and Regional APIs | Reporter-measured | By design a third party cannot read the secret. The edge-optimized and Regional delivery are reporter measurements. |

Not stated in the issue:

- The Rules section does not exist in the network template. A `Rules:` block is new for this file, and `account-wide-infrastructure.yml:363` is the only precedent in the repository.
- The mgmt policy module is consumed by three templates: `templates/v2/account/prefix-based-infrastructure.yml`, `templates/v2/service-role/template-service-role-network-cloudfront.yml`, and `template-service-role-network-full.yml`. A policy change requires redeploying whichever one the admin uses.
- The secret value lives in the CloudFront distribution configuration. `cloudfront:GetDistribution` and `GetDistributionConfig` (granted by `CloudFrontDistributionCRUD` and to any admin or read-only role in the account) expose it.

### 2.1 Runtime verification results (2026-11-08)

Run with `--profile release` (account `458901159113`, `us-east-2`) on temporary stacks named `xcme-zz-ingress-test-*`: a Secrets Manager secret, two mock REST APIs (one Regional, one edge-optimized) that echo request headers, and a CloudFront distribution with a `*.cloudfront.net` domain. Templates were kept outside the repository (`/tmp/ingress-verify/`). All stacks, the distribution, the policy, the APIs, and the secret were deleted afterward and a leftover search found nothing.

| # | Result | Evidence |
|---|--------|----------|
| V1 | **Pass.** CloudFormation resolves the reference with the **service role's** identity, and the planned statement works. | Without the statement the XCME network role failed: `...assumed-role/XCME-CloudFormation-Service-Role-Network-CloudFront-Mgmt/AWSCloudFormation is not authorized to perform: secretsmanager:GetSecretValue on resource: xcme-zz-ingress-test-OriginSecret`. With `secretsmanager:GetSecretValue` on `arn:aws:secretsmanager:us-east-2:458901159113:secret:xcme-*-OriginSecret-??????` the same stack created, and the origin received the resolved secret. A secret whose name does not match the pattern (`xcme-zz-ingress-test-Other`) was denied. |
| V2 | **Pass.** | With `Transform: AWS::Serverless-2016-10-31` and a `Rules` block, the 32-character secret value appeared 0 times in `describe-stacks`, events, resources, resource detail, the original template, and the processed template. Only the `{{resolve:...}}` text appears. The value is present in the CloudFront configuration (`get-distribution-config`), as the plan expects. |
| V3 | **Pass.** | A viewer-sent `X-Atlantis-Origin-Secret: fakevalue` reached both the Regional and edge-optimized API as the real secret. A direct call to either `execute-api` endpoint succeeds with no header (mock API; the application must enforce). |
| V4 | **Pass.** | After changing the secret, the origin still saw the old value. An update with identical template and parameters ran a stack-level update with no `Distribution` event, so nothing was re-resolved. Changing the revision parameter updated the distribution (`UPDATE_COMPLETE` in 49 s) and the origin then saw the new value. With the SAM transform, an identical update runs as a no-op update rather than failing with "No updates are to be performed". |
| V5 | **Behaves as designed, but see below.** | On the `allExcept` (`Host`, `CloudFront-Viewer-Address`) behavior, `CloudFront-Viewer-Address` was absent, a custom header was kept, and `Host` was the origin domain. |
| V6 | **Deferred** | Needs the real template with the toggle off; run during implementation as a change set. |
| V7 | **Confirmed by read-only check.** | The deployed network distribution `E3RAOR5OWPIYP4` (alias, `sni-only`, created by this template) reports `MinimumProtocolVersion: TLSv1`. |
| V8 | **Pass, with one gap.** | With the planned statement, `xcme-Worker-cross-acct-test-CloudFormationSvcRole` created `xcme-cross-acct-test-OriginSecret` with `GenerateSecretString`, updated it (description and a stack tag change: `UpdateSecret`, `TagResource`), and deleted it through stack deletion. A stack using the same role to resolve the secret value failed with `AccessDenied` on `GetSecretValue`, so the role cannot read values. Gap: `GetRandomPassword` was present in the policy throughout, so I did not isolate whether it is required; AWS lists no resource type for it, so it needs `Resource: "*"` if included. Keep it, since removing it risks failing `GenerateSecretString` stacks. |

**Findings that affect other decisions**

1. **The managed policy already delivers `CloudFront-Viewer-Address`.** `get-origin-request-policy` shows `Managed-AllViewerExceptHostHeader` as `allExcept` with `host` only, yet the Regional origin received 20 `CloudFront-*` headers, including `CloudFront-Viewer-Address` (`107.4.133.45:63168`, my public IP, confirmed with `checkip.amazonaws.com`). The AWS page sentence that the policy "includes additional CloudFront request headers" is correct. The #9 claim that the header "never reaches API Gateway" is false for a Regional API.
2. **A viewer cannot spoof the CloudFront headers.** A viewer-sent `CloudFront-Viewer-Address: 1.2.3.4:5555`, `CloudFront-Viewer-Country: XX`, and `CloudFront-Viewer-ASN: 1` all arrived at the origin with the real values.
3. **So the stripping policy removes the trustworthy header.** It protects against a spoof that does not occur, and it takes away the value `cache-data` v1.4.1 prefers. Decisions 4 and 5 rest on a premise the test refutes.
4. **Regional `sourceIp` is the viewer address** (`107.4.133.45`). This reproduces the reporter's finding.
5. **Edge-optimized behind the distribution:** `sourceIp` was an edge address (`15.158.233.104`), `CloudFront-Viewer-Address` was absent, and `X-Forwarded-For` was `viewer, edge, edge`. This matches the reporter's other finding.
6. **A viewer-sent `X-Forwarded-For` is passed through**: the origin saw `9.9.9.9, <real viewer>, <edge>`. The leftmost entry is spoofable, so right-to-left parsing is required, as `cache-data` does.

**Consequences (applied in this revision)**

- Section 6.B (stripping policy), its parameter, its tests, the `CloudFrontOriginRequestPolicyCRUD` management statement, and the H1 to H6 points from #9 are removed (Decision 10).
- The ingress page says: on a Regional API both `CloudFront-Viewer-Address` and `sourceIp` give the viewer address and the viewer cannot spoof either; edge-optimized APIs get neither; `X-Forwarded-For` must be parsed right to left.
- #9 closes as "already satisfied on Regional APIs; not available on edge-optimized".
- V1 and V8 were completed after an admin attached the statements; the temporary grants still need removal (Section 6, "Verification").

## 3. Current state

- **Origin and behaviors**: One `ApiGatewayOrigin` with `CustomOriginConfig` (`https-only`, TLSv1.2 to the origin) and two API behaviors (default behavior when the API is the root, and a `/${PathApi}/*` behavior), both with the managed origin request policy `b689b0a8-53d0-40ab-baf2-68738e2966ac` (lines 743 and 855).
- **No protection today**: Anyone can call `https://${ApiGatewayId}.execute-api.<region>.amazonaws.com/<stage>`. The only thing the distribution adds is caching and optional logging.
- **Parameters and groups**: The template uses `AWS::CloudFormation::Interface` groups, string parameters with `AllowedValues`, and patterns like `EnableGitHubConnectionAccess` and `EnableBedrockInvocationLogs` for opt-in features (`"true"`/`"false"`, default `"false"`). `OrgPrefix` and `CloudFrontLoggingVersion` were added in v0.0.44.
- **Version and governance**: `v0.1.0/2026-09-26`. PATCH = 0, so development mode applies and the version is not bumped automatically. `tests/test_network_template_unit.py:2564` pins `# Version: v0.1.0/`. The issue plans `v0.2.0`.
- **Management policy**: `CloudFrontOriginRequestPolicyRead` is read-only, `CloudFrontCachePolicyCRUD` is the precedent for create, update, and delete with `Resource: "*"`. IAM statements use long-form intrinsics and `Fn::Sub` for ARNs. Redeploy ordering notes exist in the v0.0.44 and v0.0.45 changelog entries.
- **Pipeline CloudFormation role**: `SsmParameterCRUDThisDeploymentOnly` is the pattern for per-deployment resource permissions. No Secrets Manager statement. The pipeline templates expose `CloudFormationSvcRoleIncludeManagedPolicyArns` for extra permissions (`template-pipeline.yml:294`).
- **Naming**: `AGENTS.md` requires `Prefix-ProjectId-StageId-Resource`. `${Prefix}-${ProjectId}-${StageId}-OriginSecret` complies (PascalCase resource).

## 4. Review

### 4.1 Security

- **What the control gives**: A shared secret in an origin header proves that a request passed through this distribution (or any distribution configured with the same secret). It is not strong authentication and does not replace API authorization. It matches the intent of the OAC comparison in the issue.
- **Secret exposure**: The value sits in the CloudFront configuration. Any principal with `cloudfront:GetDistribution*` can read it. It also sits in plain text in the application. Treat it as an ingress token, not a credential for sensitive actions. The CloudFormation service role reads it from Secrets Manager only at stack operations.
- **Dynamic reference caveat**: The resolved value can appear in the service the resource belongs to. The reporter's test shows it is absent from CloudFormation outputs. Re-check with the real service role (Q7).
- **Comparison and logging in the application**: Applications must compare in constant time, never log the header, and accept two values during rotation. The ingress page must say so.
- **Fail closed or open**: With the toggle on and the secret absent, `{{resolve}}` fails and the stack create or update fails (fail closed at deploy time). At request time the application decides. Document that a missing or empty configured secret in the application must reject requests, not allow them.
- **IAM scope**: `secretsmanager:GetSecretValue` on `arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${Prefix}-*-OriginSecret-??????`. The six-character random suffix is appended by Secrets Manager. A customer-managed KMS key on the secret also needs `kms:Decrypt` for the role; the default `aws/secretsmanager` key does not. Document, do not template.
- **Alternatives that reject**: Restricting by CloudFront IP ranges (an IP condition in an API Gateway resource policy) would admit every CloudFront customer's distribution, and the ranges change over time. I did not verify how API Gateway sees the source address in that case. A web ACL header match on the API stage is stronger because API Gateway enforces it before the application runs, but it needs a WAF attached by the API's stack and has per-request cost. Mention WAF in the ingress page as an optional enforcement point.
- **`CloudFront-Viewer-Address` (from #9)**: Verified on 2026-11-08: under the current managed policy a viewer-sent `CloudFront-Viewer-Address`, `CloudFront-Viewer-Country`, and `CloudFront-Viewer-ASN` arrive at a Regional origin with CloudFront's own values, so they cannot be spoofed. No stripping is needed (Decision 10). A viewer-sent `X-Forwarded-For` is passed through, so applications must parse it right to left.
- **Disclosure**: The bypass is already described in the public issue. The plan adds no exploit detail.

### 4.2 Software engineering

- **Fit**: One parameter, one condition, one `OriginCustomHeaders` property on an existing origin. A Rules assertion that the toggle is only valid when an API sits behind CloudFront (`ApiGatewayId` set and `DomainForApiGateway` empty) uses the pattern in `account-wide-infrastructure.yml:363`. Without it the toggle silently does nothing.
- **Rotation trigger (Q2)**: A string parameter that is part of a property of the distribution forces the update. Candidates: the distribution `Comment`, or a header-adjacent value. A revision suffix on the Comment is the lowest-risk place: it is metadata with no traffic effect and shows up in the console.
- **Rules and SAM**: The template uses `Transform: AWS::Serverless-2016-10-31`. Rules are processed by CloudFormation before or independent of the transform. Verify with `cfn-lint` and a deploy on a test stack.
- **Tests that change**: `tests/test_network_template_unit.py` version pin (line 2564), new tests for the parameter, group membership, condition, Rule, `OriginCustomHeaders` shape, and the `AWS::NoValue` default. `tests/test_network_cloudfront_mgmt_policy_unit.py` for the new statements. Per the testing guidelines, unit tests only; no new property-based tests.
- **Docs to update**: `docs/templates/v2/network/template-network-route53-cloudfront-s3-apigw-README.md` (parameter group, rule, header, deploy order, troubleshooting), the service-role and `prefix-based-infrastructure` READMEs if they list policy statements, `docs/templates/v2/network/README.md`, `CHANGELOG.md` under `v0.0.46` (with redeploy-service-role note), and a new "ingress standard" page.
- **Version**: `v0.2.0`, additive for the core feature. The TLS default would be a behavior change (Section 7).
- **Behavior of the three bundled items**: Function-parameter correction changes the template's parameter contract and tests (deprecation first is the conservative path). The TLS parameter changes a security default. Each has its own test and changelog impact. Q1 A keeps them in this spec, so tasks should order them after the core feature.

### 4.3 Cloud engineering

- **Topology**: Viewer, CloudFront (this template, adds the header), API Gateway default endpoint, application. On an edge-optimized API, an AWS-managed distribution sits between. The reporter measured that the origin header reaches both API types.
- **Update behavior**: Adding `OriginCustomHeaders` is an in-place distribution update with several minutes of propagation. Changing the value later is another in-place update. Rollback restores the previous resolved value only if the secret still holds it, because CloudFormation does not track which secret version a previous deploy used.
- **Rotation sequence (corrected)**: (1) application accepts old and new; (2) put the new value in the secret; (3) update the network stack with a changed rotation-trigger parameter so the distribution is modified and the reference is re-resolved; (4) wait for `Deployed` plus a margin; (5) application drops the old value. Secrets Manager automatic rotation does not apply the new value to the distribution by itself.
- **Error rewriting**: With a static origin present, the 403 and 404 custom error responses rewrite API responses to `index.html` and 200. If the application answers a missing or wrong secret with 403, the viewer sees a 200 page. Applications on such sites should use a different status for secret mismatch (for example 401 or 421), and the ingress page must say so. The rewrite cannot be scoped to a behavior in CloudFront.
- **Stages**: Each stage has its own secret name, so DEV, TEST, and PROD rotate independently. The toggle is a parameter, so a PROD-only rollout is possible.
- **Region**: The dynamic reference resolves in the stack's region. The secret must exist in that region.
- **Cost**: Secrets Manager charges per secret per month and per API call. Origin custom headers have no CloudFront charge. Not template-owned: the application stack creates the secret.
- **Observability**: CloudFront access logs (v1 or v2) record the viewer request, not the origin header. Applications should count rejections. A post-deploy check that a direct call to the `execute-api` endpoint is rejected is the practical verification.
- **Rollout**: Redeploy the network service role (or `prefix-based-infrastructure`) first, create the secret via the application stack, update the network stack, then enable enforcement in the application. Update-time note belongs in the changelog.

## 5. Gaps and observations

- The issue does not state how the secret is generated. The application stack should use `GenerateSecretString` so no human sees or stores the value; say so in the ingress page.
- Whether the application stack can create the secret depends on its role (Decision 3, scope in Q8). The starter issue referenced in the issue (atlantis-starter-02 #14) is outside this repository.
- The issue says "a template rule" for edge-optimized APIs. The template receives only an `ApiGatewayId`, so a Rules assertion cannot read the endpoint type. See Q6.
- The `X-Atlantis-Origin-Secret` name is fixed (no parameter). That is consistent with "the platform owns the naming convention", and it is allowed by CloudFront.
- A secret rotation window with two accepted values is an application responsibility. Nothing in the template enforces it.
- The viewer-sent `CloudFront-Viewer-Address` question from #9 is closed by verification: not spoofable, no stripping (Decision 10).
- Hand-off items from #9 are tracked in Section 7.

## 6. Proposed approach

Scope follows Q1 A: all items in this spec. Template version `v0.2.0`; the TLS default is the one behavior change and goes under "Breaking Changes" in the changelog.

**A. Origin protection (core)**

- Parameter `ApiOriginProtection`: `"true"`/`"false"`, default `"false"`, with `AllowedValues`. New parameter group (suggested label `"API Origin Protection"`) after the API routing group.
- Condition `UseApiOriginProtection` = `ApiOriginProtection` is `"true"` and `ApiIsBehindCloudFront`.
- `OriginCustomHeaders` on `ApiGatewayOrigin`: `!If [UseApiOriginProtection, [{HeaderName: X-Atlantis-Origin-Secret, HeaderValue: "{{resolve:secretsmanager:${Prefix}-${ProjectId}-${StageId}-OriginSecret}}"}], !Ref AWS::NoValue]`. Versionless reference. No secret-name parameter.
- Rule: if `ApiOriginProtection` is `"true"`, `ApiGatewayId` must be non-empty and `DomainForApiGateway` must be empty. New `Rules:` section with the standard section comment.
- Rotation trigger (Q2 A): optional string parameter (working name `ApiOriginSecretRevision`, default empty, restricted pattern and length) that is appended to the distribution `Comment` only when non-empty. Empty keeps today's Comment, so no change set. Changing it modifies the distribution so CloudFormation re-resolves the secret.
- Edge-optimized APIs (Q6 A): no template rule. The ingress page states that origin protection works on both API types and that `sourceIp` as the client address needs a Regional API.

**B. Viewer-header handling (from #9): no template change**

- The managed `AllViewerExceptHostHeader` policy stays on both API behaviors (lines 743 and 855). It already delivers `CloudFront-Viewer-Address` to a Regional API with the true viewer address and overwrites a viewer-sent value (verified, Section 2.1). No custom origin request policy, no extra parameter, no extra management-role statement.
- The ingress page documents this (see F).

**C. Bundled small changes (Q1 A)**

- `ViewerMinimumTlsVersion`: string, default `TLSv1.2_2021`, applied as `MinimumProtocolVersion` only when the viewer certificate uses an alias (`CreateDnsRecordForCloudFront`); otherwise `AWS::NoValue` because CloudFront fixes the policy at `TLSv1` for the default certificate. Allowed values: `TLSv1`, `TLSv1_2016`, `TLSv1.1_2016`, `TLSv1.2_2018`, `TLSv1.2_2019`, `TLSv1.2_2021`, `TLSv1.2_2025`, `TLSv1.3_2025` (`SSLv3` excluded). Check the repository's `cfn-lint` accepts the 2025 values. Operators who need old clients keep `TLSv1` explicitly.
- Origin-request and origin-response function parameters (`CloudFrontStaticFunctionOriginRequest`, `CloudFrontStaticFunctionOriginResponse`, `CloudFrontApiFunctionOriginRequest`, `CloudFrontApiFunctionOriginResponse`): deprecate (Q9 A). Keep the parameters and their metadata group entries so existing stacks that pass them still update. Mark each description `DEPRECATED`, state that CloudFront Functions run only on viewer events, and stop wiring them into `FunctionAssociations` for the default and path behaviors. Keep or retire the four `HasStatic/ApiFunctionOrigin*` conditions according to what remains referenced (cfn-lint reports unused conditions). Document in the network README and the changelog under Deprecated.
- Documentation: the distribution-wide 403/404 `CustomErrorResponses` caveat, in the network README and the ingress page.

**D. Permissions**

- `network-cloudfront-mgmt-policy.yml`:
  - `SecretsManagerOriginSecretRead` with `secretsmanager:GetSecretValue` on `arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${Prefix}-*-OriginSecret-??????`.
  - `CloudFrontOriginRequestPolicyRead` stays as is.
- `cloudformation-svc-role.yml` (pipeline CloudFormation role, Q3 A): new `SecretsManagerCRUDThisDeploymentOnly` statement scoped to `arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${Prefix}-${ProjectId}-${StageId}-*`. Actions (Q8 A): `secretsmanager:CreateSecret`, `UpdateSecret`, `DeleteSecret`, `PutSecretValue`, `DescribeSecret`, `TagResource`, `UntagResource` on that resource; no `GetSecretValue`. `secretsmanager:GetRandomPassword` does not support resource scoping and needs `Resource: "*"` for `GenerateSecretString`; verify during Q7 testing.
- Pipeline templates consuming the module: `template-pipeline.yml` (v2.0.23), `template-pipeline-github.yml` (v2.0.5), and `template-pipeline-s3-source.yml` (v0.0.0). Per `template-version-control`, increment PATCH for the first two (deployed, PATCH > 0); the third stays at v0.0.0. `template-pipeline-build-only.yml` does not use the module.

**E. Tests**

- `tests/test_network_template_unit.py`: version pin to `v0.2.0`; parameters, group membership, conditions, Rule, `OriginCustomHeaders` shape and `AWS::NoValue` default, Comment unchanged when revision is empty, the API behaviors still use the managed policy ID, TLS parameter and condition, function parameters still present, marked deprecated, and absent from `FunctionAssociations`.
- `tests/test_network_cloudfront_mgmt_policy_unit.py`: new and changed statements, including the secret ARN pattern.
- A unit test for the new `cloudformation-svc-role.yml` statement and for the two pipeline version bumps.
- Existing parameter and condition lists in `test_network_template_unit.py` (lines ~2092-2115) and `test_network_template_property.py` (lines ~1592-1596) updated. No new property-based tests.

**F. Documentation and changelog**

- Ingress standard page at `docs/end-user/api-ingress-standard.md` (location suggested; link from `docs/README.md` and the network README): Regional API behind the distribution; on a Regional API `sourceIp` and `CloudFront-Viewer-Address` both give the viewer address and a viewer cannot spoof either; edge-optimized APIs get neither (`sourceIp` is an edge address and the header is dropped); `X-Forwarded-For` must be parsed right to left; secret generation with `GenerateSecretString`, constant-time comparison, no logging of the header, the rotation sequence in Section 4.3, the 403/404 caveat and recommended status for a secret mismatch, optional WAF header match, edge-optimized limits, the KMS note, and who can read the secret in the CloudFront configuration.
- Network template README: parameters, Rule, header, deploy order, troubleshooting (`AccessDenied` on `GetSecretValue`, secret not found, rotation not applied).
- Pipeline template READMEs and `docs/templates/v2/modules` or service-role READMEs where they list IAM statements.
- `CHANGELOG.md` under `v0.0.46`: Added, Changed, and Breaking Changes (TLS default). Update-time notes: redeploy the network service role (or `prefix-based-infrastructure`) before the network stack; the pipeline role change takes effect at the next pipeline stack update.
- Drop the promotion integration test from the doc list.

**Order of deployment for adopters** (goes in the docs): redeploy service roles; update pipeline stacks (for the secret permission); the application stack creates the secret; update the network stack with `ApiOriginProtection="true"`; the application turns enforcement on.

**Verification (Q7 B)**: done on 2026-11-08 for V1 to V5, V7, and V8 (Section 2.1). Still open: V6, a change set against the previous template with the toggle off, which runs during implementation against the real template.

The temporary test grants were applied by an admin as edits to existing policies rather than separate inline policies, and must be removed after testing:

- Managed policy `XCME-CfnSvcRole-Network-CloudFront-Mgmt` (default version `v3`) carries `SecretsManagerOriginSecretRead`; restore the previous default version or remove the statement. This policy is owned by the `XCME-Atlantis-Prefix-Based-Infra` stack.
- Inline policy `CloudFormationRolePolicy` on `xcme-Worker-cross-acct-test-CloudFormationSvcRole` carries `SecretsManagerCRUDThisDeploymentOnly` and `SecretsManagerGetRandomPassword`; remove both statements. The pipeline stack owns this role.

Statements verified (these become the module changes):

```json
{"Sid":"SecretsManagerOriginSecretRead","Effect":"Allow","Action":"secretsmanager:GetSecretValue","Resource":"arn:aws:secretsmanager:us-east-2:458901159113:secret:xcme-*-OriginSecret-??????"}
```

```json
[{"Sid":"SecretsManagerCRUDThisDeploymentOnly","Effect":"Allow","Action":["secretsmanager:CreateSecret","secretsmanager:UpdateSecret","secretsmanager:DeleteSecret","secretsmanager:PutSecretValue","secretsmanager:DescribeSecret","secretsmanager:TagResource","secretsmanager:UntagResource"],"Resource":"arn:aws:secretsmanager:us-east-2:458901159113:secret:xcme-cross-acct-test-*"},{"Sid":"SecretsManagerGetRandomPassword","Effect":"Allow","Action":"secretsmanager:GetRandomPassword","Resource":"*"}]
```

**Alternatives considered**

| Option | Why not |
|--------|---------|
| Restrict API Gateway by CloudFront IP ranges | Admits every CloudFront customer's distribution and needs range upkeep; does not prove the request came through this distribution. |
| Web ACL header match on the API stage | Stronger enforcement, but the API's stack owns the stage and WAF has per-request cost. Documented as optional. |
| Secret name as a parameter | The platform owns the naming convention (issue). |
| Pin `version-id` in the dynamic reference | AWS advises versionless references; each rotation would need the new id (Q2 B not chosen). |
| Lambda authorizer or application-only check | Still needs a secret the distribution can send; no different in the template. |
| Edge-optimized refusal through a Rule, attestation parameter, or lookup custom resource | Not needed for the protection to work (Q6 A). |

## 7. Related improvements

| Item | Class | Rationale | Effort | Risk |
|------|-------|-----------|--------|------|
| Rotation-revision parameter | Include (Q2 A) | Required for the documented rotation to work. | S | Low |
| Rules assertion tying the toggle to an API behind CloudFront | Include | Stops a silently ineffective toggle. | S | Low |
| Ingress standard page | Include | Part of the issue; also carries the verified Regional and edge-optimized client-IP guidance handed over from #9. | S | Low |
| Viewer-header stripping policy (from #9) | Dropped (Decision 10) | Verified: the header is delivered and cannot be spoofed; stripping would remove the trustworthy value. | | |
| 403/404 `CustomErrorResponses` caveat and status advice | Include | In the issue; zero template risk. | S | Low |
| `ViewerMinimumTlsVersion` parameter, default `TLSv1.2_2021` | Include (Q1 A) | In the issue; the one behavior change. | S-M | Medium |
| Deprecate origin-event function parameters | Include (Q1 A, Q9 A) | In the issue. | S-M | Medium |
| Secrets Manager statement in the pipeline CloudFormation role | Include (Q3 A, Q8 A) | Needed for the documented deployment order. | M | Medium |
| Pipeline template PATCH bumps and README updates for the new statement | Include | Required by version control for deployed templates that consume the module. | S | Low |
| Drop "promotion integration test" from the doc list | Include | The document does not apply to network changes. | S | Low |
| Remove the deprecated `HeadersToForwardToApi` parameter | Note only | Breaking parameter change. | S | Medium |
| Edge-optimized endpoint-type detection | Note only (Q6 A) | Needs a parameter or custom resource. | M | Medium |
| Customer-managed KMS key on the origin secret | Note only | Document `kms:Decrypt`; not templated. | | |

## 8. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Rotation silently leaves the old value on the distribution | Rotation-revision parameter and documented steps; V4 |
| Stack update fails because the service role lacks new permissions | Changelog update-time note; redeploy the network service role first |
| Dynamic reference cannot be resolved with the service role identity | Verified in V1: it resolves with the service role once `GetSecretValue` is granted |
| The pipeline role change grants every application the ability to manage secrets named for its deployment | Scope to `${Prefix}-${ProjectId}-${StageId}-*` only; no `GetSecretValue` (Decision 8); V8 |
| Pipeline role change applies only at the next pipeline stack update | Changelog note and docs |
| Secret visible to anyone with `cloudfront:GetDistributionConfig` | State it in the docs; treat the header as an ingress token |
| 403 or 404 from the application rewritten to a static page | Document; recommend a different status for secret mismatch |
| Mixed secret state during rotation causes rejections | Application accepts both values; wait for `Deployed` plus margin |
| TLS default blocks clients without TLS 1.2 on existing custom-domain stacks | Breaking Changes note; `TLSv1` remains selectable; V7 |
| Large single spec (Q1 A) slows release | Tasks ordered so the core feature, permissions, and docs can ship independently of the bundled items |
| Template treated as deployed while PATCH = 0 | The change is documented as breaking in the changelog even though the version rules allow it in development mode |
| Temporary test grants left on the XCME managed policy and pipeline role | Removal steps in Section 6 |
| Edge-optimized APIs behind the distribution get neither `sourceIp` nor `CloudFront-Viewer-Address` | Documented; Regional recommended (Decision 6) |

## 9. Locked decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 (Q1 A) | All items stay in this spec: origin protection, TLS parameter, function-parameter fix, and error-response docs. (The #9 stripping policy was included here and dropped by Decision 10.) | User choice. Keeps the release's network changes in one place. Residual risk: larger scope and one behavior change (TLS default); tracked in Section 8. |
| 2 (Q2 A) | Add a rotation-revision parameter (default empty) appended to the distribution `Comment`; keep the versionless reference. | AWS says updating only the secret does not re-resolve it; AWS recommends versionless references. |
| 3 (Q3 A) | Add `SecretsManagerCRUDThisDeploymentOnly` to `cloudformation-svc-role.yml`, scoped to `${Prefix}-${ProjectId}-${StageId}-*`. | User choice, over my recommendation to document a managed policy. Makes the documented deployment order work without extra steps. Residual risk: every pipeline using the module gains the grant; mitigated by scope (Decision 8). |
| 4 (Q4 A) | **Superseded by Decision 10.** Stripping policy has its own toggle, default `"false"`. | Preserves "no change set" for existing stacks and avoids failures from stale service roles. |
| 5 (Q5 A) | **Superseded by Decision 10.** Strip `Host` and `CloudFront-Viewer-Address` only. | Matches the client-IP guidance; extra headers can be added when needed. |
| 6 (Q6 A) | Document edge-optimized limits; no Rule, attestation parameter, or custom resource. | The protection works on both API types; the template cannot see the endpoint type. |
| 7 (Q7 B) | I run the verification on a temporary stack with `--profile release`, confirming account and region first, and tear it down afterward. | The permission and dynamic-reference behavior cannot be confirmed by reading. Done 2026-11-08: V1 to V5, V7, and V8 pass (V8 without isolating `GetRandomPassword`). V6 runs during implementation. Temporary grants on the XCME roles still need removal (Section 6). |
| 8 (Q8 A) | The pipeline role statement allows `CreateSecret`, `UpdateSecret`, `DeleteSecret`, `PutSecretValue`, `DescribeSecret`, `TagResource`, `UntagResource` on `${Prefix}-${ProjectId}-${StageId}-*`, plus `GetRandomPassword` on `*`. It does not allow `GetSecretValue`. | Follows the `ThisDeploymentOnly` pattern and keeps the deployment role from reading secret values. A stack that needs to resolve its own secret can be handled later. |
| 9 (Q9 A) | Deprecate the four origin-request and origin-response function parameters: keep them, mark them DEPRECATED, and stop associating them. | Non-breaking, matches the `HeadersToForwardToApi` precedent, and avoids a Lambda@Edge feature. CloudFront Functions cannot run on origin events, so working stacks do not depend on them. |
| 10 (reopen, user instruction) | Drop the viewer-header stripping policy, its toggle, the `AWS::CloudFront::OriginRequestPolicy` resource, and the `CloudFrontOriginRequestPolicyCRUD` management statement. Keep `SecretsManagerOriginSecretRead` and the pipeline-role Secrets Manager statement. | Runtime verification showed the managed policy already delivers `CloudFront-Viewer-Address` and viewers cannot spoof it; stripping would remove the value `cache-data` prefers. Removes the "no change set" conflict and a quota and permission cost. |

Confirmed spin-offs: none. Q1 A keeps every item in this spec.

## 10. Open questions and recommendations

No open questions.
