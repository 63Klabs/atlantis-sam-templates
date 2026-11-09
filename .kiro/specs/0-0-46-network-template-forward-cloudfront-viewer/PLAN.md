# Network template: forward CloudFront-Viewer-Address to the API Gateway origin

> **Status**: Locked 2026-11-08 (reopened after runtime verification and re-locked the same day). Disposition: **already satisfied on Regional APIs**; not available on edge-optimized APIs. #9 makes no template change and is closed when #10 and the ingress documentation ship.
> **Issue**: [ISSUE.md](ISSUE.md) (GitHub #9)
> **Verification note (2026-11-08)**: runtime checks in account 458901159113 / us-east-2 (results in [#10 PLAN.md, Section 2.1](../0-0-46-network-template-apioriginprotection-origin/PLAN.md)) show the managed policy already delivers `CloudFront-Viewer-Address` to a Regional API and overwrites a viewer-sent value. The original premise of the issue is false for Regional APIs. Decisions 2, 3, and 6 were superseded by Decision 9.
> **Reviewed against**: `dev` at `a79a109` (v0.0.45 release) on 2026-11-08. Working tree has only the unreleased `v0.0.46` CHANGELOG header and two new untracked spec folders (#9, #10).

## 1. Summary

Applications behind the network template's CloudFront distribution cannot receive `CloudFront-Viewer-Address` unless the API behaviors' origin request policy forwards it. The template hard-codes the managed `AllViewerExceptHostHeader` policy (`b689b0a8-53d0-40ab-baf2-68738e2966ac`) on both API behaviors. The reporter wants the header forwarded for `@63klabs/cache-data` v1.4.1. A later comment on the issue (same author, with measurements) argues the header is unnecessary on a Regional API, because `requestContext.identity.sourceIp` already carries the viewer address, and proposes closing this issue in favor of documentation plus #10 (origin secret header).

What runtime verification showed (2026-11-08):

1. **The header already reaches a Regional API.** `get-origin-request-policy` shows the managed policy as `allExcept` with `host`, yet a Regional origin received 20 `CloudFront-*` headers including `CloudFront-Viewer-Address` with the true viewer address. The AWS page sentence that the policy "includes additional CloudFront request headers" is correct.
2. **A viewer cannot spoof it.** A viewer-sent `CloudFront-Viewer-Address`, `CloudFront-Viewer-Country`, and `CloudFront-Viewer-ASN` arrived with CloudFront's own values. `requestContext.identity.sourceIp` on the Regional API was also the true viewer address.
3. **Edge-optimized APIs get neither.** `sourceIp` is an edge address, `CloudFront-Viewer-Address` is absent (dropped by the AWS-managed distribution in front of the API), and `X-Forwarded-For` was `viewer, edge, edge`. A custom origin request policy on the Atlantis distribution cannot change that.
4. **A custom policy was never going to help.** `allViewerAndWhitelistCloudFront` forwards `Host` and breaks `execute-api` origins; `whitelist` is capped at 10 headers and would drop headers forwarded today.

Disposition (Decision 9): close #9 as already satisfied on Regional APIs. No template change. The ingress page in #10 documents that both `CloudFront-Viewer-Address` and `sourceIp` give the viewer address on a Regional API, that edge-optimized APIs get neither, and that `X-Forwarded-For` must be parsed right to left. The earlier plan to hand a stripping policy to #10 is withdrawn.

## 2. Assessment of the issue

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| 1 | The template forwards headers to API Gateway with the managed `AllViewerExceptHostHeader` policy | Confirmed | `templates/v2/network/template-network-route53-cloudfront-s3-apigw.yml:743` (DefaultCacheBehavior, conditional on `StaticOriginIsRoot`) and `:855` (path-based API behavior). Added in v0.0.34 (`243849b`, spec `0-0-34-cloudfront-origin-request-policy`). |
| 2 | That policy forwards no CloudFront headers, so `CloudFront-Viewer-Address` never reaches API Gateway | **Not confirmed (false for Regional)** | `get-origin-request-policy` returns `allExcept` with `host`, but a Regional mock API behind a test distribution received `CloudFront-Viewer-Address` and 19 other `CloudFront-*` headers under this policy (2026-11-08, #10 PLAN.md Section 2.1). On an edge-optimized API the header is absent. |
| 3 | `AllViewerAndCloudFrontHeaders-2022-06` also forwards `Host`, which is why the template avoids it | Confirmed | AWS managed policy page: "All headers in the viewer request" plus 21 CloudFront headers. v0.0.34 design records the Host reason (`.kiro/specs/0-0-34-cloudfront-origin-request-policy/design.md`, Key Design Decisions 1-2). |
| 4 | `CloudFront-Viewer-Address` is `IP:port` | Confirmed for IPv4, IPv6 untested | Observed `107.4.133.45:63168`. The distribution sets `IPV6Enabled: true` (`template-network-route53-cloudfront-s3-apigw.yml:659`); an IPv6 viewer was not tested. The format is the application's concern. |
| 5 | A custom `AWS::CloudFront::OriginRequestPolicy` needs `Create/Update/DeleteOriginRequestPolicy` on the management role | Confirmed | `templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml` sid `CloudFrontOriginRequestPolicyRead` grants read actions only. `CloudFrontCachePolicyCRUD` is the precedent for create/update/delete with `Resource: "*"`. Test coverage in `tests/test_network_cloudfront_mgmt_policy_unit.py`. |
| 6 | (Comment) On a Regional API behind a distribution, `sourceIp` is the true viewer address and cannot be spoofed by viewer headers or third-party edge functions | Partly confirmed | Reproduced: `sourceIp` was the viewer's address (`107.4.133.45`) and a viewer-sent `X-Forwarded-For` and `CloudFront-*` headers did not change it. Third-party edge functions and HTTP APIs were not tested. |
| 7 | (Comment) On an edge-optimized API, `sourceIp` is an edge address and a viewer-supplied `CloudFront-Viewer-Address` is dropped | Confirmed | Reproduced: `sourceIp` was `15.158.233.104`, `CloudFront-Viewer-Address` absent even though CloudFront sent it, `X-Forwarded-For` was `viewer, edge, edge`. |
| 8 | (Comment) Forwarding a Host-bearing policy to API Gateway origins does not work | Confirmed (AWS docs) | The managed-policy page says forwarding the viewer `Host` to API Gateway origins "can prevent them from working." |

Not stated in the issue:

- The default behavior and the path behavior both use the policy ID as a literal string. There is no mapping or parameter for it.
- No test asserts the API origin request policy ID. A grep of `tests/` finds only the mgmt-policy read statement. A new change would add the first such tests.
- `OriginCustomHeaders` is not set anywhere in the template yet (#10 introduces it).

## 3. Current state

- **Origin**: `${ApiGatewayId}.execute-api.${AWS::Region}.amazonaws.com`, `https-only`, TLSv1.2 (template lines ~697-709). It is the default endpoint, so the template works for both edge-optimized and Regional APIs without knowing which one it is. The template takes only an API ID, so it cannot detect the endpoint type.
- **Header forwarding**: `HeadersToForwardToApi` is deprecated and unused (line 494). The custom API cache policy `CloudFrontCachePolicyApi` sets `HeadersConfig: none` (line 997), so the cache key does not vary on headers. All forwarding happens through the managed origin request policy.
- **Why the managed policy**: v0.0.34 moved header forwarding out of the cache policy. AWS describes this exact policy as intended for API Gateway, Lambda function URL, and Lambda web function origins, because those origins need `Host` to equal the origin domain. When the viewer Host is removed, CloudFront adds a Host with the origin domain name.
- **Contradictory AWS documentation**: the `AllViewerExceptHostHeader` section lists its headers setting as all viewer headers except `Host`, and separately says it adds HTTP protocol, HTTP version, TLS version, device type and viewer location headers. The CloudFront headers page lists `CloudFront-Viewer-Address` as a header that can be added in an origin request policy but not a cache policy.
- **Header behaviors available in a custom policy** (CloudFormation `HeadersConfig`): `none`, `whitelist`, `allViewer`, `allViewerAndWhitelistCloudFront`, `allExcept`. Only `whitelist` omits `Host` while adding CloudFront headers. `allExcept` omits `Host` but adds nothing.
- **Quotas**: 10 headers per origin request policy and 20 custom origin request policies per account by default, adjustable. These are per account and shared across every stack that creates one.
- **Existing precedent for custom policy resources**: `CloudFrontCachePolicyStatic` and `CloudFrontCachePolicyApi` are created conditionally in production, with matching mgmt-role CRUD actions. Version is `v0.1.0` (PATCH = 0, development mode), so non-breaking and breaking changes alike do not require a new file yet.
- **Sibling work in the same release**: #10 (`0-0-46-network-template-apioriginprotection-origin`) edits the same template, plans a `v0.2.0` bump, adds `OriginCustomHeaders`, and adds a management-role statement. Changes to both must merge cleanly.

## 4. Review

### 4.1 Security

- **Spoofing: verified not possible for the CloudFront headers.** On a Regional API a viewer-sent `CloudFront-Viewer-Address` is replaced with the real value. A viewer-sent `X-Forwarded-For` is passed through (`9.9.9.9, <viewer>, <edge>`), so applications must parse it right to left.
- **Direct access to the origin.** Without #10, any caller can hit the `execute-api` endpoint and set `CloudFront-Viewer-Address` or `X-Forwarded-For` themselves. Header-based client IP is trustworthy only when the origin accepts traffic from the distribution alone. The `sourceIp` approach does not have this dependency.
- **Fail-open risk if forwarding is opt-in.** Not applicable: nothing is forwarded by a new toggle (Decision 9).
- **IAM scope.** Not applicable: no custom origin request policy is created under #9 (Decision 9).
- **Disclosure.** The spoofing concern describes a weakness in applications that follow the cache-data default, in a published repository. Keep exploit detail in this plan to what the decisions require, and sequence any fix with the cache-data release.

### 4.2 Software engineering

- **Fit**: the template already creates conditional custom policies, so a custom origin request policy would follow an existing pattern. The harder part is the header list, not the resource.
- **Regression risk of an allow-list**: every header an application relies on today (for example `Authorization`, `Content-Type`, `X-Api-Key`, `Accept`, `Origin`, `Referer`, `User-Agent`, custom `X-*`) is forwarded implicitly. A whitelist of up to 10 names silently drops the rest. The deprecated default list `Accept,Origin,Referer,User-Agent,Authorization` already shows what a whitelist would have to include, and it does not include `Content-Type` or `X-Api-Key`. This cannot be called backward compatible.
- **Template size and conditions**: a second policy adds a resource, a condition, and a three-way choice at two call sites (default behavior and path behavior). The `!If` expressions at lines 743 and 855 are already hard to read.
- **Tests that change**: `tests/test_network_template_unit.py:2564` pins the version to `v0.1.0`. The #10 bump to `v0.2.0` will touch that same assertion, so coordinate. `tests/test_network_cloudfront_mgmt_policy_unit.py` would need create/update/delete statement tests. No test currently asserts the managed policy ID.
- **Docs to update**: `docs/templates/v2/network/template-network-route53-cloudfront-s3-apigw-README.md` (sections around lines 587, 631, 642, 758 describe the managed policy), `CHANGELOG.md` under `v0.0.46`, and the network category README if the parameter list changes.
- **Application contract**: the value format must be documented (IPv4 `ip:port`, IPv6 form to be confirmed), because `IPV6Enabled: true` makes IPv6 viewers routine.

### 4.3 Cloud engineering

- **Topology**: Viewer, CloudFront (this template), API Gateway default endpoint, application. On an edge-optimized API there is a second, AWS-managed CloudFront distribution between this one and the API. Any header forwarded by this template must survive that hop, and the comment says it probably will not. On a Regional API there is no second distribution.
- **Update behavior**: switching a behavior's `OriginRequestPolicyId` is an in-place distribution update that takes several minutes to propagate. Creating a new `AWS::CloudFront::OriginRequestPolicy` is stateless and is created before the distribution update that references it. Rollback restores the managed policy ID.
- **Quota exposure**: 20 custom origin request policies per account. One new resource per stack is fine for a few stacks and could surprise an account that deploys many stages (every `StageId` would create its own). A shared, account-level policy would avoid this but is a different design (account-wide stack, export) and is not justified here.
- **Cost**: no direct cost. Origin request policies are free. Forwarding more headers does not change the cache key, so cache hit ratio is unaffected.
- **Stages**: DEV and TEST use `CachingDisabled` regardless of parameters (template comment at line 713). Header forwarding behaves the same in all stages, so a stage-specific test is not needed beyond a PROD-like deployment.
- **Observability**: nothing to add for a header. A post-deploy check that echoes the header is the practical verification.
- **Rollout**: behind an opt-in toggle, rollout is a parameter flip per stack. The management-role change must be deployed first (service-role stack or `prefix-based-infrastructure.yml`), as in the v0.0.44 and v0.0.45 changelog notes.

## 5. Gaps and observations

- The issue defers its own central question: which header behavior works with an API Gateway origin. Documentation answers part of it (Section 3). The rest needs a deployed stack.
- The issue and the comment disagree on direction. The issue asks for forwarding; the comment recommends not forwarding and closing. Both are by the same author, and the label `approved for development` was applied after the comment was posted (comment 03:36Z, approval 03:45Z), so the approval may reflect either.
- The comment's Regional-API finding was reproduced on 2026-11-08 with mock integrations (REST APIs only).
- Unspecified: REST versus HTTP API. The `execute-api` origin works for both, and the identity fields differ (`requestContext.identity.sourceIp` versus `requestContext.http.sourceIp`).
- Resolved by verification: the header reaches a Regional origin and a viewer-sent value is replaced.
- #10 plans to document secret rotation and an "ingress standard" page. This plan should not duplicate that page; it should link to it.
- `CustomErrorResponses` for 403 and 404 (noted in #10) can rewrite API errors when a static origin exists. Not in scope here.

## 6. Proposed approach

**#9 changes no template, management role, test, or version.** The header is already delivered to a Regional API and cannot be spoofed by a viewer, so the request is satisfied by the existing managed `AllViewerExceptHostHeader` policy. The documentation lives in #10 (Decision 8). #9 stays open until #10 and the ingress page ship, then closes with a link to them (Decision 7).

What #9 produces:

- This plan and the closure rationale (Section 9).
- A hand-off to #10: the ingress page states the verified behavior for Regional and edge-optimized APIs.
- No `requirements.md`, `design.md`, or `tasks.md`, because nothing is built under #9.

**Deliberately not done**

| Option | Result |
|--------|--------|
| Custom origin request policy with `allViewerAndWhitelistCloudFront` | Rejected. Forwards `Host`; breaks `execute-api` origins. |
| Custom origin request policy with `whitelist` | Rejected. Capped at 10 headers per policy by default, and would drop headers forwarded today. |
| Forwarding `CloudFront-Viewer-Address` through an opt-in parameter | Not needed on Regional APIs (already delivered). Does not help edge-optimized APIs: the AWS-managed distribution in front of the API drops it. |
| Stripping a client-sent `CloudFront-Viewer-Address` | Withdrawn. Viewer-sent values are replaced by CloudFront, and stripping would remove the trustworthy header. |
| Viewer-request CloudFront Function copying `event.viewer.ip` into a header | Rejected. API function slots are user-supplied ARNs, and CloudFront allows one function per event type per behavior. |
| API custom domain matching the CloudFront alias with a forwarded `Host` | Rejected. Different DNS and certificate design, and a large behavior change. |

## 7. Related improvements

| Item | Class | Rationale | Effort | Risk |
|------|-------|-----------|--------|------|
| Origin secret header (`ApiOriginProtection`) | Already #10 | Makes header-based client IP trustworthy against direct calls to the default endpoint. | M | Low |
| Ingress standard page stating the verified Regional and edge-optimized client-IP behavior | Hand to #10 | Prevents repeat requests for this header. | S | Low |
| Refuse or warn on edge-optimized APIs behind the distribution | Decided in #10 (document only) | Template cannot detect endpoint type. | | |
| Strip a client-sent `CloudFront-Viewer-Address` | Dropped | Not spoofable; stripping removes the trustworthy value. | | |
| Reproduce step for Regional `sourceIp` | Done | Reproduced on 2026-11-08 (REST). HTTP APIs untested; note in the ingress page. | | |
| Unit test pinning the API behaviors' origin request policy ID | Hand to #10 if it touches those lines, otherwise dropped | No template change in #9. | S | Low |
| Remove the deprecated `HeadersToForwardToApi` parameter | Note only | Breaking parameter change. | S | Medium |
| IPv6 note for `CloudFront-Viewer-Address` | Hand to #10 (docs) | The distribution has `IPV6Enabled: true`; IPv6 viewers were not tested. | S | Low |

## 8. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Edge-optimized APIs get neither `CloudFront-Viewer-Address` nor an accurate `sourceIp` | Documented in the ingress page; Regional recommended; handling stays document-only in #10 |
| HTTP APIs (`requestContext.http.sourceIp`) and IPv6 viewers were not tested | Note in the ingress page; test when an HTTP API is available |
| A viewer-sent `X-Forwarded-For` is spoofable on its leftmost entries | Documented: parse right to left, or use `sourceIp` on Regional APIs |
| Direct calls to the `execute-api` endpoint bypass the distribution and can supply any header | #10 origin secret |
| #9 is closed before #10 and the docs exist, leaving users without guidance | Decision 7 ties closure to #10 shipping |

## 9. Locked decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 (Q1) | Do not run runtime verification for #9. Accept the reporter's measurements and the AWS docs as stated. | User choice. **Superseded in effect:** verification ran on 2026-11-08 as part of #10 (Decision 9). |
| 2 (Q2) | Close #9 as not needed. Recommend a Regional API and `sourceIp`. No forwarding of `CloudFront-Viewer-Address`. | **Superseded by Decision 9.** |
| 3 (Q3) | Do not forward `CloudFront-Viewer-Address`. | **Superseded by Decision 9.** The header is already delivered on Regional APIs. |
| 4 (Q4) | Not applicable. | No forwarding is implemented. |
| 5 (Q6, sequencing) | #10 proceeds; #9 does not take a template version and does not touch the shared files. | Still applies. |
| 6 (Q5 A) | Fold removal of a client-sent `CloudFront-Viewer-Address` into #10. | **Superseded by Decision 9.** Verified not spoofable; stripping would remove the trustworthy header. |
| 7 (Q6 B) | Close #9 when #10 and the Regional documentation ship, not before. | Still applies. |
| 8 (Q6 hand-off) | Hand-off items: ingress page, edge-optimized rule (document only), `HeadersToForwardToApi` removal not done, IPv6 note moves to the ingress page. | Updated: stripping and the `sourceIp` reproduce step are no longer hand-off items. |
| 9 (reopen, user instruction) | Disposition of #9 is **already satisfied on Regional APIs**. No template change. Not available on edge-optimized APIs. The stripping hand-off to #10 is withdrawn. | Runtime verification on 2026-11-08: the managed policy delivers `CloudFront-Viewer-Address` to a Regional origin, a viewer-sent value is replaced, and `sourceIp` is the true viewer address. Edge-optimized APIs receive neither. |

Confirmed spin-offs: none.

## 10. Open questions and recommendations

No open questions.
