# Implementation Plan

Tasks — v0.0.44 Pre-Existing Test Failure Remediation

## Overview

Implementation task list for `design.md`. This is a **test-only** change that repairs the 149 pre-existing stale-test failures across three test files. No CloudFormation template, module, or documentation file is modified. The three test edits are independent; they are ordered here from largest to smallest, with full-suite verification last.

Legend: each task notes the requirement(s) it satisfies. Reference: [report.md](./report.md), [requirements.md](./requirements.md), [design.md](./design.md).

## Tasks

### 1. Repair pipeline notification tests (`tests/test_pipeline_notifications_unit.py`)

- [x] 1.1 Add module-resolution scaffolding: a `MODULE_DIR` constant pointing at `templates/v2/modules/pipeline/` and a `RULE_MODULE_FILES` map (`PipelineStartedRule`→`pipeline-notification-started-rule.yml`, `PipelineSucceededRule`→`pipeline-notification-succeeded-rule.yml`, `PipelineFailedRule`→`pipeline-notification-failed-rule.yml`) _(R1.2)_
- [x] 1.2 Add helpers `_module_location(template, rule_name)` (reads `Resources[rule].Fn::Transform.Parameters.Location`, unwrapping the `!Sub`/`Fn::Sub` key) and `_load_rule_module(template, rule_name)` (loads the module file resolved from that Location's basename) _(R1.1, R1.2)_
- [x] 1.3 Re-implement `_get_input_template_str` and `_get_input_paths_map` to read from the loaded module's top-level `Properties.Targets[0].InputTransformer.*`; return the `InputTemplate` value under the `Fn::Sub` key (fallback `!Sub`). Keep the existing `(template, rule_name)` signatures so call sites are unchanged _(R1.1, R1.3)_
- [x] 1.4 Confirm `TestInputTemplateJsonStructure`, `TestSubjectFormat`, `TestMessageBodyLabels`, `TestCallToAction`, and `TestNoJsonArtifacts` pass unchanged via the new helpers (no body edits expected) _(R1.4)_
- [x] 1.5 Update `TestYamlBlockScalar.test_input_template_uses_folded_strip_scalar` to read each module file's raw text and assert `InputTemplate:` is followed by long-form `Fn::Sub: >-` (regex `r"InputTemplate:\s*\n\s*Fn::Sub:\s*>-"`); parametrize over the three rule modules. Confirm `test_no_trailing_newline_in_input_template` passes via the updated helper _(R1.4)_
- [x] 1.6 Rewrite `TestTemplateParity` to a single check asserting all three parent templates reference the identical module `Location` per rule (and that it resolves to the expected `RULE_MODULE_FILES` filename); remove the three now-redundant content-comparison methods _(R1.5)_
- [x] 1.7 Run `pytest tests/test_pipeline_notifications_unit.py`; confirm the 147 previously failing tests pass (parity consolidation 9→3 is the only intentional count change) and nothing is skipped _(R1.6)_
- [x] 1.8 Confirm only `tests/test_pipeline_notifications_unit.py` changed — no template or module file modified _(R1.7)_

### 2. Accept optional promotion statement (`tests/test_s3_artifacts_bucket_policy_unit.py`)

- [x] 2.1 Replace `TestPreservationStructure.test_exactly_three_statements` with a test that partitions statements into base (plain dicts with `Sid`, no `Fn::If`) and conditional (`Fn::If`) entries; assert the three base Sids (`DenyNonSecureTransportAccess`, `WhitelistedGet`, `WhitelistedPut`) are present and the count assertion is expressed as "3 base + optional conditional" rather than a literal length _(R2.1, R2.3)_
- [x] 2.2 In the same test, assert the optional entry (when present, ≤1) is `Fn::If` on `HasPromotionSourceAccounts` with true-branch Sid `AllowCrossAccountPromotionWrite` and false-branch `{"Ref": "AWS::NoValue"}` _(R2.2)_
- [x] 2.3 Update the test name/docstring to describe the current contract (three base statements plus optional promotion) _(R2.4)_
- [x] 2.4 Run `pytest tests/test_s3_artifacts_bucket_policy_unit.py`; confirm the remaining `TestPreservationStructure` assertions (`Condition`, `PolicyDocument.Version`, `PolicyDocument.Id`) still pass and only this test file changed _(R2.5, R2.6)_

### 3. Align expected version (`tests/test_consuming_templates_artifacts_params_unit.py`)

- [x] 3.1 In `EXPECTED_VERSIONS`, change the `prefix-based-infrastructure.yml` value from `v0.0.2` to `v2.0.1`; leave the two service-role entries unchanged _(R3.1, R3.2)_
- [x] 3.2 Run `pytest "tests/test_consuming_templates_artifacts_params_unit.py::TestHeaderVersions"`; confirm all version-line checks pass and only this test file changed _(R3.3, R3.4)_

### 4. Full-suite verification

- [x] 4.1 Run `pytest tests/`; confirm the 149 in-scope failures now pass _(R4.1)_
- [x] 4.2 Confirm the only remaining failures are the two documented out-of-scope items owned by sibling specs: `test_bedrock_invocation_logs_unit.py::TestEnableBedrockInvocationLogsParameter::test_default_is_true` and the two `test_network_template_property.py` logging-property tests; no other test regresses _(R4.2, R4.3)_
- [x] 4.3 Confirm `git status` shows changes only under `tests/` (no template, module, or `docs/` files modified) _(R5.1, R5.2)_
- [x] 4.4 (Optional) If a CHANGELOG entry is desired, add it under `## v0.0.44 (unreleased)` referencing this spec; omission is acceptable for a test-only change _(R5.3)_
