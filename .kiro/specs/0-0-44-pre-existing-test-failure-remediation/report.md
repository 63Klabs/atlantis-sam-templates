# Pre-Existing Test Failure Investigation Report

Version context: v0.0.44 (unreleased)
Baseline: commit `8cf69d2` (v0.0.43 release), current `HEAD` of `dev`
Status: Investigation complete — proposed solution below, awaiting decision before implementation

## Summary

The test suite reports **151 failing tests** on the current working tree. Of these, **149 are genuinely pre-existing** (they fail against the committed `v0.0.43` baseline, on files that are clean/committed) and fall into exactly the three categories called out in the request:

| # | Category | Failing tests | Test file | Root cause | Fault |
|---|----------|--------------:|-----------|------------|-------|
| 1 | Pipeline notifications | 147 | `test_pipeline_notifications_unit.py` | Notification EventBridge rules were refactored into `AWS::Include` modules; the test still reads inline `Properties` from the parent template | Stale test |
| 2 | S3 artifacts policy structure | 1 | `test_s3_artifacts_bucket_policy_unit.py::TestPreservationStructure::test_exactly_three_statements` | Cross-account promotion feature added a conditional 4th policy statement | Stale test |
| 3 | prefix-based-infrastructure.yml version | 1 | `test_consuming_templates_artifacts_params_unit.py::TestHeaderVersions` | Template header was deliberately renumbered `v0.0.x` → `v2.0.1`; test still expects `v0.0.2` | Stale test |

**Key finding: all 149 failures are stale tests, not template regressions.** In every case the CloudFormation templates reflect deliberate, intended changes that were committed without updating the corresponding tests. No template is broken.

