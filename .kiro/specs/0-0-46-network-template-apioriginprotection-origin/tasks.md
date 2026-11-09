# Implementation Plan

Tasks — v0.0.46 Network Template API Origin Protection

## Overview

Implementation task list for [design.md](design.md), derived from [requirements.md](requirements.md) and the locked [PLAN.md](PLAN.md). Three source files change: the network template, `network-cloudfront-mgmt-policy.yml`, and `cloudformation-svc-role.yml`. Two pipeline templates take a PATCH bump because they include the pipeline module.

Notes for the implementer:

- Tasks in the same wave that edit the same file are applied in order.
- The network template is at v0.1.0 (PATCH = 0, development mode). Moving to **v0.2.0** is a deliberate choice from the source issue (Requirement 9.1), not an automatic increment.
- Use long-form intrinsic functions (`Fn::Sub`, `Ref`) in both modules. The network template keeps its short-form style.
- Do not modify existing header comments, section comments, or existing README blockquotes beyond what a task states.
- `template-pipeline-s3-source.yml` is at v2.0.0 (not v0.0.0) and includes the module, so it is bumped to **v2.0.1/<date>** (done in 1.4); task 7.6 must assert `v2.0.1` for it instead of `v0.0.0`, and task 9.3 also updates the s3-source README version header.
- Unit tests only. Add no new property-based tests (testing guidelines).
- The temporary verification stacks and grants from the plan phase must not remain in the test account (see 11.2).

## Tasks

### 1. Version management

- [x] 1.1 `templates/v2/network/template-network-route53-cloudfront-s3-apigw.yml`: change the header to `# Version: v0.2.0/<date of the change>` and make no other header comment change _(R9.1, R9.2)_
- [x] 1.2 `templates/v2/pipeline/template-pipeline.yml`: PATCH > 0, so change `# Version: v2.0.23/2026-08-15` to `v2.0.24/<date of the change>` _(R5.5)_
- [x] 1.3 `templates/v2/pipeline/template-pipeline-github.yml`: change `# Version: v2.0.5/2026-08-15` to `v2.0.6/<date of the change>` _(R5.5)_
- [x] 1.4 Confirm `template-pipeline-s3-source.yml` stays `v0.0.0` and `template-pipeline-build-only.yml` stays `v2.0.7` (the latter does not include the module) _(R5.5)_

### 2. Network template: parameters and metadata

- [x] 2.1 Add parameter `ViewerMinimumTlsVersion` (default `TLSv1.2_2021`, the eight allowed values in the design order, description and `ConstraintDescription` from the design) after `AcmCertificateArnForCloudFront`, and add it to the `Routing for CloudFront` metadata group after `AcmCertificateArnForCloudFront` _(R6.1, R6.4, design Network Template, D3)_
- [x] 2.2 Add a parameters subsection `API Origin Protection` after the API Gateway routing parameters and before `Forwarding for API Gateway behind CloudFront`, with `ApiOriginProtection` (`"true"`/`"false"`, default `"false"`) and `ApiOriginSecretRevision` (default `""`, pattern `^[a-zA-Z0-9.-]{0,32}$`); add the metadata group `API Origin Protection` after `Routing for API Gateway` and before the deprecated forwarding group _(R1.1, R1.2, R1.5, R3.1, R3.4)_
- [x] 2.3 Rewrite the `Description` of `CloudFrontStaticFunctionOriginRequest`, `CloudFrontStaticFunctionOriginResponse`, `CloudFrontApiFunctionOriginRequest`, and `CloudFrontApiFunctionOriginResponse` to begin with `DEPRECATED`, state that CloudFront Functions run only on viewer events and the value is ignored, and keep the words "static" or "API" so the existing description tests pass; leave `Type`, `Default`, `AllowedPattern`, `ConstraintDescription`, and group membership unchanged _(R7.1, R7.2)_

### 3. Network template: conditions and rules

