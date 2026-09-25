# Design — v0.0.44 Pre-Existing Test Failure Remediation

## 1. Overview

This is a **test-only** change. The 149 in-scope failures are stale assertions against templates whose committed behavior is correct and intended (see [report.md](./report.md)). The design updates three test files so they validate the current template/module architecture. No CloudFormation template, module, or documentation file is touched.

The three edits are independent and can land in any order:

| File | Failures | Nature of change |
|------|---------:|------------------|
| `tests/test_pipeline_notifications_unit.py` | 147 | Re-point helpers at the `AWS::Include` module files (resolved from each parent's `Location`); rewrite `TestTemplateParity` and the YAML block-scalar checks |
| `tests/test_s3_artifacts_bucket_policy_unit.py` | 1 | Accept the optional conditional 4th policy statement |
| `tests/test_consuming_templates_artifacts_params_unit.py` | 1 | Set expected `prefix-based-infrastructure.yml` version to `v2.0.1` |

### 1.1 Shared loader facts that shape the design

From `tests/cfn_test_utils.py`:

- `load_template(path)` runs `yaml.load` with `CFNLoader`. It works on a **module snippet** too: a module file parses to a plain dict with top-level `Type` / `Properties` / `Condition` keys (there is no `Resources` wrapper).
- The loader turns YAML **shorthand** tags (`!Sub`, `!Ref`, `!If`, ...) into single-key dicts keyed by the tag string (e.g. `{"!Sub": "..."}`).
- **Long-form** intrinsics used inside `AWS::Include` modules (`Fn::Sub:`, `Ref:`, `Fn::If:`) are ordinary YAML mapping keys, so they parse to `{"Fn::Sub": "..."}` etc. This is why the pipeline notification `InputTemplate` now sits under a `Fn::Sub` key, not `!Sub`.
- Parent templates are real templates and legitimately use shorthand, so a parent's `Fn::Transform` `Location` parses to `{"!Sub": "s3://.../<module>.yml"}`.

---

## 2. Category 1 — `tests/test_pipeline_notifications_unit.py` (147)

### 2.1 Design goal

The three notification EventBridge rules moved into shared modules:

- `PipelineStartedRule` → `templates/v2/modules/pipeline/pipeline-notification-started-rule.yml`
- `PipelineSucceededRule` → `pipeline-notification-succeeded-rule.yml`
- `PipelineFailedRule` → `pipeline-notification-failed-rule.yml`

Each parent (`template-pipeline.yml`, `template-pipeline-github.yml`, `template-pipeline-build-only.yml`) wires the rule to its module via:

```yaml
  PipelineStartedRule:
    Fn::Transform:
      Name: AWS::Include
      Parameters:
        Location: !Sub "s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/pipeline/pipeline-notification-started-rule.yml"
```

The design keeps the existing test bodies and their `(pipeline_template, rule_name)` parametrization essentially intact by changing only the **helpers** so they resolve the rule's module *from the parent's own `Location` reference* and read the rule body from there. This preserves per-parent coverage (each parent's wiring is still exercised — the parent must reference a real, loadable module) and keeps the test count stable, while matching the module architecture.

### 2.2 Helper redesign

Add module-directory context and a resolver, then re-implement the three existing helpers. Signatures stay the same, so call sites are unchanged.

```python
MODULE_DIR = Path(__file__).parent.parent / "templates" / "v2" / "modules" / "pipeline"

def _module_location(template, rule_name):
    """Return the raw Location string for a rule's AWS::Include transform."""
    rule = template["Resources"][rule_name]
    transform = rule["Fn::Transform"]
    assert transform.get("Name") == "AWS::Include", (
        f"{rule_name} should use AWS::Include"
    )
    location = transform["Parameters"]["Location"]
    # Location is {'!Sub': 's3://.../<module>.yml'} in the parent template
    if isinstance(location, dict):
        location = location.get("!Sub", location.get("Fn::Sub"))
    return location

def _load_rule_module(template, rule_name):
    """Resolve the rule's module file from its Location and load it."""
    location = _module_location(template, rule_name)
    module_file = location.rsplit("/", 1)[-1]        # e.g. pipeline-notification-started-rule.yml
    return load_template(MODULE_DIR / module_file)

def _get_input_template_str(template, rule_name):
    """Extract the raw InputTemplate Fn::Sub string from the rule's module."""
    module = _load_rule_module(template, rule_name)
    target = module["Properties"]["Targets"][0]
    input_template = target["InputTransformer"]["InputTemplate"]
    assert isinstance(input_template, dict), "InputTemplate should be a mapping"
    # Module uses long-form Fn::Sub; accept !Sub as a fallback for robustness
    return input_template.get("Fn::Sub", input_template.get("!Sub"))

def _get_input_paths_map(template, rule_name):
    module = _load_rule_module(template, rule_name)
    return module["Properties"]["Targets"][0]["InputTransformer"]["InputPathsMap"]
```

`_parse_input_template` is unchanged (it calls `_get_input_template_str` and `json.loads`). Because the parent template is still passed in and used to resolve the `Location`, the existing `pipeline_template`-parametrized tests continue to run three times (once per parent) and now pass.

### 2.3 Per-class impact

These classes need **no body changes** — they pass once the helpers resolve to the module:

- `TestInputTemplateJsonStructure` (valid JSON, exactly `Subject`/`Message`, string types)
- `TestSubjectFormat` (pipeline placeholder + state word; `ALERT:` prefix for failed)
- `TestMessageBodyLabels` (required labels, separate lines, blank-line separation, header summary)
- `TestCallToAction` (failed contains the prompt; started/succeeded do not)
- `TestNoJsonArtifacts` (no `{`/`}` or JSON key syntax outside `${...}`)

`TestYamlBlockScalar` and `TestTemplateParity` need targeted rewrites (below).

### 2.4 `TestYamlBlockScalar`

The folded-strip block scalar now lives in the **module** file as `Fn::Sub: >-`, not in the parent as `!Sub >-`.

- `test_input_template_uses_folded_strip_scalar`: read each module file's raw text and assert the `InputTemplate:` key is followed by a long-form `Fn::Sub: >-`. Parametrize over the three rule modules (resolved via `_module_location` from any parent, or directly from the rule→module names). Proposed matcher:

  ```python
  content = (MODULE_DIR / module_file).read_text(encoding="utf-8")
  assert re.search(r"InputTemplate:\s*\n\s*Fn::Sub:\s*>-", content), (
      f"{module_file} InputTemplate should use folded-strip 'Fn::Sub: >-'"
  )
  ```

- `test_no_trailing_newline_in_input_template`: unchanged in intent; it calls `_get_input_template_str`, which now reads the module, and asserts no trailing `\n`. The module uses `>-` (strip), so this holds.

### 2.5 `TestTemplateParity` (per confirmed decision #2)

Replace the "InputTemplate/InputPathsMap/labels identical across parents" assertions with a check that all three parents reference the **identical shared module `Location`** for each rule. Parity of content is then guaranteed by construction (one shared file).

```python
class TestTemplateParity:
    """All three pipeline templates reference the identical shared notification module."""

    @pytest.mark.parametrize("rule_name", RULE_NAMES)
    def test_all_templates_reference_identical_module_location(self, all_templates, rule_name):
        locations = {
            name: _module_location(tmpl, rule_name)
            for name, tmpl in all_templates.items()
        }
        distinct = set(locations.values())
        assert len(distinct) == 1, (
            f"Parents reference differing module Locations for {rule_name}: {locations}"
        )
        # And it resolves to the expected module filename
        module_file = next(iter(distinct)).rsplit("/", 1)[-1]
        assert module_file == RULE_MODULE_FILES[rule_name]
```

where `RULE_MODULE_FILES` maps each rule to its expected module filename (used only for the assertion, not for loading). The three original parity methods (`test_input_template_identical_across_templates`, `test_input_paths_map_identical_across_templates`, `test_message_labels_identical_across_templates`) are consolidated into this single, architecture-accurate check.

### 2.6 Test-count note

Consolidating the three parity methods into one reduces that class's parametrized count (9 → 3). This is an intentional restructure that preserves the original intent (parity across parents), permitted by Requirement 1.6 / 4.3. All other pipeline tests retain their existing parametrization and counts.

---

## 3. Category 2 — `tests/test_s3_artifacts_bucket_policy_unit.py` (1)

### 3.1 Current vs intended structure

`templates/v2/modules/account-wide/s3-artifacts-bucket-policy.yml` now has four `Statement` entries: three unconditional statements (`DenyNonSecureTransportAccess`, `WhitelistedGet`, `WhitelistedPut`) plus an optional conditional statement:

```yaml
      - Fn::If:
          - HasPromotionSourceAccounts
          - Sid: "AllowCrossAccountPromotionWrite"
            # ...
          - Ref: "AWS::NoValue"
```

Under static parsing (`Fn::If` is not resolved), the list length is 4.

### 3.2 Redesigned test

Replace `test_exactly_three_statements` with an assertion expressed as "three base statements plus an optional conditional promotion statement". Partition the list into concrete statements (plain dicts carrying a `Sid`) and conditional entries (`Fn::If`):

```python
def test_three_base_statements_plus_optional_promotion(self, statements):
    """Policy has the 3 base statements; the optional 4th is a conditional promotion statement."""
    base = [s for s in statements if isinstance(s, dict) and "Sid" in s and "Fn::If" not in s]
    conditional = [s for s in statements if isinstance(s, dict) and "Fn::If" in s]

    base_sids = [s.get("Sid") for s in base]
    assert set(base_sids) == {
        "DenyNonSecureTransportAccess", "WhitelistedGet", "WhitelistedPut"
    }, f"Unexpected base statement Sids: {base_sids}"

    # Zero or one optional promotion statement, gated on HasPromotionSourceAccounts
    assert len(conditional) <= 1
    if conditional:
        cond_name, true_branch, false_branch = conditional[0]["Fn::If"]
        assert cond_name == "HasPromotionSourceAccounts"
        assert true_branch.get("Sid") == "AllowCrossAccountPromotionWrite"
        assert false_branch == {"Ref": "AWS::NoValue"}
```

The remaining `TestPreservationStructure` methods (resource-level `Condition == EnableS3ArtifactsBucket`, `PolicyDocument.Version == "2012-10-17"`, `PolicyDocument.Id == "SSEAndSSLPolicy"`) are unchanged and continue to pass.

> The count assertion is deliberately expressed against the 3 base statements plus an optional conditional, not a literal length of 3 or 4, so the test stays correct whether or not the promotion statement is present.

---

## 4. Category 3 — `tests/test_consuming_templates_artifacts_params_unit.py` (1)

Single-line change to the `EXPECTED_VERSIONS` map (confirmed decision #1 — `v2.0.1/2026-08-20` is the intended header):

```python
EXPECTED_VERSIONS = {
    PREFIX_BASED_PATH: "v2.0.1",            # was "v0.0.2"
    SERVICE_ROLE_PIPELINE_PATH: "v0.0.19",  # unchanged (passing)
    SERVICE_ROLE_STORAGE_PATH: "v0.0.4",    # unchanged (passing)
}
```

`test_header_version_line` asserts `f"# Version: {expected}/" in raw_text`, so `v2.0.1` matches `# Version: v2.0.1/2026-08-20`. No other assertion in that test file references the version.

---

## 5. Testing and verification

Per the repository testing guidelines these remain fast, unit-style assertions; no property-based tests are added.

1. **Targeted reruns** after each edit:
   - `pytest tests/test_pipeline_notifications_unit.py`
   - `pytest tests/test_s3_artifacts_bucket_policy_unit.py`
   - `pytest "tests/test_consuming_templates_artifacts_params_unit.py::TestHeaderVersions"`
2. **Full suite:** `pytest tests/`. Expected outcome: the 149 in-scope failures clear. The only remaining failures are the two documented out-of-scope items owned by sibling specs:
   - `test_bedrock_invocation_logs_unit.py::TestEnableBedrockInvocationLogsParameter::test_default_is_true`
   - the two `test_network_template_property.py` logging-property tests
3. **No-regression check:** confirm no previously passing test now fails. The passing count may shift down slightly only due to the intentional `TestTemplateParity` consolidation (§2.6); no coverage intent is lost.
4. **No template drift:** confirm `git status` shows changes only under `tests/` for this spec (no template/module/doc files modified).

---

## 6. Design decisions

| Decision | Choice | Reasoning |
|---|---|---|
| How pipeline helpers find the rule body | Resolve the module from the parent's own `Location`, then `load_template` the module | Keeps existing `(pipeline_template, rule_name)` test signatures and per-parent coverage; each parent's wiring is still exercised; matches the module architecture |
| Intrinsic key for `InputTemplate` | Read `Fn::Sub` (fallback `!Sub`) | Modules must use long-form intrinsics; fallback keeps the helper robust if a rule is ever inlined |
| `TestTemplateParity` replacement | Assert identical `Location` across the three parents (+ expected module filename) | Confirmed decision #2; content parity is guaranteed by a single shared module, so the meaningful invariant is that all parents point at it |
| Parity method consolidation | Merge 3 methods into 1 | Removes now-redundant content comparisons; intentional restructure preserving intent (Req 1.6/4.3) |
| S3 policy count assertion | "3 base + optional conditional promotion", not a fixed length | Correct whether or not the promotion statement renders; validates the conditional's shape |
| Version fix | Update the test's expected value to `v2.0.1` | Confirmed decision #1; the committed template header is the source of truth |
| Out-of-scope failures | Leave to sibling specs | Confirmed decision #3; those files are owned by other v0.0.44 specs |

---

## 7. Requirements coverage

| Requirement | Addressed by |
|---|---|
| 1 (repair pipeline notification tests) | §2.1–§2.6 |
| 2 (accept optional promotion statement) | §3.1–§3.2 |
| 3 (align prefix-based expected version) | §4 |
| 4 (full-suite verification) | §5 |
| 5 (change governance — test-only) | §1, §5.4, §6 |
