# Requirements Document

**Spec:** v0.0.44 Pre-Existing Test Failure Remediation

## Introduction

The test suite currently reports 151 failing tests. Investigation (see [report.md](./report.md)) confirmed that **149 of these are pre-existing stale tests** that fail against the committed `v0.0.43` baseline (commit `8cf69d2`) on files that are clean and committed. In every case the CloudFormation templates and modules reflect deliberate, intended, already-committed changes, and the tests were simply never updated to match. No template is broken.

This spec updates the three affected test files so the suite once again reflects the true, intended behavior of the templates. It is a **test-only** change: no CloudFormation template, module, parameter, resource, output, or documentation file is modified.

The 149 in-scope failures fall into exactly three categories:

1. **Pipeline notification tests (147)** — `tests/test_pipeline_notifications_unit.py`. The three EventBridge notification rules were refactored (commit `5c2cbe9`) into `AWS::Include` modules under `templates/v2/modules/pipeline/`. The parent pipeline templates now contain only an `Fn::Transform` reference, so the test's assumption that the rule body lives inline at `Resources.<Rule>.Properties.Targets[0]` no longer holds (`KeyError: 'Properties'`). The modules also use long-form intrinsics (`Fn::Sub`), while the test helper reads the shorthand `!Sub` key.
2. **S3 artifacts policy structure (1)** — `tests/test_s3_artifacts_bucket_policy_unit.py::TestPreservationStructure::test_exactly_three_statements`. The cross-account promotion feature added an optional conditional fourth statement (`Fn::If [HasPromotionSourceAccounts, AllowCrossAccountPromotionWrite, AWS::NoValue]`) to `templates/v2/modules/account-wide/s3-artifacts-bucket-policy.yml`. Static YAML parsing now yields four statements; the test hard-codes three.
3. **prefix-based-infrastructure.yml version (1)** — `tests/test_consuming_templates_artifacts_params_unit.py::TestHeaderVersions`. The header of `templates/v2/account/prefix-based-infrastructure.yml` was deliberately renumbered to `v2.0.1/2026-08-20` (commit `22ef057`), but the test's `EXPECTED_VERSIONS` map still expects `v0.0.2`.

The 149 failures were reproduced and bounded exactly:

```
pytest tests/test_pipeline_notifications_unit.py \
       tests/test_s3_artifacts_bucket_policy_unit.py::TestPreservationStructure::test_exactly_three_statements \
       tests/test_consuming_templates_artifacts_params_unit.py::TestHeaderVersions::test_header_version_line
# => 149 failed, 2 passed
```

## Confirmed decisions

The following were confirmed with the maintainer before writing this document:

1. `v2.0.1/2026-08-20` is the intended header for `prefix-based-infrastructure.yml`; the test is the stale party and will be updated to expect `v2.0.1`.
2. For `TestTemplateParity`, the replacement assertion SHALL verify that all three parent pipeline templates reference the identical shared module `Location`, rather than comparing full module contents.
3. The two out-of-scope failures (Bedrock default flip and the network `HasV1Destination` logging property tests) are left to their originating v0.0.44 specs and are NOT addressed here.

## Relationship to other v0.0.44 work

The two excluded failures belong to sibling specs: the `EnableBedrockInvocationLogs` default flip (`0-0-44-bedrock-invocation-logs-default-off`) and the CloudFront logging-version / log-prefix work (`0-0-44-bedrock-media-and-log-prefix-segmentation`). Those specs own the corresponding test updates as their final "update tests" task. This spec touches none of the files owned by those specs.

---

## Requirements

### Requirement 1: Repair the pipeline notification tests against the module architecture

**User Story:** As a maintainer, I want the pipeline notification tests to read the notification rule bodies from their `AWS::Include` module files, so that the suite validates the current module-based architecture instead of the removed inline structure.

#### Acceptance Criteria

1. THE test helpers in `tests/test_pipeline_notifications_unit.py` that currently read `template["Resources"][rule_name]["Properties"]["Targets"][0]` SHALL instead load the corresponding module snippet from `templates/v2/modules/pipeline/` and read its top-level `Properties.Targets[0]`.
2. THE rule-to-module mapping SHALL be: `PipelineStartedRule` → `pipeline-notification-started-rule.yml`, `PipelineSucceededRule` → `pipeline-notification-succeeded-rule.yml`, `PipelineFailedRule` → `pipeline-notification-failed-rule.yml`.
3. THE helper that extracts the `InputTemplate` string SHALL read the long-form `Fn::Sub` key produced by the module (and MAY also accept a `!Sub` key for robustness), rather than assuming `!Sub`.
4. THE existing content assertions (valid JSON with exactly `Subject` and `Message` keys, required message labels, subject format, no stray JSON artifacts, folded-strip YAML block scalar, no trailing newline, and the failed-message call-to-action) SHALL be preserved in intent and SHALL pass against the module content unchanged.
5. `TestTemplateParity` SHALL be updated to assert that all three parent pipeline templates (`template-pipeline.yml`, `template-pipeline-github.yml`, `template-pipeline-build-only.yml`) reference the identical shared module `Location` for each notification rule, in place of comparing inline `InputTemplate`/`InputPathsMap`/labels across templates.
6. WHEN the full set of tests in `tests/test_pipeline_notifications_unit.py` is run, THEN all 147 previously failing tests SHALL pass (or be restructured into equivalent passing tests that preserve the original coverage intent), with no test skipped to achieve this.
7. THE changes SHALL be confined to `tests/test_pipeline_notifications_unit.py`; NO template or module file SHALL be modified.

