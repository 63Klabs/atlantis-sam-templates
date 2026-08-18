"""
Unit tests verifying the CodePipelineServiceRole in each pipeline template
grants sns:Publish on the PipelineNotificationTopic.

Manual approval actions (ApproveToPromote / ApproveRelease) publish to the
PipelineNotificationTopic using the pipeline's service role. Without an
sns:Publish grant scoped to that topic, CodePipeline fails the approval action
at runtime ("The Pipeline or Action role does not have permission to publish
to topics in Amazon SNS").

Fast, concrete unit tests (no property-based testing) per the repository's
testing guidelines.

Validates: runtime IAM permission for manual approval SNS notifications.
"""

import sys
import os
from pathlib import Path

import pytest

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import load_template


TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "v2" / "pipeline"

# All four pipeline templates whose inline CodePipelineServiceRole publishes to
# the notification topic for manual approval actions.
TEMPLATE_FILES = [
    "template-pipeline.yml",
    "template-pipeline-github.yml",
    "template-pipeline-build-only.yml",
    "template-pipeline-s3-source.yml",
]

TOPIC_LOGICAL_ID = "PipelineNotificationTopic"


def _as_list(value):
    """Normalize a scalar-or-list CFN field into a list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _references_topic(resource_value):
    """Return True if a Resource entry is a Ref (short- or long-form) to the
    PipelineNotificationTopic."""
    if isinstance(resource_value, dict):
        for tag in ("!Ref", "Ref"):
            if resource_value.get(tag) == TOPIC_LOGICAL_ID:
                return True
    return False


def _get_service_role_statements(template):
    """Extract the CodePipelineServiceRole policy statements from a template."""
    role = template["Resources"]["CodePipelineServiceRole"]
    policies = role["Properties"]["Policies"]
    # Single inline policy per the templates; collect all statements defensively.
    statements = []
    for policy in policies:
        statements.extend(_as_list(policy["PolicyDocument"]["Statement"]))
    return statements


@pytest.fixture(params=TEMPLATE_FILES, ids=TEMPLATE_FILES)
def pipeline_template(request):
    """Load each pipeline template as a parameterized fixture."""
    return load_template(TEMPLATE_DIR / request.param)


class TestCodePipelineServiceRolePublishesToTopic:
    """Each template's CodePipelineServiceRole must allow sns:Publish scoped to
    the PipelineNotificationTopic."""

    def test_has_role(self, pipeline_template):
        assert "CodePipelineServiceRole" in pipeline_template["Resources"], (
            "CodePipelineServiceRole resource must exist"
        )

    def test_grants_sns_publish_on_notification_topic(self, pipeline_template):
        statements = _get_service_role_statements(pipeline_template)

        matching = [
            stmt
            for stmt in statements
            if stmt.get("Effect") == "Allow"
            and "sns:Publish" in _as_list(stmt.get("Action"))
            and any(_references_topic(r) for r in _as_list(stmt.get("Resource")))
        ]

        assert matching, (
            "CodePipelineServiceRole must have an Allow statement granting "
            "sns:Publish on the PipelineNotificationTopic (via Ref). "
            f"Statements found: {[s.get('Sid') for s in statements]}"
        )

    def test_publish_statement_is_scoped_to_topic_only(self, pipeline_template):
        """Least privilege: the sns:Publish statement must not use a wildcard
        resource."""
        statements = _get_service_role_statements(pipeline_template)

        for stmt in statements:
            if "sns:Publish" in _as_list(stmt.get("Action")):
                resources = _as_list(stmt.get("Resource"))
                assert resources, "sns:Publish statement must specify a Resource"
                assert all(_references_topic(r) for r in resources), (
                    "sns:Publish must be scoped to the PipelineNotificationTopic, "
                    f"got: {resources}"
                )
                assert "*" not in resources, "sns:Publish must not use a wildcard resource"