- [x] 3.1 Add conditions `UseApiOriginProtection` (`!And` of `ApiOriginProtection` equals `"true"` and `!Condition ApiIsBehindCloudFront`) and `HasApiOriginSecretRevision`; delete `HasStaticFunctionOriginRequest`, `HasStaticFunctionOriginResponse`, `HasApiFunctionOriginRequest`, and `HasApiFunctionOriginResponse` once 4.4 removes their last references (apply 4.4 first if the linter complains) _(R1.3, R7.4, design D2)_
- [x] 3.2 Add a `Rules` section between `Conditions` and `Resources` with the standard section comment block and the rule `ApiOriginProtectionRequiresApiBehindCloudFront` (rule condition `ApiOriginProtection` equals `"true"`; assertion `ApiGatewayId` not empty and `DomainForApiGateway` empty; clear `AssertDescription`) _(R1.4, R9.3, design D6)_

### 4. Network template: distribution

- [x] 4.1 Change `CloudFrontDistribution` `DistributionConfig.Comment` to `!If [HasApiOriginSecretRevision, !Sub "${Prefix}-${ProjectId}-${StageId} rev ${ApiOriginSecretRevision}", !Sub "${Prefix}-${ProjectId}-${StageId}"]` _(R3.2, R3.3, design D1)_
- [x] 4.2 Add `OriginCustomHeaders` to the `ApiGatewayOrigin` entry: `!If [UseApiOriginProtection, [{HeaderName: X-Atlantis-Origin-Secret, HeaderValue: !Sub '{{resolve:secretsmanager:${Prefix}-${ProjectId}-${StageId}-OriginSecret}}'}], !Ref AWS::NoValue]`; no version segments in the reference; add no output, parameter, or resource for the secret _(R2.1, R2.2, R2.3, R2.5, R2.6, design D7)_
- [x] 4.3 Add `MinimumProtocolVersion: !If [CreateDnsRecordForCloudFront, !Ref ViewerMinimumTlsVersion, !Ref AWS::NoValue]` to `ViewerCertificate` _(R6.2, R6.3)_
- [x] 4.4 Remove the `origin-request` and `origin-response` items from all four `FunctionAssociations` lists (DefaultCacheBehavior static and API branches, the static path behavior, and the API path behavior), leaving the viewer-request and viewer-response items unchanged _(R7.3, R7.5)_
- [x] 4.5 Confirm both API behaviors still use `OriginRequestPolicyId: b689b0a8-53d0-40ab-baf2-68738e2966ac` and that no `AWS::CloudFront::OriginRequestPolicy` resource exists in the template _(R8.1, R8.2)_

### 5. Modules

- [x] 5.1 `templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml`: add `SecretsManagerOriginSecretRead` (`secretsmanager:GetSecretValue` on `arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${Prefix}-*-OriginSecret-??????` through `Fn::Sub`) after `AcmCertificateRead`, with the explanatory comment from the design; update the module comment block only, **not** the `Description` property (replacement on update); leave `CloudFrontOriginRequestPolicyRead` as is and add no origin request policy create, update, or delete action _(R4.1 to R4.4, design D5)_
- [x] 5.2 `templates/v2/modules/pipeline/cloudformation-svc-role.yml`: add `SecretsManagerCRUDThisDeploymentOnly` (seven actions, resource `...secret:${Prefix}-${ProjectId}-${StageId}-*`) and `SecretsManagerGetRandomPassword` (`Resource: "*"`, with comment) after `SsmParameterCRUDThisDeploymentOnly`; grant no `GetSecretValue` _(R5.1 to R5.4)_

### 6. Tests: update existing

