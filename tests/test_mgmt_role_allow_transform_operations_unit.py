"""
Unit tests for the AllowTransformOperations statement in management role templates.

Validates that both pipeline-mgmt-role.yml and storage-mgmt-role.yml contain
an AllowTransformOperations statement with the correct Sid, action
(cloudformation:CreateChangeSet), and all three transform resource ARNs.
Also verifies the existing ManageCloudFormationStacksByResourcePrefix statement
remains unchanged.

Validates: Requirements 1.1, 1.2, 2.1, 3.2
"""

import pytest
import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.cfn_test_utils import load_template


# --- Fixtures ---


@pytest.fixture
def pipeline_template():
    """Load the pipeline management role module template."""
    template_path = (
        Path(__file__).parent.parent
        / "templates"
        / "v2"
        / "modules"
        / "management-roles"
        / "pipeline-mgmt-role.yml"
    )
    return load_template(template_path)


@pytest.fixture
def storage_template():
    """Load the storage management role module template."""
    template_path = (
        Path(__file__).parent.parent
        / "templates"
        / "v2"
        / "modules"
        / "management-roles"
        / "storage-mgmt-role.yml"
    )
    return load_template(template_path)


@pytest.fixture
def pipeline_statements(pipeline_template):
    """Extract policy statements from the pipeline template."""
    return pipeline_template["Properties"]["Policies"][0]["PolicyDocument"]["Statement"]


@pytest.fixture
def storage_statements(storage_template):
    """Extract policy statements from the storage template."""
    return storage_template["Properties"]["Policies"][0]["PolicyDocument"]["Statement"]


def find_statement_by_sid(statements, sid):
    """Find a statement by its Sid field."""
    for stmt in statements:
        if stmt.get("Sid") == sid:
            return stmt
    return None


# --- Expected values ---

EXPECTED_TRANSFORM_ARNS = [
    "arn:aws:cloudformation:*:aws:transform/Serverless-2016-10-31",
    "arn:aws:cloudformation:*:aws:transform/LanguageExtensions",
    "arn:aws:cloudformation:*:aws:transform/Include",
]

EXPECTED_MANAGE_CFN_ACTIONS = [
    "cloudformation:*Stack*",
    "cloudformation:CreateChangeSet",
    "cloudformation:ExecuteChangeSet",
    "cloudformation:DeleteChangeSet",
    "cloudformation:DescribeChangeSet",
    "cloudformation:GetTemplate",
    "cloudformation:GetTemplateSummary",
]


# --- Task 4.1: AllowTransformOperations in pipeline template ---


class TestAllowTransformOperationsPipeline:
    """Verify AllowTransformOperations exists in pipeline template with correct config."""

    def test_statement_exists(self, pipeline_statements):
        """AllowTransformOperations statement must exist."""
        stmt = find_statement_by_sid(pipeline_statements, "AllowTransformOperations")
        assert stmt is not None, "AllowTransformOperations statement not found in pipeline template"

    def test_effect_is_allow(self, pipeline_statements):
        """AllowTransformOperations must have Effect: Allow."""
        stmt = find_statement_by_sid(pipeline_statements, "AllowTransformOperations")
        assert stmt["Effect"] == "Allow"

    def test_action_is_create_change_set(self, pipeline_statements):
        """AllowTransformOperations must have action cloudformation:CreateChangeSet."""
        stmt = find_statement_by_sid(pipeline_statements, "AllowTransformOperations")
        action = stmt["Action"]
        # Action may be a string or a list with one item
        if isinstance(action, list):
            assert action == ["cloudformation:CreateChangeSet"]
        else:
            assert action == "cloudformation:CreateChangeSet"

    def test_resource_contains_all_transform_arns(self, pipeline_statements):
        """AllowTransformOperations must contain all three transform resource ARNs."""
        stmt = find_statement_by_sid(pipeline_statements, "AllowTransformOperations")
        resource = stmt["Resource"]
        if isinstance(resource, str):
            resource = [resource]
        for arn in EXPECTED_TRANSFORM_ARNS:
            assert arn in resource, f"Missing transform ARN: {arn}"


# --- Task 4.2: AllowTransformOperations in storage template ---


