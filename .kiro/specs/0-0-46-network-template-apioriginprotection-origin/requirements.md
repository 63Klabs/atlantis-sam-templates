# Requirements Document

**Spec:** v0.0.46 Network Template API Origin Protection

## Introduction

The network template protects its S3 origin with an Origin Access Control but has no equivalent for its API Gateway origin. The distribution reaches the API through the default `execute-api` endpoint, so that endpoint stays reachable by anyone, and a request that skips the distribution bypasses its caching and any web ACL attached to it.

This spec adds an opt-in origin secret header. When enabled, CloudFront adds `X-Atlantis-Origin-Secret` to every origin request to the API, with the value taken from a Secrets Manager secret named by platform convention. CloudFront overwrites any viewer-sent header of the same name. The application accepts requests only when the header matches.

The spec also includes the permissions and documentation the feature needs, and three smaller changes listed in the source issue (a viewer minimum TLS version parameter, deprecation of four origin-event function parameters, and documentation of the distribution-wide 403/404 error rewrite).

- **GitHub Issue**: [#10](https://github.com/63Klabs/atlantis-sam-templates/issues/10)
- **Type**: feature
- **Plan**: [PLAN.md](PLAN.md) (locked 2026-11-08; Decisions 1 to 10)
- **Related**: [0-0-46-network-template-forward-cloudfront-viewer](../0-0-46-network-template-forward-cloudfront-viewer/PLAN.md) (issue #9, closes as already satisfied on Regional APIs)

## Glossary

- **Origin secret**: A Secrets Manager secret named `${Prefix}-${ProjectId}-${StageId}-OriginSecret`. Created by the application stack, not by the network template.
- **Origin secret header**: The custom origin header `X-Atlantis-Origin-Secret`.
- **Dynamic reference**: A CloudFormation `{{resolve:secretsmanager:...}}` reference. CloudFormation resolves it with the identity of the stack's service role at stack create and update.
- **Network service role**: `${PrefixUpper}-CloudFormation-Service-Role-Network-CloudFront-Mgmt` and `...-Network-Full-Mgmt`. Both include the managed policy built from `network-cloudfront-mgmt-policy.yml`.
- **Pipeline CloudFormation role**: `${Prefix}-Worker-${ProjectId}-${StageId}-CloudFormationSvcRole`, built from `templates/v2/modules/pipeline/cloudformation-svc-role.yml`. It deploys the application stack that creates the origin secret.
- **API behind CloudFront**: The condition `ApiIsBehindCloudFront` in the network template (`ApiGatewayId` set and `DomainForApiGateway` empty).
- **Rotation revision**: An operator-supplied string that is included in the distribution `Comment` so that changing it modifies the distribution and makes CloudFormation re-resolve the secret.

## Verified Behavior

Runtime checks were run on 2026-11-08 in account `458xxxxxxx`, region `us-east-2`, with temporary stacks that have since been deleted. Full results are in [PLAN.md Section 2.1](PLAN.md). These facts drive the requirements:

1. CloudFormation resolves `{{resolve:secretsmanager:...}}` with the **service role's** identity. A role without `secretsmanager:GetSecretValue` fails the create with `AccessDenied`.
2. The resolved value does not appear in `describe-stacks`, stack events, stack resources, or the original or processed templates, with `Transform: AWS::Serverless-2016-10-31` and a `Rules` section. It does appear in the CloudFront distribution configuration.
3. A viewer-sent `X-Atlantis-Origin-Secret` is replaced by the real value on Regional and edge-optimized APIs.
4. Changing only the secret value does not update the distribution. Changing the rotation revision updates it and the origin then receives the new value.
5. `AllViewerExceptHostHeader` already delivers `CloudFront-Viewer-Address` to a Regional API and a viewer-sent value is overwritten, so no custom origin request policy is needed.
6. The deployed network distribution reports `MinimumProtocolVersion: TLSv1` because the template sets no value.
7. A pipeline CloudFormation role with the statement in Requirement 5 can create, update, and delete the convention-named secret and cannot read its value.

## Out of Scope

- A custom `AWS::CloudFront::OriginRequestPolicy`, forwarding or stripping `CloudFront-Viewer-Address`, and any `Create/Update/DeleteOriginRequestPolicy` management-role permission (Decision 10).
- Creating the origin secret in the network template, or any secret-name parameter.
- Detecting or refusing edge-optimized APIs in the template (Decision 6).
- Removing the deprecated `HeadersToForwardToApi` parameter.
- Application-side enforcement code and the starter template changes (outside this repository).
- Customer-managed KMS key handling for the secret (documented only).

## Requirements

### 1. ApiOriginProtection Parameter, Condition, and Rule

**User Story:** As a platform operator, I want to turn on origin protection for an API behind CloudFront with one parameter, so that I can require requests to carry a secret CloudFront adds.

#### Acceptance Criteria

1.1 THE network template SHALL define a parameter `ApiOriginProtection` of type `String` with `AllowedValues` `"true"` and `"false"` and default `"false"`.

1.2 THE network template SHALL list `ApiOriginProtection` in a new `AWS::CloudFormation::Interface` parameter group labeled `API Origin Protection`, placed after the `Routing for API Gateway` group and before the deprecated forwarding group.

1.3 THE network template SHALL define a condition `UseApiOriginProtection` that is true only when `ApiOriginProtection` is `"true"` and the condition `ApiIsBehindCloudFront` is true.

1.4 THE network template SHALL define a `Rules` section, with the standard section comment block, containing a rule that applies when `ApiOriginProtection` is `"true"` and asserts that `ApiGatewayId` is not empty and `DomainForApiGateway` is empty, with an assertion description that tells the operator how to fix the combination.

1.5 THE parameter description SHALL state that the secret `${Prefix}-${ProjectId}-${StageId}-OriginSecret` must exist in the stack's region before the stack is created or updated with `"true"`.

### 2. Origin Secret Header

**User Story:** As a platform operator, I want CloudFront to send a shared secret to the API origin, so that the application can reject requests that did not pass through the distribution.

#### Acceptance Criteria

2.1 WHEN `UseApiOriginProtection` is true, THE `ApiGatewayOrigin` entry in `CloudFrontDistribution` SHALL set `OriginCustomHeaders` to one header with `HeaderName` `X-Atlantis-Origin-Secret` and `HeaderValue` `{{resolve:secretsmanager:${Prefix}-${ProjectId}-${StageId}-OriginSecret}}`.

2.2 THE dynamic reference SHALL be versionless (no version-stage and no version-id).

2.3 WHEN `UseApiOriginProtection` is false, THE `OriginCustomHeaders` property SHALL resolve to `AWS::NoValue`.

2.4 WHEN the template is updated from the previous version with `ApiOriginProtection="false"` and the rotation revision empty, THE protection feature SHALL cause no resource change in the change set. The viewer TLS default in Requirement 6 is the only intended behavior change.

2.5 THE template SHALL NOT add a parameter for the secret name or the header name.

2.6 THE template SHALL NOT place the secret value, or any dynamic reference, in an `Outputs` entry.

### 3. Rotation Revision

**User Story:** As a platform operator, I want a way to make CloudFormation pick up a rotated secret, so that rotation reaches the distribution.

#### Acceptance Criteria

3.1 THE network template SHALL define an optional `String` parameter for the rotation revision (working name `ApiOriginSecretRevision`) with default `""`, a restrictive `AllowedPattern` (alphanumeric, dot, and dash), a maximum length of 32, and a `ConstraintDescription`, placed in the `API Origin Protection` group.

3.2 WHEN the rotation revision is empty, THE distribution `Comment` SHALL equal the current value `${Prefix}-${ProjectId}-${StageId}`.

3.3 WHEN the rotation revision is not empty, THE distribution `Comment` SHALL include the revision so that changing the parameter modifies the distribution.

3.4 THE parameter description SHALL state that updating only the secret value does not update the distribution, and that changing the revision makes CloudFormation re-resolve the secret.

### 4. Network Management Policy

**User Story:** As a platform administrator, I want the network service role to read the origin secret and nothing broader, so that stack updates resolve the reference without widening access.

#### Acceptance Criteria

4.1 THE `network-cloudfront-mgmt-policy.yml` module SHALL add a statement with `Sid` `SecretsManagerOriginSecretRead`, `Effect` `Allow`, `Action` `secretsmanager:GetSecretValue`, and `Resource` `arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${Prefix}-*-OriginSecret-??????`.

4.2 THE statement SHALL use long-form intrinsic functions (`Fn::Sub`) as required for `AWS::Include` modules.

4.3 THE module SHALL keep `CloudFrontOriginRequestPolicyRead` as it is and SHALL NOT add origin request policy create, update, or delete actions.

4.4 THE module header comment SHALL mention the new statement and its purpose where the module comment describes the managed capabilities.

### 5. Pipeline CloudFormation Role

**User Story:** As an application developer, I want my pipeline's CloudFormation role to create the origin secret for my deployment, so that the documented deployment order works without extra policies.

#### Acceptance Criteria

5.1 THE `templates/v2/modules/pipeline/cloudformation-svc-role.yml` module SHALL add a statement with `Sid` `SecretsManagerCRUDThisDeploymentOnly`, `Effect` `Allow`, actions `secretsmanager:CreateSecret`, `secretsmanager:UpdateSecret`, `secretsmanager:DeleteSecret`, `secretsmanager:PutSecretValue`, `secretsmanager:DescribeSecret`, `secretsmanager:TagResource`, and `secretsmanager:UntagResource`, and `Resource` `arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${Prefix}-${ProjectId}-${StageId}-*`.

5.2 THE module SHALL add a statement with `Sid` `SecretsManagerGetRandomPassword`, action `secretsmanager:GetRandomPassword`, and `Resource` `"*"`, with a comment that the action has no resource type.

5.3 THE module SHALL NOT grant `secretsmanager:GetSecretValue`.

5.4 THE new statements SHALL follow the placement and comment style of `SsmParameterCRUDThisDeploymentOnly`.

5.5 WHEN the module changes, THE version header of each deployed template that includes it SHALL be incremented by one PATCH and dated: `template-pipeline.yml` (currently v2.0.23) and `template-pipeline-github.yml` (currently v2.0.5). `template-pipeline-s3-source.yml` (currently v2.0.0) SHALL be bumped to v2.0.1 (PATCH bump, dated). `template-pipeline-build-only.yml` does not include the module and SHALL NOT change.

### 6. Viewer Minimum TLS Version

**User Story:** As a platform operator, I want to choose the minimum TLS version for viewers on a custom domain, so that distributions do not accept TLS 1.0 by default.

#### Acceptance Criteria

6.1 THE network template SHALL define a parameter `ViewerMinimumTlsVersion` of type `String`, default `TLSv1.2_2021`, with `AllowedValues` `TLSv1`, `TLSv1_2016`, `TLSv1.1_2016`, `TLSv1.2_2018`, `TLSv1.2_2019`, `TLSv1.2_2021`, `TLSv1.2_2025`, and `TLSv1.3_2025`, placed in the `Routing for CloudFront` group.

6.2 WHEN `CreateDnsRecordForCloudFront` is true, THE `ViewerCertificate` SHALL set `MinimumProtocolVersion` to `ViewerMinimumTlsVersion`.

6.3 WHEN `CreateDnsRecordForCloudFront` is false, THE `ViewerCertificate` SHALL NOT set `MinimumProtocolVersion`, because CloudFront fixes the policy at `TLSv1` for the default certificate.

6.4 THE parameter description SHALL state that it applies only with an alias certificate, that clients without TLS 1.2 stop connecting when the default applies, and that `TLSv1` restores the previous behavior.

6.5 IF the repository's `cfn-lint` version rejects a `TLSv1.2_2025` or `TLSv1.3_2025` value, THEN THE implementation SHALL record the finding and either upgrade `cfn-lint` or add a documented, narrowly scoped ignore.

### 7. Deprecate Origin-Event Function Parameters

**User Story:** As a platform operator, I want the template to stop pretending CloudFront Functions run on origin events, so that the parameters are not misleading.

#### Acceptance Criteria

7.1 THE parameters `CloudFrontStaticFunctionOriginRequest`, `CloudFrontStaticFunctionOriginResponse`, `CloudFrontApiFunctionOriginRequest`, and `CloudFrontApiFunctionOriginResponse` SHALL remain defined with their current default, `AllowedPattern`, and metadata group membership.

7.2 EACH of the four descriptions SHALL begin with `DEPRECATED` and SHALL state that CloudFront Functions run only on viewer-request and viewer-response events and that the value is ignored.

7.3 THE distribution SHALL NOT include `origin-request` or `origin-response` entries in `FunctionAssociations` for any behavior.

7.4 WHERE a condition (`HasStaticFunctionOriginRequest`, `HasStaticFunctionOriginResponse`, `HasApiFunctionOriginRequest`, `HasApiFunctionOriginResponse`) is no longer referenced, THE template SHALL either remove it or keep it with a comment, so that `cfn-lint` passes without new suppressions.

7.5 THE viewer-request and viewer-response associations SHALL behave as before.

### 8. Viewer Headers Unchanged

#### Acceptance Criteria

8.1 THE API behaviors (the default behavior when the API is the root, and the `/${PathApi}/*` behavior) SHALL keep `OriginRequestPolicyId` `b689b0a8-53d0-40ab-baf2-68738e2966ac`.

8.2 THE template SHALL NOT create an `AWS::CloudFront::OriginRequestPolicy` resource.

### 9. Template Version and Header

#### Acceptance Criteria

9.1 THE network template header SHALL read `# Version: v0.2.0/<date of the change>`.

9.2 THE template header comments SHALL otherwise not change, except where a steering document requires it.

9.3 THE template SHALL keep the section comment blocks, add one for `Rules`, and keep the existing subsection comment style.

9.4 THE template SHALL pass `cfn-lint` with the repository's configuration.

### 10. Tests

#### Acceptance Criteria

10.1 `tests/test_network_template_unit.py` SHALL be updated so the version assertion expects `v0.2.0`, and its parameter, condition, and group lists include the new items.

10.2 NEW unit tests SHALL verify, for the network template: the `ApiOriginProtection` parameter definition and group; the `UseApiOriginProtection` condition; the `Rules` assertion; the `OriginCustomHeaders` shape and `AWS::NoValue` default; the versionless dynamic reference; the rotation revision parameter and its effect on `Comment` (empty and non-empty); the `ViewerMinimumTlsVersion` parameter, allowed values, and condition; the four deprecated parameters still present with `DEPRECATED` descriptions; no origin-event entries in `FunctionAssociations`; the API behaviors still using the managed policy ID; and no `AWS::CloudFront::OriginRequestPolicy` resource.

10.3 `tests/test_network_cloudfront_mgmt_policy_unit.py` SHALL verify `SecretsManagerOriginSecretRead` (Sid, effect, single action, resource pattern) and that no origin request policy create, update, or delete action was added.

10.4 A new unit test file SHALL verify the `cloudformation-svc-role.yml` statements (Sids, exact action lists, resource patterns, `GetRandomPassword` on `"*"`, and absence of `GetSecretValue`) and the PATCH increments for `template-pipeline.yml` and `template-pipeline-github.yml`.

10.5 THE existing parameter and condition lists in `tests/test_network_template_unit.py` and `tests/test_network_template_property.py` that reference the function parameters SHALL be updated for any condition removed under 7.4.

10.6 THE test suite SHALL stay fast (the total run under 30 seconds) and SHALL NOT add new property-based tests, per the repository's testing guidelines.

10.7 THE CloudFormation template validation suite (`tests/test_cfn_templates.py`) SHALL pass for all modified templates and modules.

### 11. Documentation

#### Acceptance Criteria

11.1 THE network template README (`docs/templates/v2/network/template-network-route53-cloudfront-s3-apigw-README.md`) SHALL document: the new parameter group and parameters; the Rule; the origin header; deployment order; rotation steps; troubleshooting entries for `AccessDenied` on `secretsmanager:GetSecretValue`, secret not found, and rotation not applied; the deprecated function parameters; the TLS parameter; a version history entry; and the existing blockquotes SHALL be preserved.

11.2 A new page `docs/end-user/api-ingress-standard.md` SHALL be added and linked from `docs/README.md`, `docs/end-user/README.md`, and the network template README. It SHALL cover:
- Regional API behind the distribution as the recommended pattern.
- On a Regional API, `requestContext.identity.sourceIp` and `CloudFront-Viewer-Address` both carry the viewer address and a viewer cannot spoof either (verified for REST APIs; HTTP APIs and IPv6 viewers untested).
- On an edge-optimized API, neither is usable (`sourceIp` is an edge address, the header is dropped) and `X-Forwarded-For` has the form `viewer, edge, edge`.
- A viewer-sent `X-Forwarded-For` is passed through, so applications must parse it right to left.
- The origin secret pattern: generation with `GenerateSecretString`, constant-time comparison, never logging the header, rejecting when the secret is missing, and using a status other than 403 or 404 for a mismatch.
- The rotation sequence: application accepts old and new; put the new value; update the network stack with a changed revision; wait for `Deployed` plus a margin; remove the old value.
- Who can read the value (any principal with `cloudfront:GetDistribution` or `GetDistributionConfig`) and the KMS note (`kms:Decrypt` for a customer-managed key).
- The distribution-wide 403/404 `CustomErrorResponses` rewrite when a static origin exists, which also applies to API responses.
- Optional enforcement with a web ACL header match on the API stage.

11.3 THE README for each affected pipeline template (`template-pipeline-README.md`, `template-pipeline-github-README.md`, and `template-pipeline-s3-source-README.md`) SHALL document the new Secrets Manager statements wherever it documents the CloudFormation role's permissions.

11.4 WHERE documentation lists the network management policy statements (service-role or account README, `templates/v2/modules/README.md`), THE new statement SHALL be added.

11.5 THE category READMEs (`docs/templates/v2/network/README.md`, `docs/templates/v2/pipeline/README.md`) SHALL reflect new versions and links.

11.6 THE documentation SHALL state the deployment order: redeploy the service role (or `prefix-based-infrastructure`), update the pipeline stack, create the secret in the application stack, update the network stack with `ApiOriginProtection="true"`, then enable enforcement in the application.

### 12. Changelog

#### Acceptance Criteria

12.1 `CHANGELOG.md` SHALL get entries under `## v0.0.46 (unreleased)` only, without altering existing text, linking this spec.

12.2 THE entries SHALL include: Added (`ApiOriginProtection`, rotation revision, the two management statements, the ingress page); Changed (`ViewerMinimumTlsVersion`, the documentation of the 403/404 rewrite); Deprecated (the four function parameters); Breaking Changes (the TLS default for custom-domain distributions, with the `TLSv1` opt-out).

12.3 THE entries SHALL include update-time notes: redeploy the network service role (or `prefix-based-infrastructure`, `template-service-role-network-cloudfront.yml`, or `template-service-role-network-full.yml`) before updating the network stack; the pipeline role change reaches an application at its next pipeline stack update.

### 13. Release Verification

#### Acceptance Criteria

13.1 BEFORE release, a change set of the new network template against the previous template, with `ApiOriginProtection="false"`, an empty rotation revision, and the same TLS value as the deployed distribution (`TLSv1`), SHALL show no change for the protection feature (check V6).

13.2 THE temporary verification stacks and grants from the plan phase SHALL NOT remain in the account. The managed policy `XCME-CfnSvcRole-Network-CloudFront-Mgmt` and the role `xcme-Worker-cross-acct-test-CloudFormationSvcRole` SHALL contain no test statements.

## Open Items to Carry into Design

- The exact `Comment` format when the revision is set (for example a suffix).
- Whether any of the four function-origin conditions can be removed without disturbing existing tests (7.4).
- Whether `cfn-lint` in `.venv` accepts the 2025 TLS values (6.5).
- Location and wording of the ingress page (11.2); the path given here is the planned default.
