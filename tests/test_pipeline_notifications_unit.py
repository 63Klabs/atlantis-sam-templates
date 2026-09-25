"""
Unit tests for pipeline notification formatting.
Tests the InputTemplate content in all three pipeline templates to verify
human-readable email formatting with labeled fields, proper subjects,
and consistent structure across templates.
"""

import json
import pytest
import re
import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import load_template


# ---------------------------------------------------------------------------
# Constants and fixtures
# ---------------------------------------------------------------------------

TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "v2" / "pipeline"

# Directory holding the AWS::Include notification rule modules that the parent
# pipeline templates reference via Fn::Transform.
MODULE_DIR = Path(__file__).parent.parent / "templates" / "v2" / "modules" / "pipeline"

TEMPLATE_FILES = [
    "template-pipeline.yml",
    "template-pipeline-github.yml",
    "template-pipeline-build-only.yml",
]

RULE_NAMES = [
    "PipelineStartedRule",
    "PipelineSucceededRule",
    "PipelineFailedRule",
]

# Maps each notification rule to its shared AWS::Include module filename.
RULE_MODULE_FILES = {
    "PipelineStartedRule": "pipeline-notification-started-rule.yml",
    "PipelineSucceededRule": "pipeline-notification-succeeded-rule.yml",
    "PipelineFailedRule": "pipeline-notification-failed-rule.yml",
}

STATE_MAP = {
    "PipelineStartedRule": "STARTED",
    "PipelineSucceededRule": "SUCCEEDED",
    "PipelineFailedRule": "FAILED",
}

SUBJECT_STATE_WORD = {
    "PipelineStartedRule": "Started",
    "PipelineSucceededRule": "Succeeded",
    "PipelineFailedRule": "Failed",
}

