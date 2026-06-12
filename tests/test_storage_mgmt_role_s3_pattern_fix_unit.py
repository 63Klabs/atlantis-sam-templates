"""
Unit tests for the S3 resource pattern fix and IAM managed policy addition
in storage-mgmt-role.yml.

Validates that:
- ManageBucketsByResourcePrefix has exactly 2 resource entries (bucket-level and object-level)
- Both entries use Fn::If with UseS3BucketNameOrgPrefix condition
- The non-org branch resolves to ${Prefix} (simplified pattern)
- The org-prefix branch resolves to ${S3BucketNameOrgPrefix}-${Prefix}
- ManageManagedPoliciesByResourcePrefix exists with correct actions and resource
- Existing statements remain unchanged

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 3.1, 4.2
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
def storage_statements(storage_template):
    """Extract policy statements from the storage template."""
    return storage_template["Properties"]["Policies"][0]["PolicyDocument"]["Statement"]


def find_statement_by_sid(statements, sid):
    """Find a statement by its Sid field."""
    for stmt in statements:
        if stmt.get("Sid") == sid:
            return stmt
    return None


# --- Task 4.1: ManageBucketsByResourcePrefix has exactly 2 resource entries ---


class TestManageBucketsResourceEntries:
    """Verify ManageBucketsByResourcePrefix has exactly 2 resource entries."""

    def test_statement_exists(self, storage_statements):
        """ManageBucketsByResourcePrefix statement must exist."""
        stmt = find_statement_by_sid(storage_statements, "ManageBucketsByResourcePrefix")
        assert stmt is not None, "ManageBucketsByResourcePrefix statement not found"

    def test_has_exactly_two_resource_entries(self, storage_statements):
        """ManageBucketsByResourcePrefix must have exactly 2 resource entries."""
        stmt = find_statement_by_sid(storage_statements, "ManageBucketsByResourcePrefix")
        resource = stmt["Resource"]
        assert isinstance(resource, list), "Resource should be a list"
        assert len(resource) == 2, f"Expected 2 resource entries, got {len(resource)}"

    def test_bucket_level_entry_exists(self, storage_statements):
        """One resource entry must be bucket-level: arn:aws:s3:::${BucketPrefix}-*"""
        stmt = find_statement_by_sid(storage_statements, "ManageBucketsByResourcePrefix")
        resource = stmt["Resource"]
        template_strings = [entry["Fn::Sub"][0] for entry in resource]
        assert "arn:aws:s3:::${BucketPrefix}-*" in template_strings, (
            f"Bucket-level entry 'arn:aws:s3:::${{BucketPrefix}}-*' not found. Got: {template_strings}"
        )

    def test_object_level_entry_exists(self, storage_statements):
        """One resource entry must be object-level: arn:aws:s3:::${BucketPrefix}-*/*"""
        stmt = find_statement_by_sid(storage_statements, "ManageBucketsByResourcePrefix")
        resource = stmt["Resource"]
        template_strings = [entry["Fn::Sub"][0] for entry in resource]
        assert "arn:aws:s3:::${BucketPrefix}-*/*" in template_strings, (
            f"Object-level entry 'arn:aws:s3:::${{BucketPrefix}}-*/*' not found. Got: {template_strings}"
        )


# --- Task 4.2: Both entries use Fn::If with UseS3BucketNameOrgPrefix, non-org branch is ${Prefix} ---