class TestAllowTransformOperationsStorage:
    """Verify AllowTransformOperations exists in storage template with correct config."""

    def test_statement_exists(self, storage_statements):
        """AllowTransformOperations statement must exist."""
        stmt = find_statement_by_sid(storage_statements, "AllowTransformOperations")
        assert stmt is not None, "AllowTransformOperations statement not found in storage template"

    def test_effect_is_allow(self, storage_statements):
        """AllowTransformOperations must have Effect: Allow."""
        stmt = find_statement_by_sid(storage_statements, "AllowTransformOperations")
        assert stmt["Effect"] == "Allow"

    def test_action_is_create_change_set(self, storage_statements):
        """AllowTransformOperations must have action cloudformation:CreateChangeSet."""
        stmt = find_statement_by_sid(storage_statements, "AllowTransformOperations")
        action = stmt["Action"]
        # Action may be a string or a list with one item
        if isinstance(action, list):
            assert action == ["cloudformation:CreateChangeSet"]
        else:
            assert action == "cloudformation:CreateChangeSet"

    def test_resource_contains_all_transform_arns(self, storage_statements):
        """AllowTransformOperations must contain all three transform resource ARNs."""
        stmt = find_statement_by_sid(storage_statements, "AllowTransformOperations")
        resource = stmt["Resource"]
        if isinstance(resource, str):
            resource = [resource]
        for arn in EXPECTED_TRANSFORM_ARNS:
            assert arn in resource, f"Missing transform ARN: {arn}"


# --- Task 4.3: AllowTransformOperations has no Condition key ---


class TestAllowTransformOperationsNoCondition:
    """Verify AllowTransformOperations has no Condition key in both templates."""

    def test_pipeline_no_condition(self, pipeline_statements):
        """AllowTransformOperations in pipeline template must NOT have a Condition."""
        stmt = find_statement_by_sid(pipeline_statements, "AllowTransformOperations")
        assert "Condition" not in stmt, "AllowTransformOperations should not have a Condition"

    def test_storage_no_condition(self, storage_statements):
        """AllowTransformOperations in storage template must NOT have a Condition."""
        stmt = find_statement_by_sid(storage_statements, "AllowTransformOperations")
        assert "Condition" not in stmt, "AllowTransformOperations should not have a Condition"


# --- Task 4.4: ManageCloudFormationStacksByResourcePrefix unchanged ---


class TestManageCfnStacksUnchanged:
    """Verify ManageCloudFormationStacksByResourcePrefix remains unchanged in both templates."""

    def test_pipeline_has_correct_actions(self, pipeline_statements):
        """ManageCloudFormationStacksByResourcePrefix in pipeline must have expected actions."""
        stmt = find_statement_by_sid(pipeline_statements, "ManageCloudFormationStacksByResourcePrefix")
        assert stmt is not None, "ManageCloudFormationStacksByResourcePrefix not found in pipeline template"
        actions = sorted(stmt["Action"])
        assert actions == sorted(EXPECTED_MANAGE_CFN_ACTIONS)

    def test_pipeline_has_condition_with_prefix(self, pipeline_statements):
        """ManageCloudFormationStacksByResourcePrefix in pipeline must have Fn::Sub resource with Prefix-*."""
        stmt = find_statement_by_sid(pipeline_statements, "ManageCloudFormationStacksByResourcePrefix")
        resource = stmt["Resource"]
        # Resource is a dict with Fn::Sub
        assert "Fn::Sub" in resource
        assert "${Prefix}-*" in resource["Fn::Sub"]

    def test_storage_has_correct_actions(self, storage_statements):
        """ManageCloudFormationStacksByResourcePrefix in storage must have expected actions."""
        stmt = find_statement_by_sid(storage_statements, "ManageCloudFormationStacksByResourcePrefix")
        assert stmt is not None, "ManageCloudFormationStacksByResourcePrefix not found in storage template"
        actions = sorted(stmt["Action"])
        assert actions == sorted(EXPECTED_MANAGE_CFN_ACTIONS)

    def test_storage_has_condition_with_prefix(self, storage_statements):
        """ManageCloudFormationStacksByResourcePrefix in storage must have Fn::Sub resource with Prefix-*."""
        stmt = find_statement_by_sid(storage_statements, "ManageCloudFormationStacksByResourcePrefix")
        resource = stmt["Resource"]
        # Resource is a dict with Fn::Sub
        assert "Fn::Sub" in resource
        assert "${Prefix}-*" in resource["Fn::Sub"]