REQUIRED_LABELS = [
    "Status:",
    "Pipeline:",
    "Execution ID:",
    "Time:",
    "Console Link:",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    module_file = location.rsplit("/", 1)[-1]
    return load_template(MODULE_DIR / module_file)


def _get_input_template_str(template, rule_name):
    """Extract the raw InputTemplate Fn::Sub string from the rule's module."""
    module = _load_rule_module(template, rule_name)
    target = module["Properties"]["Targets"][0]
    input_template = target["InputTransformer"]["InputTemplate"]
    assert isinstance(input_template, dict), "InputTemplate should be a mapping"
    # Module uses long-form Fn::Sub; accept !Sub as a fallback for robustness
    return input_template.get("Fn::Sub", input_template.get("!Sub"))


def _parse_input_template(template, rule_name):
    """Parse the InputTemplate JSON and return the dict with Subject and Message."""
    raw = _get_input_template_str(template, rule_name)
    return json.loads(raw)


def _get_input_paths_map(template, rule_name):
    """Extract the InputPathsMap from the rule's module."""
    module = _load_rule_module(template, rule_name)
    return module["Properties"]["Targets"][0]["InputTransformer"]["InputPathsMap"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(params=TEMPLATE_FILES, ids=TEMPLATE_FILES)
def pipeline_template(request):
    """Load each pipeline template as a parameterized fixture."""
    return load_template(TEMPLATE_DIR / request.param)


@pytest.fixture
def all_templates():
    """Load all three pipeline templates as a dict keyed by filename."""
    return {
        name: load_template(TEMPLATE_DIR / name)
        for name in TEMPLATE_FILES
    }



# ===========================================================================
# Property 5 – InputTemplate is valid JSON with exactly Subject and Message
# ===========================================================================

class TestInputTemplateJsonStructure:
    """Each InputTemplate renders to valid JSON with exactly Subject and Message keys."""

    @pytest.mark.parametrize("rule_name", RULE_NAMES)
    def test_input_template_is_valid_json(self, pipeline_template, rule_name):
        """InputTemplate string parses as valid JSON."""
        raw = _get_input_template_str(pipeline_template, rule_name)
        parsed = json.loads(raw)  # will raise on invalid JSON
        assert isinstance(parsed, dict)

    @pytest.mark.parametrize("rule_name", RULE_NAMES)
    def test_input_template_has_exactly_two_keys(self, pipeline_template, rule_name):
        """InputTemplate JSON has exactly Subject and Message keys."""
        parsed = _parse_input_template(pipeline_template, rule_name)
        assert set(parsed.keys()) == {"Subject", "Message"}

    @pytest.mark.parametrize("rule_name", RULE_NAMES)
    def test_subject_is_string(self, pipeline_template, rule_name):
        """Subject value is a non-empty string."""
        parsed = _parse_input_template(pipeline_template, rule_name)
        assert isinstance(parsed["Subject"], str)
        assert len(parsed["Subject"]) > 0

    @pytest.mark.parametrize("rule_name", RULE_NAMES)
    def test_message_is_string(self, pipeline_template, rule_name):
        """Message value is a non-empty string."""
        parsed = _parse_input_template(pipeline_template, rule_name)
        assert isinstance(parsed["Message"], str)
        assert len(parsed["Message"]) > 0


# ===========================================================================
# Property 2 – Subject line format per state
# ===========================================================================

class TestSubjectFormat:
    """Subject contains pipeline name placeholder and state-appropriate text."""

    @pytest.mark.parametrize("rule_name", ["PipelineStartedRule", "PipelineSucceededRule"])
    def test_started_succeeded_subject_contains_pipeline_and_state(self, pipeline_template, rule_name):
        """Started/Succeeded subjects contain <pipeline> and the state word."""
        parsed = _parse_input_template(pipeline_template, rule_name)
        subject = parsed["Subject"]
        assert "<pipeline>" in subject, "Subject should contain pipeline placeholder"
        assert SUBJECT_STATE_WORD[rule_name] in subject, (
            f"Subject should contain '{SUBJECT_STATE_WORD[rule_name]}'"
        )

    def test_failed_subject_starts_with_alert(self, pipeline_template):
        """Failed subject starts with 'ALERT:'."""
        parsed = _parse_input_template(pipeline_template, "PipelineFailedRule")
        subject = parsed["Subject"]
        assert subject.startswith("ALERT:"), "Failed subject must start with 'ALERT:'"

    def test_failed_subject_contains_pipeline_and_failed(self, pipeline_template):
        """Failed subject contains <pipeline> and 'Failed'."""
        parsed = _parse_input_template(pipeline_template, "PipelineFailedRule")
        subject = parsed["Subject"]
        assert "<pipeline>" in subject
        assert "Failed" in subject

    @pytest.mark.parametrize("rule_name", ["PipelineStartedRule", "PipelineSucceededRule"])
    def test_non_failed_subject_does_not_start_with_alert(self, pipeline_template, rule_name):
        """Started/Succeeded subjects do NOT start with 'ALERT:'."""
        parsed = _parse_input_template(pipeline_template, rule_name)
        subject = parsed["Subject"]
        assert not subject.startswith("ALERT:"), (
            f"{rule_name} subject should not start with 'ALERT:'"
        )


# ===========================================================================
# Property 1 – Message body labels on separate lines with section separation
# ===========================================================================

class TestMessageBodyLabels:
    """Message contains required labels on separate lines with blank-line separation."""

    @pytest.mark.parametrize("rule_name", RULE_NAMES)
    def test_message_contains_all_required_labels(self, pipeline_template, rule_name):
        """Message contains Status:, Pipeline:, Execution ID:, Time:, Console Link:."""
        parsed = _parse_input_template(pipeline_template, rule_name)
        message = parsed["Message"]
        for label in REQUIRED_LABELS:
            assert label in message, f"Message missing label '{label}'"

    @pytest.mark.parametrize("rule_name", RULE_NAMES)
    def test_labels_on_separate_lines(self, pipeline_template, rule_name):
        """Each label appears at the start of its own line."""
        parsed = _parse_input_template(pipeline_template, rule_name)
        # After JSON parsing, \n are real newlines in the string
        lines = parsed["Message"].split("\n")
        for label in REQUIRED_LABELS:
            matching = [l for l in lines if l.strip().startswith(label)]
            assert len(matching) >= 1, f"Label '{label}' not found at start of any line"

    @pytest.mark.parametrize("rule_name", RULE_NAMES)
    def test_blank_line_separation(self, pipeline_template, rule_name):
        """Message contains blank lines (double newline) for visual section separation."""
        parsed = _parse_input_template(pipeline_template, rule_name)
        message = parsed["Message"]
        assert "\n\n" in message, "Message should contain blank line separation (double newline)"

    @pytest.mark.parametrize("rule_name", RULE_NAMES)
    def test_header_summary_present(self, pipeline_template, rule_name):
        """Message starts with a header summary line like 'Pipeline Execution - STATE'."""
        parsed = _parse_input_template(pipeline_template, rule_name)
        message = parsed["Message"]
        state = STATE_MAP[rule_name]
        expected_header = f"Pipeline Execution - {state}"
        assert message.startswith(expected_header), (
            f"Message should start with '{expected_header}'"
        )


# ===========================================================================
# Property 3 – Call-to-action for FAILED only
# ===========================================================================

class TestCallToAction:
    """FAILED message contains call-to-action; STARTED and SUCCEEDED do not."""

    CALL_TO_ACTION = "Please check the pipeline for errors."

    def test_failed_message_contains_call_to_action(self, pipeline_template):
        """FAILED message includes the call-to-action prompt."""
        parsed = _parse_input_template(pipeline_template, "PipelineFailedRule")
        assert self.CALL_TO_ACTION in parsed["Message"]

    @pytest.mark.parametrize("rule_name", ["PipelineStartedRule", "PipelineSucceededRule"])
    def test_non_failed_message_does_not_contain_call_to_action(self, pipeline_template, rule_name):
        """STARTED/SUCCEEDED messages do NOT include the call-to-action prompt."""
        parsed = _parse_input_template(pipeline_template, rule_name)
        assert self.CALL_TO_ACTION not in parsed["Message"], (
            f"{rule_name} message should not contain call-to-action"
        )



# ===========================================================================
# Property 4 – No JSON artifacts in rendered message/subject values
# ===========================================================================

class TestNoJsonArtifacts:
    """Rendered Subject and Message values are free of JSON structural syntax."""

    JSON_KEY_ARTIFACTS = ['"Message":', '"Subject":']

    @pytest.mark.parametrize("rule_name", RULE_NAMES)
    def test_subject_no_json_artifacts(self, pipeline_template, rule_name):
        """Subject value does not contain JSON structural characters or key syntax."""
        parsed = _parse_input_template(pipeline_template, rule_name)
        subject = parsed["Subject"]
        for artifact in self.JSON_KEY_ARTIFACTS:
            assert artifact not in subject, (
                f"Subject should not contain JSON artifact '{artifact}'"
            )
        # Subject should not contain { or } at all
        assert "{" not in subject, "Subject should not contain '{'"
        assert "}" not in subject, "Subject should not contain '}'"

    @pytest.mark.parametrize("rule_name", RULE_NAMES)
    def test_message_no_json_key_artifacts(self, pipeline_template, rule_name):
        """Message value does not contain JSON key syntax like "Message": or "Subject":."""
        parsed = _parse_input_template(pipeline_template, rule_name)
        message = parsed["Message"]
        for artifact in self.JSON_KEY_ARTIFACTS:
            assert artifact not in message, (
                f"Message should not contain JSON artifact '{artifact}'"
            )

    @pytest.mark.parametrize("rule_name", RULE_NAMES)
    def test_message_no_json_braces_outside_cfn_variables(self, pipeline_template, rule_name):
        """Message has no JSON braces outside of CloudFormation ${...} substitution variables."""
        parsed = _parse_input_template(pipeline_template, rule_name)
        message = parsed["Message"]
        # Remove CloudFormation !Sub variable references like ${AWS::Region}
        stripped = re.sub(r"\$\{[^}]+\}", "", message)
        assert "{" not in stripped, (
            "Message should not contain '{' outside of CloudFormation ${...} variables"
        )
        assert "}" not in stripped, (
            "Message should not contain '}' outside of CloudFormation ${...} variables"
        )


# ===========================================================================
# Property 6 – Template parity across all three pipeline variants
# ===========================================================================

class TestTemplateParity:
    """All three pipeline templates reference the identical shared notification module.

    Because the notification rule bodies now live in shared AWS::Include modules,
    content parity across the three parent templates (InputTemplate, InputPathsMap,
    message labels) is guaranteed by construction: each parent points at the same
    module file. The meaningful invariant is therefore that every parent references
    the identical module Location per rule, and that the Location resolves to the
    expected module filename.
    """

    @pytest.mark.parametrize("rule_name", RULE_NAMES)
    def test_all_templates_reference_identical_module_location(self, all_templates, rule_name):
        """All parents reference the same module Location, resolving to the expected file."""
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


# ===========================================================================
# YAML block scalar uses >- (not |)
# ===========================================================================

class TestYamlBlockScalar:
    """InputTemplate uses >- folded block scalar to avoid trailing newline."""

    @pytest.mark.parametrize(
        "module_file", list(RULE_MODULE_FILES.values()), ids=list(RULE_MODULE_FILES.keys())
    )
    def test_input_template_uses_folded_strip_scalar(self, module_file):
        """Raw module YAML uses long-form 'Fn::Sub: >-' (folded, strip) for InputTemplate."""
        content = (MODULE_DIR / module_file).read_text(encoding="utf-8")

        # The block scalar now lives in the AWS::Include module as a long-form
        # intrinsic: `InputTemplate:` followed by `Fn::Sub: >-`.
        assert re.search(r"InputTemplate:\s*\n\s*Fn::Sub:\s*>-", content), (
            f"{module_file} InputTemplate should use folded-strip 'Fn::Sub: >-'"
        )

    @pytest.mark.parametrize("template_file", TEMPLATE_FILES)
    def test_no_trailing_newline_in_input_template(self, template_file):
        """Parsed InputTemplate string does not end with a newline."""
        template = load_template(TEMPLATE_DIR / template_file)
        for rule_name in RULE_NAMES:
            raw = _get_input_template_str(template, rule_name)
            assert not raw.endswith("\n"), (
                f"InputTemplate in {template_file}/{rule_name} should not have trailing newline"
            )