### Requirement 2: Accept the optional promotion statement in the S3 artifacts policy structure test

**User Story:** As a maintainer, I want the artifacts-bucket-policy structure test to recognize the optional cross-account promotion statement, so that it validates the current intended policy shape.

#### Acceptance Criteria

1. THE `TestPreservationStructure` test in `tests/test_s3_artifacts_bucket_policy_unit.py` SHALL assert that the three unconditional statements with Sids `DenyNonSecureTransportAccess`, `WhitelistedGet`, and `WhitelistedPut` are present.
2. THE test SHALL recognize the optional fourth entry as an `Fn::If` on the `HasPromotionSourceAccounts` condition whose true branch has Sid `AllowCrossAccountPromotionWrite` and whose false branch is `Ref: AWS::NoValue`.
3. THE test SHALL NOT fail solely because the statement list length is four rather than three; the count assertion SHALL be expressed in terms of the three base statements plus the optional conditional statement.
4. THE test name and/or docstring SHALL be updated to describe the current contract (three base statements plus an optional promotion statement) rather than "exactly three statements".
5. THE other `TestPreservationStructure` assertions (resource-level `Condition` is `EnableS3ArtifactsBucket`, `PolicyDocument.Version` is `2012-10-17`, `PolicyDocument.Id` is `SSEAndSSLPolicy`) SHALL remain unchanged and continue to pass.
6. THE changes SHALL be confined to `tests/test_s3_artifacts_bucket_policy_unit.py`; NO template or module file SHALL be modified.

### Requirement 3: Align the expected version for prefix-based-infrastructure.yml

**User Story:** As a maintainer, I want the consuming-templates version test to expect the intended header version, so that the deliberate version renumber is reflected in the suite.

#### Acceptance Criteria

1. THE `EXPECTED_VERSIONS` mapping in `tests/test_consuming_templates_artifacts_params_unit.py` SHALL set the expected version for `prefix-based-infrastructure.yml` to `v2.0.1`.
2. THE expected versions for `template-service-role-pipeline.yml` (`v0.0.19`) and `template-service-role-storage.yml` (`v0.0.4`) SHALL remain unchanged.
3. WHEN `TestHeaderVersions::test_header_version_line[prefix-based-infrastructure.yml]` is run, THEN it SHALL pass against the committed header `# Version: v2.0.1/2026-08-20`.
4. THE changes SHALL be confined to `tests/test_consuming_templates_artifacts_params_unit.py`; NO template file SHALL be modified.

### Requirement 4: Full-suite verification

**User Story:** As a maintainer, I want to confirm the remediation clears exactly the 149 in-scope failures and introduces no new ones, so that the suite state is well understood.

#### Acceptance Criteria

1. WHEN `pytest tests/` is run after the changes, THEN the 149 previously failing in-scope tests SHALL pass.
2. THE only remaining failures after the changes SHALL be the two documented out-of-scope failures owned by the sibling v0.0.44 specs (the Bedrock `test_default_is_true` assertion and the two `test_network_template_property.py` logging-property tests), and no other test SHALL regress.
3. THE previously passing count (742) SHALL not decrease as a result of these changes, except for tests intentionally renamed or restructured under Requirements 1–3 whose coverage intent is preserved.
4. THE test suite SHALL continue to complete within the performance envelope defined by the repository testing guidelines (unit-style, fast; total suite well under the guideline ceiling).

### Requirement 5: Change governance

**User Story:** As a maintainer, I want the remediation recorded appropriately, so that the change is traceable without over-documenting a test-only change.

#### Acceptance Criteria

1. NO CloudFormation template, module, or end-user documentation under `docs/` SHALL be modified by this spec.
2. THE work SHALL be limited to the three test files named in Requirements 1, 2, and 3.
3. IF a CHANGELOG entry is added, THEN it SHALL be placed under the `v0.0.44 (unreleased)` section and SHALL reference this spec; per the changelog guidelines, test-only changes are optional to record, so omission is acceptable.

## Non-goals / out of scope

1. Any modification to CloudFormation templates, modules, or their behavior.
2. The two out-of-scope failures owned by sibling specs (`0-0-44-bedrock-invocation-logs-default-off` and `0-0-44-bedrock-media-and-log-prefix-segmentation`).
3. Adding new test coverage beyond what is needed to restore and preserve the existing intent of the affected tests.
4. Introducing property-based tests; per the repository testing guidelines these repairs remain fast unit-style assertions.
5. Refactoring unrelated tests or shared test utilities beyond what the three named files require.

## Constraints and assumptions

1. The CloudFormation templates and modules are the source of truth; the failures are stale tests, so all fixes live in test files only.
2. `AWS::Include` modules must use long-form intrinsics, so the pipeline notification module bodies expose `Fn::Sub` (not `!Sub`); the shared test loader parses YAML shorthand tags into single-key dicts keyed by the tag.
3. All three parent pipeline templates reference the same shared notification module files, so InputTemplate/InputPathsMap parity across parents is guaranteed by construction and is validated via identical `Location` references.
4. The `s3-artifacts-bucket-policy.yml` promotion statement resolves to `AWS::NoValue` when `HasPromotionSourceAccounts` is false, preserving the original three-statement runtime behavior; the fourth entry is only present in the static (unresolved) template.
5. The two out-of-scope failures will remain until their originating specs land; their continued presence after this spec is expected, not a regression.