class TestS3EntriesNonOrgBranch:
    """Verify both S3 resource entries use Fn::If and non-org branch resolves to ${Prefix}."""

    def test_bucket_level_uses_fn_if(self, storage_statements):
        """Bucket-level entry BucketPrefix must use Fn::If with UseS3BucketNameOrgPrefix."""
        stmt = find_statement_by_sid(storage_statements, "ManageBucketsByResourcePrefix")
        resource = stmt["Resource"]
        # Find the bucket-level entry
        bucket_entry = next(e for e in resource if e["Fn::Sub"][0] == "arn:aws:s3:::${BucketPrefix}-*")
        bucket_prefix_value = bucket_entry["Fn::Sub"][1]["BucketPrefix"]
        assert "Fn::If" in bucket_prefix_value, "BucketPrefix must use Fn::If"
        assert bucket_prefix_value["Fn::If"][0] == "UseS3BucketNameOrgPrefix", (
            f"Condition must be 'UseS3BucketNameOrgPrefix', got '{bucket_prefix_value['Fn::If'][0]}'"
        )

    def test_object_level_uses_fn_if(self, storage_statements):
        """Object-level entry BucketPrefix must use Fn::If with UseS3BucketNameOrgPrefix."""
        stmt = find_statement_by_sid(storage_statements, "ManageBucketsByResourcePrefix")
        resource = stmt["Resource"]
        # Find the object-level entry
        object_entry = next(e for e in resource if e["Fn::Sub"][0] == "arn:aws:s3:::${BucketPrefix}-*/*")
        bucket_prefix_value = object_entry["Fn::Sub"][1]["BucketPrefix"]
        assert "Fn::If" in bucket_prefix_value, "BucketPrefix must use Fn::If"
        assert bucket_prefix_value["Fn::If"][0] == "UseS3BucketNameOrgPrefix", (
            f"Condition must be 'UseS3BucketNameOrgPrefix', got '{bucket_prefix_value['Fn::If'][0]}'"
        )

    def test_bucket_level_non_org_branch_is_prefix_only(self, storage_statements):
        """Bucket-level false branch (index 2) must be Fn::Sub: ${Prefix} — not containing AccountId or Region."""
        stmt = find_statement_by_sid(storage_statements, "ManageBucketsByResourcePrefix")
        resource = stmt["Resource"]
        bucket_entry = next(e for e in resource if e["Fn::Sub"][0] == "arn:aws:s3:::${BucketPrefix}-*")
        false_branch = bucket_entry["Fn::Sub"][1]["BucketPrefix"]["Fn::If"][2]
        assert false_branch == {"Fn::Sub": "${Prefix}"}, (
            f"Non-org branch must be {{'Fn::Sub': '${{Prefix}}'}}, got {false_branch}"
        )

    def test_object_level_non_org_branch_is_prefix_only(self, storage_statements):
        """Object-level false branch (index 2) must be Fn::Sub: ${Prefix} — not containing AccountId or Region."""
        stmt = find_statement_by_sid(storage_statements, "ManageBucketsByResourcePrefix")
        resource = stmt["Resource"]
        object_entry = next(e for e in resource if e["Fn::Sub"][0] == "arn:aws:s3:::${BucketPrefix}-*/*")
        false_branch = object_entry["Fn::Sub"][1]["BucketPrefix"]["Fn::If"][2]
        assert false_branch == {"Fn::Sub": "${Prefix}"}, (
            f"Non-org branch must be {{'Fn::Sub': '${{Prefix}}'}}, got {false_branch}"
        )

    def test_bucket_level_non_org_branch_no_account_or_region(self, storage_statements):
        """Bucket-level false branch must NOT contain ${AWS::AccountId} or ${AWS::Region}."""
        stmt = find_statement_by_sid(storage_statements, "ManageBucketsByResourcePrefix")
        resource = stmt["Resource"]
        bucket_entry = next(e for e in resource if e["Fn::Sub"][0] == "arn:aws:s3:::${BucketPrefix}-*")
        false_branch = bucket_entry["Fn::Sub"][1]["BucketPrefix"]["Fn::If"][2]
        false_branch_str = str(false_branch)
        assert "${AWS::AccountId}" not in false_branch_str, "Non-org branch must not contain ${AWS::AccountId}"
        assert "${AWS::Region}" not in false_branch_str, "Non-org branch must not contain ${AWS::Region}"

    def test_object_level_non_org_branch_no_account_or_region(self, storage_statements):
        """Object-level false branch must NOT contain ${AWS::AccountId} or ${AWS::Region}."""
        stmt = find_statement_by_sid(storage_statements, "ManageBucketsByResourcePrefix")
        resource = stmt["Resource"]
        object_entry = next(e for e in resource if e["Fn::Sub"][0] == "arn:aws:s3:::${BucketPrefix}-*/*")
        false_branch = object_entry["Fn::Sub"][1]["BucketPrefix"]["Fn::If"][2]
        false_branch_str = str(false_branch)
        assert "${AWS::AccountId}" not in false_branch_str, "Non-org branch must not contain ${AWS::AccountId}"
        assert "${AWS::Region}" not in false_branch_str, "Non-org branch must not contain ${AWS::Region}"


# --- Task 4.3: Org-prefix branch resolves to ${S3BucketNameOrgPrefix}-${Prefix} ---


