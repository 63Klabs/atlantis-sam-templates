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

def _get_input_template_str(template, rule_name):
    """Extract the raw InputTemplate string from a parsed template."""
    rule = template["Resources"][rule_name]
    target = rule["Properties"]["Targets"][0]
    input_template = target["InputTransformer"]["InputTemplate"]
    # InputTemplate is {'!Sub': '<json_string>'} after CFNLoader parsing
    assert isinstance(input_template, dict), "InputTemplate should be a dict with !Sub key"
    return input_template["!Sub"]


def _parse_input_template(template, rule_name):
    """Parse the InputTemplate JSON and return the dict with Subject and Message."""
    raw = _get_input_template_str(template, rule_name)
    return json.loads(raw)


def _get_input_paths_map(template, rule_name):
    """Extract the InputPathsMap from a parsed template."""
    rule = template["Resources"][rule_name]
    target = rule["Properties"]["Targets"][0]
    return target["InputTransformer"]["InputPathsMap"]


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
    """InputTemplate structure is identical across all three pipeline templates."""

    @pytest.mark.parametrize("rule_name", RULE_NAMES)
    def test_input_template_identical_across_templates(self, all_templates, rule_name):
        """InputTemplate JSON structure matches across all three templates for each rule."""
        templates_list = list(all_templates.values())
        names_list = list(all_templates.keys())

        reference = _parse_input_template(templates_list[0], rule_name)

        for i in range(1, len(templates_list)):
            other = _parse_input_template(templates_list[i], rule_name)
            assert reference.keys() == other.keys(), (
                f"Key mismatch between {names_list[0]} and {names_list[i]} for {rule_name}"
            )
            # Subject format must match (ignoring CloudFormation Sub variables)
            assert reference["Subject"] == other["Subject"], (
                f"Subject mismatch between {names_list[0]} and {names_list[i]} for {rule_name}"
            )

    @pytest.mark.parametrize("rule_name", RULE_NAMES)
    def test_input_paths_map_identical_across_templates(self, all_templates, rule_name):
        """InputPathsMap is identical across all three templates for each rule."""
        templates_list = list(all_templates.values())
        names_list = list(all_templates.keys())

        reference = _get_input_paths_map(templates_list[0], rule_name)

        for i in range(1, len(templates_list)):
            other = _get_input_paths_map(templates_list[i], rule_name)
            assert reference == other, (
                f"InputPathsMap mismatch between {names_list[0]} and {names_list[i]} for {rule_name}"
            )

    @pytest.mark.parametrize("rule_name", RULE_NAMES)
    def test_message_labels_identical_across_templates(self, all_templates, rule_name):
        """Message labels and field order match across all three templates."""
        templates_list = list(all_templates.values())
        names_list = list(all_templates.keys())

        def extract_labels(message):
            """Extract label lines from the message for comparison."""
            lines = message.split("\\n")
            return [l.strip().split(":")[0] + ":" for l in lines if ":" in l and l.strip()]

        ref_msg = _parse_input_template(templates_list[0], rule_name)["Message"]
        ref_labels = extract_labels(ref_msg)

        for i in range(1, len(templates_list)):
            other_msg = _parse_input_template(templates_list[i], rule_name)["Message"]
            other_labels = extract_labels(other_msg)
            assert ref_labels == other_labels, (
                f"Label order mismatch between {names_list[0]} and {names_list[i]} for {rule_name}"
            )


# ===========================================================================
# YAML block scalar uses >- (not |)
# ===========================================================================

class TestYamlBlockScalar:
    """InputTemplate uses >- folded block scalar to avoid trailing newline."""

    @pytest.mark.parametrize("template_file", TEMPLATE_FILES)
    @pytest.mark.parametrize("rule_name", RULE_NAMES)
    def test_input_template_uses_folded_strip_scalar(self, template_file, rule_name):
        """Raw YAML uses >- (folded, strip) for InputTemplate, not | (literal)."""
        filepath = TEMPLATE_DIR / template_file
        content = filepath.read_text(encoding="utf-8")

        # Find all InputTemplate lines and verify they use >-
        # Pattern: InputTemplate: !Sub >-
        matches = re.findall(r"InputTemplate:\s*!Sub\s+(.+)", content)
        assert len(matches) >= 3, (
            f"Expected at least 3 InputTemplate declarations in {template_file}"
        )
        for match in matches:
            assert match.strip().startswith(">-"), (
                f"InputTemplate should use >- block scalar, found: {match.strip()}"
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