- [x] 6.1 `tests/test_network_template_unit.py`: rename `test_template_version_is_v0_1_0` and expect `# Version: v0.2.0/` _(R10.1)_
- [x] 6.2 `tests/test_network_template_unit.py`: reduce `STATIC_CONDITIONS`, `API_CONDITIONS`, and `ALL_CONDITIONS` to the four viewer conditions; replace `CONDITION_TO_PARAM = dict(zip(ALL_CONDITIONS, ALL_FUNCTION_PARAMS))` with an explicit dictionary of the four viewer conditions to their parameters; set `EVENT_TYPES = ['viewer-request', 'viewer-response']` _(R10.1, R10.5, design Test Design)_
- [x] 6.3 `tests/test_network_template_unit.py`: change the four item-count tests (`test_static_branch_has_4_items`, `test_api_branch_has_4_items`, `test_static_path_has_4_items`, `test_api_path_has_4_items`) to expect 2 items and rename them; the four event-type tests now expect the viewer-only list _(R10.1)_
- [x] 6.4 `tests/test_network_template_unit.py`: update `test_*_references_*_params`, `test_*_uses_*_conditions`, and `test_no_*_refs_*` so they check only the viewer parameters and conditions _(R10.1)_
- [x] 6.5 `tests/test_network_template_unit.py`: in `TestCloudFrontFunctionConditions`, keep the existence and `!Not`/`!Equals` tests for the four viewer conditions and add a test that the four origin conditions are absent _(R7.4, R10.1)_
- [x] 6.6 `tests/test_network_template_property.py`: confirm no test depends on the removed conditions or origin-event items; change only what breaks, and add no new property tests _(R10.5, R10.6)_

### 7. Tests: add new

- [x] 7.1 `tests/test_network_template_unit.py`: add `TestApiOriginProtectionParameter`, `TestApiOriginProtectionMetadata` (group position), `TestApiOriginProtectionCondition`, and `TestApiOriginProtectionRule` per the design _(R1.1 to R1.5, R10.2)_
- [x] 7.2 `tests/test_network_template_unit.py`: add `TestOriginCustomHeaders` (shape, versionless `!Sub` string, `AWS::NoValue` default, only the API origin carries the property, no secret in `Outputs`) and `TestApiOriginSecretRevision` (default, pattern, max length, both `Comment` strings) _(R2.1 to R2.6, R3.1 to R3.4, R10.2)_
- [x] 7.3 `tests/test_network_template_unit.py`: add `TestViewerMinimumTlsVersion` (default, eight allowed values, group, `MinimumProtocolVersion` expression) _(R6.1 to R6.3, R10.2)_
- [x] 7.4 `tests/test_network_template_unit.py`: add `TestApiOriginRequestPolicyUnchanged` (both behaviors keep the managed ID, no `AWS::CloudFront::OriginRequestPolicy`) and `TestDeprecatedFunctionParameters` (`DEPRECATED` descriptions, unchanged defaults and pattern, no `origin-request` or `origin-response` anywhere under `FunctionAssociations`) _(R7.1 to R7.3, R8.1, R8.2, R10.2)_
- [x] 7.5 `tests/test_network_cloudfront_mgmt_policy_unit.py`: add `TestSecretsManagerOriginSecretRead` (Sid, effect, single action, resource string; `CloudFrontOriginRequestPolicyRead` unchanged; no create, update, or delete origin request policy action anywhere in the policy) _(R4.1 to R4.3, R10.3)_
- [x] 7.6 Create `tests/test_pipeline_cfn_svc_role_secrets_unit.py`: statements by `Sid` with exact actions, effects, and resources; no `secretsmanager:GetSecretValue`; the size guard that renders each `Fn::Sub` with worst-case-length values and asserts the inline policy is under 10,240 characters; version assertions `v2.0.24`, `v2.0.6`, `v0.0.0` (s3-source), and `v2.0.7` (build-only) _(R5.1 to R5.5, R10.4, design D8)_

### 8. Validation

- [x] 8.1 Run `.venv/bin/cfn-lint` on the network template and confirm no new findings against the baseline (two W8001, W1001, W1028 only); confirm the two modules still pass the repository validation _(R9.4)_
- [x] 8.2 Run `.venv/bin/python -m pytest tests/ -q` and confirm green and under 30 seconds in total _(R10.6, R10.7)_
- [x] 8.3 Run `.venv/bin/python scripts/cfn_lint_runner.py --templates-dir templates/v2 --verbose` (as `buildspec.yml` does) and confirm no errors _(R10.7)_