The remaining **2 failures are out of scope** for this report — they are produced by *uncommitted, in-progress* v0.0.44 work (see [Out of scope](#out-of-scope-2-additional-failures) below), not by the committed baseline.

## Investigation method

1. Ran the full suite: `pytest tests/` → 151 failed, 742 passed.
2. Grouped failures by test file/class to identify the three clusters.
3. Confirmed each in-scope failure touches only files that are **clean/committed** at `HEAD` (via `git status`), proving the failures pre-date the current working changes.
4. Read the current templates/modules to determine whether the template or the test is the source of truth.
5. Traced the divergence to specific commits (`5c2cbe9` module refactor, `22ef057` version renumber, and the promotion feature).

Scope confirmation:

```
pytest tests/test_pipeline_notifications_unit.py \
       tests/test_s3_artifacts_bucket_policy_unit.py::TestPreservationStructure::test_exactly_three_statements \
       tests/test_consuming_templates_artifacts_params_unit.py::TestHeaderVersions::test_header_version_line
# => 149 failed, 2 passed
```

---

## Category 1 — Pipeline notification tests (147 failures)

### What fails

Every test in `test_pipeline_notifications_unit.py` fails, the first error being:

```
KeyError: 'Properties'
  rule = template["Resources"][rule_name]
  target = rule["Properties"]["Targets"][0]   # <-- KeyError
```

Affected classes: `TestInputTemplateJsonStructure` (36), `TestMessageBodyLabels` (36), `TestNoJsonArtifacts` (27), `TestSubjectFormat` (18), `TestYamlBlockScalar` (12), `TestCallToAction` (9), `TestTemplateParity` (9).

### Root cause

Commit `5c2cbe9` ("updated pipelines to use modules") moved the body of the three notification EventBridge rules out of the parent pipeline templates and into shared module snippets consumed via `Fn::Transform: AWS::Include`.

The parent templates (`template-pipeline.yml`, `template-pipeline-github.yml`, `template-pipeline-build-only.yml`) now contain only a transform reference — there is no inline `Properties` block:

```yaml
  PipelineStartedRule:
    Fn::Transform:
      Name: AWS::Include
      Parameters:
        Location: !Sub "s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/pipeline/pipeline-notification-started-rule.yml"
```

The actual `Properties.Targets[0].InputTransformer.InputTemplate` now lives in:

- `templates/v2/modules/pipeline/pipeline-notification-started-rule.yml`
- `templates/v2/modules/pipeline/pipeline-notification-succeeded-rule.yml`
- `templates/v2/modules/pipeline/pipeline-notification-failed-rule.yml`

The test helpers still assume the old inline structure:

```python
def _get_input_template_str(template, rule_name):
    rule = template["Resources"][rule_name]
    target = rule["Properties"]["Targets"][0]          # no longer present
    input_template = target["InputTransformer"]["InputTemplate"]
    return input_template["!Sub"]                      # module uses Fn::Sub, not !Sub
```

Two distinct breakages:

1. **Location moved** — properties are in the module files, not the parent.
2. **Intrinsic syntax differs** — `AWS::Include` modules must use long-form intrinsics (`Fn::Sub`), so even after locating the target, the helper's `input_template["!Sub"]` lookup would need to become `input_template["Fn::Sub"]`. (The module correctly uses `Fn::Sub` per the module-standards steering.)

The message/subject content itself is unchanged, so the label/JSON/subject assertions will pass once the helpers read from the correct place.

### Proposed solution (test-only)

Rewrite the helpers in `test_pipeline_notifications_unit.py` to source the rule body from the module files rather than the parent template:

- Add a module directory constant: `MODULE_DIR = .../templates/v2/modules/pipeline`.
- Map each rule name to its module file (`PipelineStartedRule` → `pipeline-notification-started-rule.yml`, etc.).
- `_get_input_template_str` / `_get_input_paths_map` load the module YAML (top-level `Properties.Targets[0].InputTransformer...`) and read the `Fn::Sub` key (accept `!Sub` too for robustness).
- `TestTemplateParity` (which asserts the InputTemplate/InputPathsMap/labels are identical across the three parent templates): since all three parents now include the **same** shared module, parity is guaranteed by construction. Update it to either (a) assert all three parents reference the identical module `Location`, or (b) compare the module files directly. Recommendation: assert identical `Location` references, which is the property that actually matters now.

No template change required — the module refactor is correct and intended.

---

## Category 2 — S3 artifacts bucket policy structure (1 failure)

### What fails

```
tests/test_s3_artifacts_bucket_policy_unit.py::TestPreservationStructure::test_exactly_three_statements
  AssertionError: Expected 3 statements, got 4
```

### Root cause

`templates/v2/modules/account-wide/s3-artifacts-bucket-policy.yml` gained an optional cross-account promotion statement. The `Statement` list now has four entries; the fourth is a conditional block:

```yaml
      - Fn::If:
          - HasPromotionSourceAccounts
          - Sid: "AllowCrossAccountPromotionWrite"
            Effect: Allow
            # ... scoped to promotions/* and *-PromoteServiceRole principals
          - Ref: "AWS::NoValue"
```

At deploy time this resolves to either the promotion statement (when `HasPromotionSourceAccounts`) or `AWS::NoValue` (preserving the original 3-statement behavior). Under static YAML parsing, the list length is 4. The test `test_exactly_three_statements` was written before the promotion feature and hard-codes a count of 3.

### Proposed solution (test-only)

Update `TestPreservationStructure` to reflect the current, intended structure:

- Assert the three concrete Sids (`DenyNonSecureTransportAccess`, `WhitelistedGet`, `WhitelistedPut`) are present among the *unconditional* statements.
- Recognize the optional 4th entry as an `Fn::If` on `HasPromotionSourceAccounts` whose true-branch Sid is `AllowCrossAccountPromotionWrite` and whose false-branch is `AWS::NoValue`.

Suggested approach: partition statements into "concrete" (plain dicts with a `Sid`) vs "conditional" (`Fn::If`), assert exactly 3 concrete with the expected Sids, and assert the conditional promotion statement is well-formed. Rename the test (e.g., `test_three_base_statements_plus_optional_promotion`) to describe the current contract.

No template change required.

---

## Category 3 — prefix-based-infrastructure.yml version (1 failure)

### What fails

```
tests/test_consuming_templates_artifacts_params_unit.py::TestHeaderVersions::test_header_version_line[prefix-based-infrastructure.yml]
  AssertionError: Expected version line '# Version: v0.0.2/...' not found in prefix-based-infrastructure.yml
```

### Root cause

The template header is currently:

```
# Version: v2.0.1/2026-08-20
```

but the test's `EXPECTED_VERSIONS` map still expects `v0.0.2`:

```python
EXPECTED_VERSIONS = {
    PREFIX_BASED_PATH: "v0.0.2",            # <-- stale
    SERVICE_ROLE_PIPELINE_PATH: "v0.0.19",  # passes
    SERVICE_ROLE_STORAGE_PATH: "v0.0.4",    # passes
}
```

The version was deliberately raised in commit `22ef057` ("updated version numbers so they were no longer considered development"). Per the template-version-control steering, moving off a `PATCH = 0` development version to a stable `PATCH > 0` version is an intentional lifecycle step — the template header is the source of truth. The two sibling templates in the same test were bumped consistently (and their assertions still pass); only the `prefix-based` expected value was left behind.

### Proposed solution (test-only) — needs a one-line confirmation

Update the expected value to match the committed template header:

```python
PREFIX_BASED_PATH: "v2.0.1",
```

> Decision needed: confirm `v2.0.1/2026-08-20` is the intended, correct header for `prefix-based-infrastructure.yml`. It has been committed since `22ef057`, so the strong default is "yes, the header is correct and the test is stale." If instead the header was raised in error, the fix would live in the template rather than the test. See [Open questions](#open-questions).

No template change expected.

---

## Out of scope: 2 additional failures

The full suite shows 2 more failures beyond the 149. These come from **uncommitted, in-progress** v0.0.44 work (files currently modified in the working tree) and are tied to active specs, so they are excluded from this remediation:

- `test_bedrock_invocation_logs_unit.py::TestEnableBedrockInvocationLogsParameter::test_default_is_true` — `account-wide-infrastructure.yml` now defaults `EnableBedrockInvocationLogs` to `"false"` (spec `0-0-44-bedrock-invocation-logs-default-off`); this assertion was not updated to `test_default_is_false`.
- `test_network_template_property.py` (`TestLoggingConfigurationFormatProperty`, `TestLoggingDisabledProperty`) — the CloudFront logging condition changed from `HasLogBucket` to `HasV1Destination` (spec `0-0-44-bedrock-media-and-log-prefix-segmentation`, `CloudFrontLoggingVersion` work); the property tests were not updated.

These should be addressed as the final "update tests" task within their originating specs, not here. They are listed for completeness only.

---

## Overall recommendation

Treat all 149 in-scope failures as **stale-test maintenance**. No CloudFormation template needs to change; the templates are correct and reflect intended, committed behavior. The work is confined to three test files:

1. `tests/test_pipeline_notifications_unit.py` — re-point helpers at the notification module files and adapt to `Fn::Sub`; convert `TestTemplateParity` to a shared-module reference check. (147)
2. `tests/test_s3_artifacts_bucket_policy_unit.py` — allow the optional conditional promotion statement in `TestPreservationStructure`. (1)
3. `tests/test_consuming_templates_artifacts_params_unit.py` — set `EXPECTED_VERSIONS[PREFIX_BASED_PATH] = "v2.0.1"`. (1)

Per the repository testing guidelines, keep these as fast unit-style assertions (the pipeline module reads are trivial file loads). Expected total runtime impact: negligible.

## Open questions

1. **Version confirmation (Category 3):** Is `v2.0.1/2026-08-20` the intended header for `prefix-based-infrastructure.yml`? (Default assumption: yes — update the test.) If not, the template header is what should change.
2. **`TestTemplateParity` intent (Category 1):** Confirm the preferred replacement — assert all three parents reference the identical module `Location` (recommended), versus comparing full module contents. Both preserve the original guarantee; the former is simpler and matches the new architecture.
3. **Scope confirmation:** Should the 2 out-of-scope failures (bedrock default, network logging property) be folded into this remediation, or left to their originating v0.0.44 specs? (Default: leave them to their specs.)

## Proposed next steps

If the direction above is approved, the follow-on spec artifacts (`requirements.md`, `design.md`, `tasks.md`) can be generated to implement the three test updates, followed by a full `pytest tests/` run to confirm the 149 failures clear (and only the 2 out-of-scope, in-progress failures remain until their specs land).