class TestS3EntriesOrgBranch:
    """Verify org-prefix branch (index 1) resolves to ${S3BucketNameOrgPrefix}-${Prefix}."""

    def test_bucket_level_org_branch(self, storage_statements):
        """Bucket-level true branch (index 1) must be Fn::Sub: ${S3BucketNameOrgPrefix}-${Prefix}."""
        stmt = find_statement_by_sid(storage_statements, "ManageBucketsByResourcePrefix")
        resource = stmt["Resource"]
        bucket_entry = next(e for e in resource if e["Fn::Sub"][0] == "arn:aws:s3:::${BucketPrefix}-*")
        true_branch = bucket_entry["Fn::Sub"][1]["BucketPrefix"]["Fn::If"][1]
        assert true_branch == {"Fn::Sub": "${S3BucketNameOrgPrefix}-${Prefix}"}, (
            f"Org branch must be {{'Fn::Sub': '${{S3BucketNameOrgPrefix}}-${{Prefix}}'}}, got {true_branch}"
        )

    def test_object_level_org_branch(self, storage_statements):
        """Object-level true branch (index 1) must be Fn::Sub: ${S3BucketNameOrgPrefix}-${Prefix}."""
        stmt = find_statement_by_sid(storage_statements, "ManageBucketsByResourcePrefix")
        resource = stmt["Resource"]
        object_entry = next(e for e in resource if e["Fn::Sub"][0] == "arn:aws:s3:::${BucketPrefix}-*/*")
        true_branch = object_entry["Fn::Sub"][1]["BucketPrefix"]["Fn::If"][1]
        assert true_branch == {"Fn::Sub": "${S3BucketNameOrgPrefix}-${Prefix}"}, (
            f"Org branch must be {{'Fn::Sub': '${{S3BucketNameOrgPrefix}}-${{Prefix}}'}}, got {true_branch}"
        )


# --- Task 4.4: ManageManagedPoliciesByResourcePrefix statement ---


class TestManageManagedPoliciesStatement:
    """Verify ManageManagedPoliciesByResourcePrefix statement exists with correct config."""

    EXPECTED_ACTIONS = [
        "iam:CreatePolicy",
        "iam:DeletePolicy",
        "iam:CreatePolicyVersion",
        "iam:DeletePolicyVersion",
        "iam:TagPolicy",
        "iam:UntagPolicy",
    ]

    def test_statement_exists(self, storage_statements):
        """ManageManagedPoliciesByResourcePrefix statement must exist."""
        stmt = find_statement_by_sid(storage_statements, "ManageManagedPoliciesByResourcePrefix")
        assert stmt is not None, "ManageManagedPoliciesByResourcePrefix statement not found"

    def test_effect_is_allow(self, storage_statements):
        """ManageManagedPoliciesByResourcePrefix must have Effect: Allow."""
        stmt = find_statement_by_sid(storage_statements, "ManageManagedPoliciesByResourcePrefix")
        assert stmt["Effect"] == "Allow"

    def test_has_all_six_actions(self, storage_statements):
        """ManageManagedPoliciesByResourcePrefix must have all 6 IAM actions."""
        stmt = find_statement_by_sid(storage_statements, "ManageManagedPoliciesByResourcePrefix")
        actions = stmt["Action"]
        if isinstance(actions, str):
            actions = [actions]
        assert sorted(actions) == sorted(self.EXPECTED_ACTIONS), (
            f"Expected actions {sorted(self.EXPECTED_ACTIONS)}, got {sorted(actions)}"
        )

    def test_resource_contains_role_path(self, storage_statements):
        """ManageManagedPoliciesByResourcePrefix resource must contain ${RolePath}."""
        stmt = find_statement_by_sid(storage_statements, "ManageManagedPoliciesByResourcePrefix")
        resource = stmt["Resource"]
        # Resource is a dict with Fn::Sub
        assert "Fn::Sub" in resource, "Resource must use Fn::Sub"
        assert "${RolePath}" in resource["Fn::Sub"], (
            f"Resource must contain '${{RolePath}}', got: {resource['Fn::Sub']}"
        )

    def test_resource_contains_prefix_wildcard(self, storage_statements):
        """ManageManagedPoliciesByResourcePrefix resource must contain ${Prefix}-*."""
        stmt = find_statement_by_sid(storage_statements, "ManageManagedPoliciesByResourcePrefix")
        resource = stmt["Resource"]
        assert "Fn::Sub" in resource, "Resource must use Fn::Sub"
        assert "${Prefix}-*" in resource["Fn::Sub"], (
            f"Resource must contain '${{Prefix}}-*', got: {resource['Fn::Sub']}"
        )