### 9. Documentation (required final implementation task)

- [x] 9.1 Update `docs/templates/v2/network/template-network-route53-cloudfront-s3-apigw-README.md`: header version and date; the new parameter group and parameters in the steering table format; `ViewerMinimumTlsVersion`; `DEPRECATED` notes on the four function parameters; the `Rules` section; `OriginCustomHeaders` under `CloudFrontDistribution`; the conditions list; the management-policy statement text where it lists the network role's statements; deployment order and rotation steps; troubleshooting entries (`AccessDenied` on `GetSecretValue`, secret not found, rotation not applied, 403/404 rewrite); version history entry; link to the ingress page; preserve every existing blockquote _(R11.1, R11.4, R11.6)_
- [x] 9.2 Create `docs/end-user/api-ingress-standard.md` with the content listed in Requirement 11.2 and the client-IP table from the design (verified REST results, untested HTTP API and IPv6 noted); link it from `docs/README.md`, `docs/end-user/README.md`, and the network template README _(R11.2)_
- [x] 9.3 Update the CloudFormation role statement lists in `docs/templates/v2/pipeline/template-pipeline-README.md` (near the `CloudFormationSvcRole` section), `template-pipeline-github-README.md`, and `template-pipeline-s3-source-README.md`, and the version headers of the first two _(R11.3)_
- [x] 9.4 Update `docs/templates/v2/network/README.md` and `docs/templates/v2/pipeline/README.md` version references and summaries _(R11.5)_
- [x] 9.5 Verify every parameter, condition, resource, and Rule in the network README matches the final template, and that all pre-existing blockquotes are intact _(R11.1)_

### 10. Changelog

- [x] 10.1 Add entries under `## v0.0.46 (unreleased)` only, without altering existing text: Added (`ApiOriginProtection`, rotation revision, two management statements, ingress page), Changed (`ViewerMinimumTlsVersion`, 403/404 documentation), Deprecated (four function parameters), Breaking Changes (TLS default and the `TLSv1` opt-out), with the update-time notes (redeploy the network service role or `prefix-based-infrastructure` first; the pipeline role change arrives at the next pipeline stack update); link this spec _(R12.1 to R12.3)_

### 11. Release verification (manual)

- [~] 11.1 Create a change set of the new network template against a stack deployed from v0.1.0 with `ApiOriginProtection="false"`, an empty revision, and `ViewerMinimumTlsVersion="TLSv1"` and confirm no resource change; a second change set with the default TLS value must show only the `MinimumProtocolVersion` modification on `CloudFrontDistribution`. Confirm the account and region with the user before creating anything, and delete test stacks afterward _(R13.1)_
- [x] 11.2 Confirm the test account holds no leftover verification artifacts: no `xcme-zz-*` stacks, distributions, APIs, or secrets, and no test statements on `XCME-CfnSvcRole-Network-CloudFront-Mgmt` or on `xcme-Worker-cross-acct-test-CloudFormationSvcRole`. **Known open item:** `CloudFormationRolePolicy` on that role still contained `SecretsManagerCRUDThisDeploymentOnly` when this list was written _(R13.2)_

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "1.4"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.3", "5.1", "5.2"] },
    { "id": 2, "tasks": ["3.2", "4.1", "4.2", "4.3", "4.4", "4.5"] },
    { "id": 3, "tasks": ["3.1"] },
    { "id": 4, "tasks": ["6.1", "6.2", "6.3", "6.4", "6.5", "6.6"] },
    { "id": 5, "tasks": ["7.1", "7.2", "7.3", "7.4", "7.5", "7.6"] },
    { "id": 6, "tasks": ["8.1", "8.2", "8.3"] },
    { "id": 7, "tasks": ["9.1", "9.2", "9.3", "9.4", "9.5"] },
    { "id": 8, "tasks": ["10.1"] },
    { "id": 9, "tasks": ["11.1", "11.2"] }
  ]
}
```
