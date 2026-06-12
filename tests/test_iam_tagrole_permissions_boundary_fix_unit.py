"""
Unit tests for the IAM TagRole/UntagRole permissions boundary fix.

Validates that iam:TagRole and iam:UntagRole are separated into their own
unconditional statement (TagWorkerRolesByResourcePrefix) while the
ManageWorkerRolesByResourcePrefix statement retains the iam:PermissionsBoundary
condition for privilege-escalation-sensitive actions.

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8
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


# --- Task 4.1: TagWorkerRolesByResourcePrefix in pipeline template ---


class TestTagStatementPipeline:
    """Verify TagWorkerRolesByResourcePrefix exists in pipeline template with correct config."""

    def test_tag_statement_exists(self, pipeline_statements):
        """TagWorkerRolesByResourcePrefix statement must exist."""
        stmt = find_statement_by_sid(pipeline_statements, "TagWorkerRolesByResourcePrefix")
        assert stmt is not None, "TagWorkerRolesByResourcePrefix statement not found"

    def test_tag_statement_has_correct_actions(self, pipeline_statements):
        """TagWorkerRolesByResourcePrefix must have exactly iam:TagRole and iam:UntagRole."""
        stmt = find_statement_by_sid(pipeline_statements, "TagWorkerRolesByResourcePrefix")
        actions = sorted(stmt["Action"])
        assert actions == sorted(["iam:TagRole", "iam:UntagRole"])

    def test_tag_statement_has_no_condition(self, pipeline_statements):
        """TagWorkerRolesByResourcePrefix must NOT have a Condition block."""
        stmt = find_statement_by_sid(pipeline_statements, "TagWorkerRolesByResourcePrefix")
        assert "Condition" not in stmt, "TagWorkerRolesByResourcePrefix should not have a Condition"

    def test_tag_statement_effect_is_allow(self, pipeline_statements):
        """TagWorkerRolesByResourcePrefix must have Effect: Allow."""
        stmt = find_statement_by_sid(pipeline_statements, "TagWorkerRolesByResourcePrefix")
        assert stmt["Effect"] == "Allow"


# --- Task 4.2: TagWorkerRolesByResourcePrefix in storage template ---


class TestTagStatementStorage:
    """Verify TagWorkerRolesByResourcePrefix exists in storage template with correct config."""

    def test_tag_statement_exists(self, storage_statements):
        """TagWorkerRolesByResourcePrefix statement must exist."""
        stmt = find_statement_by_sid(storage_statements, "TagWorkerRolesByResourcePrefix")
        assert stmt is not None, "TagWorkerRolesByResourcePrefix statement not found"

    def test_tag_statement_has_correct_actions(self, storage_statements):
        """TagWorkerRolesByResourcePrefix must have exactly iam:TagRole and iam:UntagRole."""
        stmt = find_statement_by_sid(storage_statements, "TagWorkerRolesByResourcePrefix")
        actions = sorted(stmt["Action"])
        assert actions == sorted(["iam:TagRole", "iam:UntagRole"])

    def test_tag_statement_has_no_condition(self, storage_statements):
        """TagWorkerRolesByResourcePrefix must NOT have a Condition block."""
        stmt = find_statement_by_sid(storage_statements, "TagWorkerRolesByResourcePrefix")
        assert "Condition" not in stmt, "TagWorkerRolesByResourcePrefix should not have a Condition"

    def test_tag_statement_effect_is_allow(self, storage_statements):
        """TagWorkerRolesByResourcePrefix must have Effect: Allow."""
        stmt = find_statement_by_sid(storage_statements, "TagWorkerRolesByResourcePrefix")
        assert stmt["Effect"] == "Allow"


# --- Task 4.3: ManageWorkerRolesByResourcePrefix in pipeline template ---


class TestManageStatementPipeline:
    """Verify ManageWorkerRolesByResourcePrefix in pipeline template retains condition without tag actions."""

    def test_manage_statement_does_not_contain_tag_role(self, pipeline_statements):
        """ManageWorkerRolesByResourcePrefix must NOT contain iam:TagRole."""
        stmt = find_statement_by_sid(pipeline_statements, "ManageWorkerRolesByResourcePrefix")
        assert "iam:TagRole" not in stmt["Action"]

    def test_manage_statement_does_not_contain_untag_role(self, pipeline_statements):
        """ManageWorkerRolesByResourcePrefix must NOT contain iam:UntagRole."""
        stmt = find_statement_by_sid(pipeline_statements, "ManageWorkerRolesByResourcePrefix")
        assert "iam:UntagRole" not in stmt["Action"]

    def test_manage_statement_retains_permissions_boundary_condition(self, pipeline_statements):
        """ManageWorkerRolesByResourcePrefix must retain the iam:PermissionsBoundary condition."""
        stmt = find_statement_by_sid(pipeline_statements, "ManageWorkerRolesByResourcePrefix")
        assert "Condition" in stmt, "ManageWorkerRolesByResourcePrefix must have a Condition"
        # The condition uses Fn::If with HasPermissionsBoundaryArn
        condition = stmt["Condition"]
        assert "Fn::If" in condition
        if_block = condition["Fn::If"]
        assert if_block[0] == "HasPermissionsBoundaryArn"
        # The true branch must contain iam:PermissionsBoundary
        true_branch = if_block[1]
        assert "StringEquals" in true_branch
        assert "iam:PermissionsBoundary" in true_branch["StringEquals"]

    def test_manage_statement_retains_privilege_escalation_actions(self, pipeline_statements):
        """ManageWorkerRolesByResourcePrefix must retain all privilege-escalation-sensitive actions."""
        stmt = find_statement_by_sid(pipeline_statements, "ManageWorkerRolesByResourcePrefix")
        expected_actions = [
            "iam:AttachRolePolicy",
            "iam:CreateRole",
            "iam:DeleteRolePolicy",
            "iam:DetachRolePolicy",
            "iam:PutRolePolicy",
            "iam:UpdateRoleDescription",
        ]
        for action in expected_actions:
            assert action in stmt["Action"], f"{action} missing from ManageWorkerRolesByResourcePrefix"


# --- Task 4.4: ManageWorkerRolesByResourcePrefix in storage template ---


class TestManageStatementStorage:
    """Verify ManageWorkerRolesByResourcePrefix in storage template retains condition without tag actions."""

    def test_manage_statement_does_not_contain_tag_role(self, storage_statements):
        """ManageWorkerRolesByResourcePrefix must NOT contain iam:TagRole."""
        stmt = find_statement_by_sid(storage_statements, "ManageWorkerRolesByResourcePrefix")
        assert "iam:TagRole" not in stmt["Action"]

    def test_manage_statement_does_not_contain_untag_role(self, storage_statements):
        """ManageWorkerRolesByResourcePrefix must NOT contain iam:UntagRole."""
        stmt = find_statement_by_sid(storage_statements, "ManageWorkerRolesByResourcePrefix")
        assert "iam:UntagRole" not in stmt["Action"]

    def test_manage_statement_retains_permissions_boundary_condition(self, storage_statements):
        """ManageWorkerRolesByResourcePrefix must retain the iam:PermissionsBoundary condition."""
        stmt = find_statement_by_sid(storage_statements, "ManageWorkerRolesByResourcePrefix")
        assert "Condition" in stmt, "ManageWorkerRolesByResourcePrefix must have a Condition"
        condition = stmt["Condition"]
        assert "Fn::If" in condition
        if_block = condition["Fn::If"]
        assert if_block[0] == "HasPermissionsBoundaryArn"
        true_branch = if_block[1]
        assert "StringEquals" in true_branch
        assert "iam:PermissionsBoundary" in true_branch["StringEquals"]

    def test_manage_statement_retains_privilege_escalation_actions(self, storage_statements):
        """ManageWorkerRolesByResourcePrefix must retain all privilege-escalation-sensitive actions."""
        stmt = find_statement_by_sid(storage_statements, "ManageWorkerRolesByResourcePrefix")
        expected_actions = [
            "iam:AttachRolePolicy",
            "iam:CreateRole",
            "iam:DeleteRolePolicy",
            "iam:DetachRolePolicy",
            "iam:PutRolePolicy",
            "iam:UpdateRoleDescription",
        ]
        for action in expected_actions:
            assert action in stmt["Action"], f"{action} missing from ManageWorkerRolesByResourcePrefix"


# --- Task 4.5: Resource ARN consistency between statements ---


class TestResourceArnConsistency:
    """Verify Resource ARN pattern is identical between ManageWorkerRolesByResourcePrefix and TagWorkerRolesByResourcePrefix."""

    def test_pipeline_resource_arn_matches(self, pipeline_statements):
        """Resource ARN must be identical between both statements in pipeline template."""
        manage_stmt = find_statement_by_sid(pipeline_statements, "ManageWorkerRolesByResourcePrefix")
        tag_stmt = find_statement_by_sid(pipeline_statements, "TagWorkerRolesByResourcePrefix")
        assert manage_stmt["Resource"] == tag_stmt["Resource"]

    def test_storage_resource_arn_matches(self, storage_statements):
        """Resource ARN must be identical between both statements in storage template."""
        manage_stmt = find_statement_by_sid(storage_statements, "ManageWorkerRolesByResourcePrefix")
        tag_stmt = find_statement_by_sid(storage_statements, "TagWorkerRolesByResourcePrefix")
        assert manage_stmt["Resource"] == tag_stmt["Resource"]

    def test_pipeline_resource_arn_uses_worker_pattern(self, pipeline_statements):
        """Resource ARN must use the Worker role prefix pattern."""
        tag_stmt = find_statement_by_sid(pipeline_statements, "TagWorkerRolesByResourcePrefix")
        resource = tag_stmt["Resource"]
        # Should be {"Fn::Sub": "arn:aws:iam::${AWS::AccountId}:role${RolePath}${Prefix}-Worker-*"}
        assert "Fn::Sub" in resource
        assert "Worker-*" in resource["Fn::Sub"]

    def test_storage_resource_arn_uses_worker_pattern(self, storage_statements):
        """Resource ARN must use the Worker role prefix pattern."""
        tag_stmt = find_statement_by_sid(storage_statements, "TagWorkerRolesByResourcePrefix")
        resource = tag_stmt["Resource"]
        assert "Fn::Sub" in resource
        assert "Worker-*" in resource["Fn::Sub"]