# --- Task 4.5: Existing statements remain unchanged ---


class TestExistingStatementsUnchanged:
    """Verify existing statements still exist with their expected actions."""

    def test_manage_event_rules_exists(self, storage_statements):
        """ManageEventRulesByResourcePrefix must still exist."""
        stmt = find_statement_by_sid(storage_statements, "ManageEventRulesByResourcePrefix")
        assert stmt is not None, "ManageEventRulesByResourcePrefix statement not found"

    def test_manage_event_rules_has_events_actions(self, storage_statements):
        """ManageEventRulesByResourcePrefix must have events:* actions."""
        stmt = find_statement_by_sid(storage_statements, "ManageEventRulesByResourcePrefix")
        actions = stmt["Action"]
        if isinstance(actions, str):
            actions = [actions]
        events_actions = [a for a in actions if a.startswith("events:")]
        assert len(events_actions) > 0, "ManageEventRulesByResourcePrefix must have events:* actions"

    def test_manage_cfn_stacks_exists(self, storage_statements):
        """ManageCloudFormationStacksByResourcePrefix must still exist."""
        stmt = find_statement_by_sid(storage_statements, "ManageCloudFormationStacksByResourcePrefix")
        assert stmt is not None, "ManageCloudFormationStacksByResourcePrefix statement not found"

    def test_manage_cfn_stacks_has_cloudformation_actions(self, storage_statements):
        """ManageCloudFormationStacksByResourcePrefix must have cloudformation:* actions."""
        stmt = find_statement_by_sid(storage_statements, "ManageCloudFormationStacksByResourcePrefix")
        actions = stmt["Action"]
        if isinstance(actions, str):
            actions = [actions]
        cfn_actions = [a for a in actions if a.startswith("cloudformation:")]
        assert len(cfn_actions) > 0, "ManageCloudFormationStacksByResourcePrefix must have cloudformation:* actions"

    def test_allow_transform_operations_exists(self, storage_statements):
        """AllowTransformOperations must still exist."""
        stmt = find_statement_by_sid(storage_statements, "AllowTransformOperations")
        assert stmt is not None, "AllowTransformOperations statement not found"

    def test_allow_transform_operations_has_create_change_set(self, storage_statements):
        """AllowTransformOperations must have cloudformation:CreateChangeSet action."""
        stmt = find_statement_by_sid(storage_statements, "AllowTransformOperations")
        actions = stmt["Action"]
        if isinstance(actions, str):
            actions = [actions]
        assert "cloudformation:CreateChangeSet" in actions, (
            "AllowTransformOperations must have cloudformation:CreateChangeSet action"
        )

    def test_lambda_crud_exists(self, storage_statements):
        """LambdaCRUDThisDeploymentOnly must still exist."""
        stmt = find_statement_by_sid(storage_statements, "LambdaCRUDThisDeploymentOnly")
        assert stmt is not None, "LambdaCRUDThisDeploymentOnly statement not found"

    def test_lambda_crud_has_lambda_action(self, storage_statements):
        """LambdaCRUDThisDeploymentOnly must have lambda:* action."""
        stmt = find_statement_by_sid(storage_statements, "LambdaCRUDThisDeploymentOnly")
        actions = stmt["Action"]
        if isinstance(actions, str):
            actions = [actions]
        lambda_actions = [a for a in actions if a.startswith("lambda:")]
        assert len(lambda_actions) > 0, "LambdaCRUDThisDeploymentOnly must have lambda:* action"

    def test_dynamodb_crud_exists(self, storage_statements):
        """DynamoDbCRUDThisDeploymentOnly must still exist."""
        stmt = find_statement_by_sid(storage_statements, "DynamoDbCRUDThisDeploymentOnly")
        assert stmt is not None, "DynamoDbCRUDThisDeploymentOnly statement not found"

    def test_dynamodb_crud_has_dynamodb_action(self, storage_statements):
        """DynamoDbCRUDThisDeploymentOnly must have dynamodb:* action."""
        stmt = find_statement_by_sid(storage_statements, "DynamoDbCRUDThisDeploymentOnly")
        actions = stmt["Action"]
        if isinstance(actions, str):
            actions = [actions]
        dynamodb_actions = [a for a in actions if a.startswith("dynamodb:")]
        assert len(dynamodb_actions) > 0, "DynamoDbCRUDThisDeploymentOnly must have dynamodb:* action"
